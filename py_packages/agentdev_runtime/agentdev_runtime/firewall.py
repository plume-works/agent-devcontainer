"""
Egress firewall, inert unless ``ENABLE_FIREWALL=true``.

The bootstrap runs ``agentdev-runtime firewall apply`` as root before supervisord starts dockerd,
so the flush keeps the engine's rules. Only deploy admits a proxy. Adapted from the Claude Code
reference implementation. Spec: firewall, standalone-opencode-runtime.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
import ipaddress
import json
from pathlib import Path
import re
import shlex
import shutil
import socket
import subprocess
import sys
import urllib.error
import urllib.request

from agentdev_runtime import settings as env

PREFIX = 'agentdev-runtime firewall'
IMAGE_ALLOWLIST = Path('/etc/agentdev/firewall-allowlist.txt')
CHECKOUT_ALLOWLIST = Path('.devcontainer/firewall-allowlist.txt')
GITHUB_META = 'github-meta'
GITHUB_META_URL = 'https://api.github.com/meta'
DOCKER_DNS = '127.0.0.11'
IPSET = 'allowed-domains'
BLOCKED_PROBE = 'https://example.com'
ALLOWED_PROBE = 'https://api.github.com/zen'
DOMAIN_RE = re.compile(
    r'^(\*\.)?[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?(\.[A-Za-z0-9]([A-Za-z0-9-]*[A-Za-z0-9])?)+$'
)
CIDR_RE = re.compile(r'^([0-9]{1,3}\.){3}[0-9]{1,3}/([0-9]|[12][0-9]|3[0-2])$')
IPV4_RE = re.compile(r'^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$')


class FirewallError(Exception):
    """The firewall refuses its configuration or failed to apply."""


def entries(text: str) -> list[tuple[int, str]]:
    """Return each allowlist entry with its line number, comments and blanks dropped."""
    found = []
    for number, line in enumerate(text.splitlines(), start=1):
        entry = re.sub(r'\s', '', line.split('#', 1)[0])
        if entry:
            found.append((number, entry))
    return found


def validate_allowlist(path: Path) -> list[str]:
    if not path.is_file():
        raise FirewallError(f'allowlist {path} does not exist')
    found = entries(path.read_text())
    for number, entry in found:
        if entry != GITHUB_META and not DOMAIN_RE.match(entry):
            raise FirewallError(
                f"{path}:{number}: '{entry}' is neither github-meta nor a domain name"
            )
    return [entry for _, entry in found]


def proxy_cidrs(raw: str, web_ports: str) -> list[str]:
    cidrs = [cidr for cidr in raw.replace(',', ' ').split() if cidr]
    for cidr in cidrs:
        if not CIDR_RE.match(cidr):
            raise FirewallError(f"AGENTDEV_TRUSTED_PROXY_CIDRS entry '{cidr}' is not an IPv4 CIDR")
    if not cidrs:
        raise FirewallError(
            'ENABLE_FIREWALL=true requires AGENTDEV_TRUSTED_PROXY_CIDRS, or the proxy cannot '
            f'reach {web_ports}'
        )
    return cidrs


def github_ranges(meta: object) -> list[str]:
    """Collapse GitHub's IPv4 ``web``, ``api``, and ``git`` ranges into the fewest CIDRs."""
    if not isinstance(meta, dict) or not all(meta.get(key) for key in ('web', 'api', 'git')):
        raise FirewallError('GitHub API response missing required fields')
    networks = []
    for cidr in [*meta['web'], *meta['api'], *meta['git']]:
        try:
            network = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            continue
        if isinstance(network, ipaddress.IPv4Network):
            networks.append(network)
    return [str(network) for network in ipaddress.collapse_addresses(networks)]


def allowlist_path(settings: env.Settings) -> Path:
    """Pick the allowlist: an explicit setting, else the checkout's or the image's copy."""
    explicit = settings.raw('FIREWALL_ALLOWLIST')
    if explicit:
        return Path(explicit)
    if settings.raw('AGENTDEV_RUNTIME_MODE') == env.DEPLOY:
        return IMAGE_ALLOWLIST
    checkout = settings.path('DEV_WORKSPACE_FOLDER') / CHECKOUT_ALLOWLIST
    return checkout if checkout.is_file() else IMAGE_ALLOWLIST


@dataclass
class System:
    """The commands and network calls the firewall makes; tests replace it."""

    out: list[str] = field(default_factory=list)

    def say(self, message: str) -> None:
        print(message, flush=True)

    def run(self, *argv: str, check: bool = True) -> bool:
        result = subprocess.run(argv, check=False, stderr=None if check else subprocess.DEVNULL)
        if check and result.returncode != 0:
            raise FirewallError(f'{shlex.join(argv)} exited {result.returncode}')
        return result.returncode == 0

    def output(self, *argv: str) -> str:
        return subprocess.run(argv, check=True, capture_output=True, text=True).stdout

    def has(self, program: str) -> bool:
        return shutil.which(program) is not None

    def gateway(self) -> str | None:
        """Return the default route's gateway, read from the kernel's route table."""
        try:
            lines = Path('/proc/net/route').read_text().splitlines()[1:]
        except OSError:
            return None
        for line in lines:
            fields = line.split()
            if len(fields) > 2 and fields[1] == '00000000':
                return socket.inet_ntoa(int(fields[2], 16).to_bytes(4, 'little'))
        return None

    def resolve(self, host: str) -> list[str]:
        try:
            infos = socket.getaddrinfo(host, None, socket.AF_INET, socket.SOCK_STREAM)
        except (OSError, UnicodeError):
            return []
        return list(dict.fromkeys(str(info[4][0]) for info in infos))

    def fetch_json(self, url: str) -> object:
        try:
            with urllib.request.urlopen(url, timeout=30) as response:
                return json.loads(response.read())
        except (OSError, ValueError) as error:
            raise FirewallError(f'Failed to fetch GitHub IP ranges: {error}') from error

    def reachable(self, url: str) -> bool:
        """Return whether ``url`` answers at all; an HTTP error status still answered."""
        try:
            with urllib.request.urlopen(url, timeout=5):
                return True
        except urllib.error.HTTPError:
            return True
        except (OSError, ValueError):
            return False


def iptables(system: System, *args: str) -> None:
    system.run('iptables', *args)


def apply_policy(system: System, allowlist: list[str], source: Path) -> None:
    """Default-DROP egress allowing only the allowlist, Docker DNS, and the Docker host."""
    system.say(f'Loading allowlist from {source}')
    nat = system.output('iptables-save', '-t', 'nat')
    dns_rules = [line for line in nat.splitlines() if DOCKER_DNS in line]
    for table in ('filter', 'nat', 'mangle'):
        iptables(system, '-t', table, '-F')
        iptables(system, '-t', table, '-X')
    system.run('ipset', 'destroy', IPSET, check=False)
    if dns_rules:
        system.say('Restoring Docker DNS rules...')
        system.run('iptables', '-t', 'nat', '-N', 'DOCKER_OUTPUT', check=False)
        system.run('iptables', '-t', 'nat', '-N', 'DOCKER_POSTROUTING', check=False)
        for rule in dns_rules:
            iptables(system, '-t', 'nat', *shlex.split(rule))
    else:
        system.say('No Docker DNS rules to restore')
    for protocol in ('udp', 'tcp'):
        iptables(
            system,
            '-A',
            'OUTPUT',
            '-p',
            protocol,
            '--dport',
            '53',
            '-d',
            DOCKER_DNS,
            '-j',
            'ACCEPT',
        )
    for protocol in ('udp', 'tcp'):
        iptables(
            system,
            *('-A', 'INPUT', '-p', protocol, '--sport', '53', '-s', DOCKER_DNS),
            *('-m', 'state', '--state', 'ESTABLISHED', '-j', 'ACCEPT'),
        )
    gateway = system.gateway()
    if gateway:
        iptables(
            system, '-A', 'OUTPUT', '-p', 'tcp', '-d', gateway, '--dport', '22', '-j', 'ACCEPT'
        )
        iptables(
            system,
            *('-A', 'INPUT', '-p', 'tcp', '-s', gateway, '--sport', '22'),
            *('-m', 'state', '--state', 'ESTABLISHED', '-j', 'ACCEPT'),
        )
    else:
        system.say(
            'WARNING: Could not determine Docker host IP; SSH egress will be restricted by '
            'allowlist rules'
        )
    iptables(system, '-A', 'INPUT', '-i', 'lo', '-j', 'ACCEPT')
    iptables(system, '-A', 'OUTPUT', '-o', 'lo', '-j', 'ACCEPT')
    system.run('ipset', 'create', IPSET, 'hash:net')
    for entry in allowlist:
        add_entry(system, entry)
    if not gateway:
        raise FirewallError('Failed to detect host IP')
    system.say(f'Host IP: {gateway}/32')
    iptables(system, '-A', 'INPUT', '-s', f'{gateway}/32', '-j', 'ACCEPT')
    iptables(system, '-A', 'OUTPUT', '-d', f'{gateway}/32', '-j', 'ACCEPT')
    for chain in ('INPUT', 'FORWARD', 'OUTPUT'):
        iptables(system, '-P', chain, 'DROP')
    for chain in ('INPUT', 'OUTPUT'):
        iptables(
            system, '-A', chain, '-m', 'state', '--state', 'ESTABLISHED,RELATED', '-j', 'ACCEPT'
        )
    iptables(system, '-A', 'OUTPUT', '-m', 'set', '--match-set', IPSET, 'dst', '-j', 'ACCEPT')
    iptables(system, '-A', 'OUTPUT', '-j', 'REJECT', '--reject-with', 'icmp-admin-prohibited')
    block_ipv6(system)
    system.say('Firewall configuration complete')


def add_entry(system: System, entry: str) -> None:
    if entry == GITHUB_META:
        system.say('Fetching GitHub IP ranges...')
        for cidr in github_ranges(system.fetch_json(GITHUB_META_URL)):
            if not CIDR_RE.match(cidr):
                raise FirewallError(f'Invalid CIDR from GitHub meta: {cidr}')
            system.say(f'Adding GitHub range {cidr}')
            system.run('ipset', 'add', IPSET, cidr)
        return
    system.say(f'Resolving {entry}...')
    addresses = system.resolve(entry)
    if not addresses:
        system.say(f'WARNING: Failed to resolve {entry} (skipping)')
        return
    for address in addresses:
        if not IPV4_RE.match(address):
            raise FirewallError(f'Invalid IP from DNS for {entry}: {address}')
        system.say(f'Adding {address} for {entry}')
        system.run('ipset', 'add', IPSET, address, check=False)


def block_ipv6(system: System) -> None:
    """Block IPv6 entirely: the allowlist is IPv4-only, so IPv6 would bypass it."""
    if not system.has('ip6tables'):
        system.say('WARNING: ip6tables not available; IPv6 traffic is not restricted')
        return
    system.run('ip6tables', '-A', 'INPUT', '-i', 'lo', '-j', 'ACCEPT')
    system.run('ip6tables', '-A', 'OUTPUT', '-o', 'lo', '-j', 'ACCEPT')
    for chain in ('INPUT', 'FORWARD', 'OUTPUT'):
        system.run('ip6tables', '-P', chain, 'DROP')
    system.say('IPv6 blocked')


def verify(system: System) -> None:
    """Fail unless a known-blocked host is blocked and GitHub's API still answers."""
    system.say('Verifying firewall rules...')
    if system.reachable(BLOCKED_PROBE):
        raise FirewallError(f'Firewall verification failed - was able to reach {BLOCKED_PROBE}')
    system.say('Firewall verification passed - example.com is blocked as expected')
    if not system.reachable(ALLOWED_PROBE):
        raise FirewallError(
            'Firewall verification failed - unable to reach https://api.github.com'
        )
    system.say('Firewall verification passed - api.github.com is reachable as expected')


def allow_proxy_ingress(system: System, cidrs: Iterable[str], web_ports: str) -> None:
    """Admit only the trusted proxy sources to the web ports."""
    for cidr in cidrs:
        iptables(
            system,
            '-A',
            'INPUT',
            '-p',
            'tcp',
            '-s',
            cidr,
            '-m',
            'multiport',
            '--dports',
            web_ports,
            '-j',
            'ACCEPT',
        )


def filter_nested_egress(system: System) -> None:
    """Apply the allowlist again in DOCKER-USER, which dockerd keeps and consults first."""
    if not system.run('iptables', '-N', 'DOCKER-USER', check=False):
        iptables(system, '-F', 'DOCKER-USER')
    iptables(
        system,
        '-A',
        'DOCKER-USER',
        '-m',
        'state',
        '--state',
        'ESTABLISHED,RELATED',
        '-j',
        'RETURN',
    )
    iptables(system, '-A', 'DOCKER-USER', '-o', 'docker0', '-j', 'RETURN')
    iptables(system, '-A', 'DOCKER-USER', '-o', 'br-+', '-j', 'RETURN')
    iptables(system, '-A', 'DOCKER-USER', '-m', 'set', '--match-set', IPSET, 'dst', '-j', 'RETURN')
    iptables(system, '-A', 'DOCKER-USER', '-j', 'REJECT', '--reject-with', 'icmp-admin-prohibited')


def apply(settings: env.Settings, system: System | None = None) -> int:
    """``firewall apply``: validate everything, then apply the policy and verify it."""
    system = system or System()
    if settings.raw('ENABLE_FIREWALL') != 'true':
        print(f"{PREFIX}: ENABLE_FIREWALL is not 'true'; the firewall stays inert", flush=True)
        return 0
    deploy = settings.raw('AGENTDEV_RUNTIME_MODE') == env.DEPLOY
    web_ports = f'{settings.get("AGENTDEV_OPENCODE_PORT")},{settings.get("AGENTDEV_XPRA_PORT")}'
    try:
        source = allowlist_path(settings)
        allowlist = validate_allowlist(source)
        cidrs = (
            proxy_cidrs(settings.raw('AGENTDEV_TRUSTED_PROXY_CIDRS'), web_ports) if deploy else []
        )
        apply_policy(system, allowlist, source)
        verify(system)
        if deploy:
            allow_proxy_ingress(system, cidrs, web_ports)
            system.say(f'{PREFIX}: proxy sources {" ".join(cidrs)} may reach ports {web_ports}')
        filter_nested_egress(system)
    except FirewallError as error:
        print(f'{PREFIX}: {error}', file=sys.stderr, flush=True)
        return 1
    return 0


def main(argv: list[str]) -> int:
    if argv != ['apply']:
        print('usage: agentdev-runtime firewall apply', file=sys.stderr)
        return 2
    return apply(env.Settings())
