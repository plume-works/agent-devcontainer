"""Tests for `agentdev-runtime firewall apply`: opt-in, validation, policy, nested egress."""

from __future__ import annotations

from collections.abc import Iterator
import inspect
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

from agentdev_runtime import bootstrap, firewall as egress
from agentdev_runtime.settings import Settings
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE = REPO_ROOT / 'py_packages/agentdev_runtime'
PINS = REPO_ROOT / 'devcontainer-compose-pins.yml'
ALLOWLIST = 'github-meta\nregistry-1.docker.io\n*.example-cdn.net\n# comment\n\n'
META = {
    'web': ['140.82.112.0/20', '2a0a:a440::/29'],
    'api': ['140.82.112.0/21'],
    'git': ['192.30.252.0/22'],
}
LOCKDOWN = [
    f'{tool} {rule}'
    for tool in ('iptables', 'ip6tables')
    for rule in (
        '-P INPUT DROP',
        '-P FORWARD DROP',
        '-P OUTPUT DROP',
        '-F',
        '-A INPUT -i lo -j ACCEPT',
        '-A OUTPUT -o lo -j ACCEPT',
    )
]
NAT = '-A DOCKER_OUTPUT -d 127.0.0.11/32 -p udp -m udp --dport 53 -j DNAT --to-destination 127.0.0.11:41234\n'


class FakeSystem(egress.System):
    """Records each command instead of touching the kernel or the network."""

    def __init__(self, blocked_reachable: bool = False, github_reachable: bool = True) -> None:
        super().__init__()
        self.calls: list[str] = []
        self.said: list[str] = []
        self.blocked_reachable = blocked_reachable
        self.github_reachable = github_reachable

    def say(self, message: str) -> None:
        self.said.append(message)

    def run(self, *argv: str, check: bool = True) -> bool:
        self.calls.append(' '.join(argv))
        return not (argv[:3] == ('iptables', '-N', 'DOCKER-USER'))

    def output(self, *argv: str) -> str:
        self.calls.append(' '.join(argv))
        return NAT

    def has(self, program: str) -> bool:
        return True

    def gateway(self) -> str | None:
        return '172.17.0.1'

    def resolve(self, host: str) -> list[str]:
        return {'registry-1.docker.io': ['3.0.0.1', '3.0.0.2']}.get(host, [])

    def fetch_json(self, url: str) -> object:
        return META

    def reachable(self, url: str) -> bool:
        return self.blocked_reachable if url == egress.BLOCKED_PROBE else self.github_reachable


class Firewall:
    """One firewall application against a fake system, with its settings."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.allowlist = root / 'allowlist.txt'
        self.allowlist.write_text(ALLOWLIST)
        self.system = FakeSystem()

    def run(self, **env: str) -> int:
        base = {
            'ENABLE_FIREWALL': 'true',
            'FIREWALL_ALLOWLIST': str(self.allowlist),
            'DEV_WORKSPACE_FOLDER': str(self.root),
        }
        return egress.apply(Settings(base | env), self.system)

    def calls(self) -> list[str]:
        return self.system.calls


@pytest.fixture
def firewall(tmp_path: Path) -> Firewall:
    return Firewall(tmp_path)


@pytest.mark.parametrize('value', ['', 'false', 'yes'])
def test_inert_unless_explicitly_enabled(firewall: Firewall, value: str, capsys):
    assert firewall.run(ENABLE_FIREWALL=value) == 0
    assert 'stays inert' in capsys.readouterr().out
    assert firewall.calls() == []


def test_applies_the_shared_policy_then_nested_egress(firewall: Firewall):
    assert firewall.run() == 0
    calls = firewall.calls()
    assert calls[0] == 'iptables-save -t nat'
    assert (
        'iptables -t nat -A DOCKER_OUTPUT -d 127.0.0.11/32 -p udp -m udp --dport 53 -j DNAT --to-destination 127.0.0.11:41234'
        in calls
    )
    assert 'ipset create allowed-domains hash:net' in calls
    assert 'ipset add allowed-domains 140.82.112.0/20' in calls
    assert 'ipset add allowed-domains 192.30.252.0/22' in calls
    assert not any('140.82.112.0/21' in call or '2a0a' in call for call in calls)
    assert 'ipset add allowed-domains 3.0.0.2' in calls
    assert 'iptables -P OUTPUT DROP' in calls and 'ip6tables -P OUTPUT DROP' in calls
    assert not any('--dports' in call for call in calls)
    assert 'iptables -A DOCKER-USER -m set --match-set allowed-domains dst -j RETURN' in calls
    assert calls[-1] == 'iptables -A DOCKER-USER -j REJECT --reject-with icmp-admin-prohibited'


def test_an_unresolvable_entry_is_skipped(firewall: Firewall):
    assert firewall.run() == 0
    assert 'WARNING: Failed to resolve *.example-cdn.net (skipping)' in firewall.system.said


@pytest.mark.parametrize(
    ('env', 'message'),
    [
        ({'FIREWALL_ALLOWLIST': '/nonexistent'}, 'does not exist'),
    ],
)
def test_invalid_configuration_fails_closed(firewall: Firewall, env, message, capsys):
    assert firewall.run(**env) == 1
    assert message in capsys.readouterr().err
    assert firewall.calls() == LOCKDOWN


def test_invalid_allowlist_entries_fail(firewall: Firewall, capsys):
    firewall.allowlist.write_text('github-meta\nhttps://evil.example/path\n')
    assert firewall.run() == 1
    assert 'neither github-meta nor a domain name' in capsys.readouterr().err
    assert firewall.calls() == LOCKDOWN


@pytest.mark.parametrize(
    ('system', 'message'),
    [
        (FakeSystem(blocked_reachable=True), 'was able to reach https://example.com'),
        (FakeSystem(github_reachable=False), 'unable to reach https://api.github.com'),
    ],
)
def test_self_verification_fails_loudly(firewall: Firewall, system, message, capsys):
    firewall.system = system
    assert firewall.run() == 1
    assert message in capsys.readouterr().err
    assert not any('DOCKER-USER' in call for call in system.calls)
    assert system.calls[-len(LOCKDOWN) :] == LOCKDOWN


class FailingMetaSystem(FakeSystem):
    def fetch_json(self, url: str) -> object:
        raise egress.FirewallError('GitHub meta unavailable')


def test_a_failure_after_the_flush_fails_closed(firewall: Firewall, capsys):
    firewall.system = FailingMetaSystem()
    assert firewall.run() == 1
    assert 'GitHub meta unavailable' in capsys.readouterr().err
    calls = firewall.calls()
    assert 'iptables -t filter -F' in calls
    assert calls[-len(LOCKDOWN) :] == LOCKDOWN


@pytest.mark.parametrize(
    ('value', 'requested'),
    [
        ('1', True),
        ('yes', True),
        ('ON', True),
        ('TRUE', True),
        ('', False),
        ('0', False),
        ('no', False),
        ('false', False),
    ],
)
def test_bootstrap_passes_the_exact_word_to_the_firewall(monkeypatch, value, requested):
    seen: dict[str, str] = {}

    def run(settings: Settings) -> int:
        seen['value'] = settings.raw('ENABLE_FIREWALL')
        return 0

    monkeypatch.setattr(bootstrap, 'container_environment', lambda: {'ENABLE_FIREWALL': value})
    monkeypatch.setattr(bootstrap, 'run', run)
    assert bootstrap.main([]) == 0
    assert seen['value'] == ('true' if requested else 'false')


def test_an_unrecognized_value_locks_egress_down(monkeypatch, capsys):
    system = FakeSystem()
    monkeypatch.setattr(bootstrap, 'container_environment', lambda: {'ENABLE_FIREWALL': 'ture'})
    monkeypatch.setattr(egress, 'System', lambda: system)
    assert bootstrap.main([]) == 1
    assert 'ENABLE_FIREWALL must be' in capsys.readouterr().err
    assert system.calls == LOCKDOWN


@pytest.mark.parametrize(('value', 'locked'), [('yes', True), ('false', False)])
def test_a_failed_bootstrap_fails_closed_when_the_firewall_is_on(monkeypatch, value, locked):
    system = FakeSystem()

    def run(settings: Settings) -> int:
        raise bootstrap.BootstrapError('storage refused')

    monkeypatch.setattr(bootstrap, 'container_environment', lambda: {'ENABLE_FIREWALL': value})
    monkeypatch.setattr(bootstrap, 'run', run)
    monkeypatch.setattr(egress, 'System', lambda: system)
    assert bootstrap.main([]) == 1
    assert system.calls == (LOCKDOWN if locked else [])


def test_bootstrap_applies_the_firewall_last():
    assert inspect.getsource(bootstrap.run).rstrip().endswith('return egress.apply(settings)')


def desktop_image() -> str | None:
    for line in PINS.read_text().splitlines():
        if line.strip().startswith('image:'):
            image = line.split('image:', 1)[1].strip()
            if (
                subprocess.run(
                    ['docker', 'image', 'inspect', image], capture_output=True
                ).returncode
                == 0
            ):
                return image
    return None


@pytest.fixture
def network() -> Iterator[tuple[str, str]]:
    if shutil.which('docker') is None or desktop_image() is None:
        pytest.skip('requires Docker and a local agentdev-devcontainer image')
    name = f'agentdev-fw-{uuid4().hex[:8]}'
    subprocess.run(
        ['docker', 'network', 'create', '--subnet', '10.231.7.0/24', name],
        check=True,
        capture_output=True,
    )
    containers: list[str] = []
    try:
        yield name, desktop_image() or ''
    finally:
        listed = subprocess.run(
            ['docker', 'ps', '-aq', '--filter', f'network={name}'], capture_output=True, text=True
        ).stdout.split()
        containers.extend(listed)
        if containers:
            subprocess.run(['docker', 'rm', '-f', *containers], capture_output=True)
        subprocess.run(['docker', 'network', 'rm', name], capture_output=True)


RUNTIME_SCRIPT = """
set -euo pipefail
printf 'github-meta\\nregistry-1.docker.io\\nauth.docker.io\\nproduction.cloudflare.docker.com\\nproduction.cloudfront.docker.com\\n' \\
  > /tmp/allowlist.txt
FIREWALL_ALLOWLIST=/tmp/allowlist.txt PYTHONPATH=/opt/agentdev-runtime-src \\
  python3 -m agentdev_runtime firewall apply > /tmp/fw.log 2>&1 \\
  || { cat /tmp/fw.log; exit 1; }
echo firewall-ready
dockerd > /tmp/dockerd.log 2>&1 &
for _ in $(seq 120); do docker info >/dev/null 2>&1 && break; sleep 0.5; done
docker run --rm hello-world >/dev/null && echo nested-pull-ok
gh_ip=$(getent ahostsv4 api.github.com | awk 'NR == 1 {print $1}')
docker run --rm busybox nc -z -w 5 "$gh_ip" 443 && echo nested-github-ok
forbidden_ip=$(getent ahostsv4 example.com | awk 'NR == 1 {print $1}')
docker run --rm busybox nc -z -w 5 "$forbidden_ip" 80 || echo nested-forbidden-blocked
curl -s --connect-timeout 5 https://example.com >/dev/null || echo egress-blocked
touch /tmp/done
sleep 600
"""


def test_egress_and_nested_docker_together(network):
    name, image = network
    runtime = f'{name}-runtime'
    subprocess.run(
        [
            'docker',
            'run',
            '-d',
            '--name',
            runtime,
            '--privileged',
            '--network',
            name,
            '--ip',
            '10.231.7.10',
            '-e',
            'ENABLE_FIREWALL=true',
            '-v',
            f'{PACKAGE}:/opt/agentdev-runtime-src:ro',
            '--tmpfs',
            '/var/lib/docker:exec',
            '--entrypoint',
            'bash',
            image,
            '-c',
            RUNTIME_SCRIPT,
        ],
        check=True,
        capture_output=True,
    )
    waited = subprocess.run(
        [
            'docker',
            'exec',
            runtime,
            'bash',
            '-c',
            'for _ in $(seq 400); do [ -e /tmp/done ] && exit 0; sleep 0.5; done; exit 1',
        ],
        capture_output=True,
        timeout=300,
    )
    logs = subprocess.run(['docker', 'logs', runtime], capture_output=True, text=True)
    assert waited.returncode == 0, logs.stdout + logs.stderr
    output = logs.stdout.splitlines()
    for line in (
        'firewall-ready',
        'nested-pull-ok',
        'nested-github-ok',
        'nested-forbidden-blocked',
        'egress-blocked',
    ):
        assert line in output, logs.stdout + logs.stderr
