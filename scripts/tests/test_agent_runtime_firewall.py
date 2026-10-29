"""Tests for runtime-firewall.sh: opt-in, validation, proxy ingress, and nested Docker egress."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / '.devcontainer/scripts'
SCRIPT = SCRIPTS / 'runtime-firewall.sh'
PINS = REPO_ROOT / 'devcontainer-compose-pins.yml'
ALLOWLIST = 'github-meta\nregistry-1.docker.io\n*.example-cdn.net\n# comment\n\n'


class Firewall:
    """Stubbed iptables and init-firewall.sh that record what the wrapper does."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.log = root / 'calls.log'
        self.allowlist = root / 'allowlist.txt'
        self.allowlist.write_text(ALLOWLIST)
        bin_dir = root / 'bin'
        bin_dir.mkdir()
        for name in ('iptables', 'init-firewall.sh'):
            stub = bin_dir / name
            stub.write_text(
                f'#!/usr/bin/env bash\necho "{name} $* ${{FIREWALL_ALLOWLIST:-}}" >> "{self.log}"\n'
                f'exit "${{STUB_EXIT:-0}}"\n'
            )
            stub.chmod(0o755)
        self.bin = bin_dir

    def run(self, **env: str) -> subprocess.CompletedProcess[str]:
        base = {
            'PATH': f'{self.bin}:/usr/bin:/bin',
            'ENABLE_FIREWALL': 'true',
            'AGENTDEV_RUNTIME_MODE': 'deploy',
            'FIREWALL_ALLOWLIST': str(self.allowlist),
            'AGENTDEV_INIT_FIREWALL': str(self.bin / 'init-firewall.sh'),
            'AGENTDEV_TRUSTED_PROXY_CIDRS': '10.9.0.5/32,10.9.1.0/24',
        }
        return subprocess.run([SCRIPT], env=base | env, capture_output=True, text=True)

    def calls(self) -> list[str]:
        return self.log.read_text().splitlines() if self.log.exists() else []


@pytest.fixture
def firewall(tmp_path: Path) -> Firewall:
    return Firewall(tmp_path)


@pytest.mark.parametrize('value', ['', 'false', 'yes'])
def test_inert_unless_explicitly_enabled(firewall: Firewall, value: str):
    result = firewall.run(ENABLE_FIREWALL=value, AGENTDEV_TRUSTED_PROXY_CIDRS='')
    assert result.returncode == 0
    assert 'stays inert' in result.stdout
    assert firewall.calls() == []


def test_applies_the_shared_policy_then_proxy_ingress_and_nested_egress(firewall: Firewall):
    result = firewall.run()
    assert result.returncode == 0, result.stderr
    calls = firewall.calls()
    assert calls[0] == f'init-firewall.sh  {firewall.allowlist}'
    rules = [call.rsplit(' ', 1)[0] for call in calls[1:]]
    assert rules[:2] == [
        'iptables -A INPUT -p tcp -s 10.9.0.5/32 -m multiport --dports 4096,14500 -j ACCEPT',
        'iptables -A INPUT -p tcp -s 10.9.1.0/24 -m multiport --dports 4096,14500 -j ACCEPT',
    ]
    assert 'iptables -A DOCKER-USER -m set --match-set allowed-domains dst -j RETURN' in rules
    assert rules[-1] == 'iptables -A DOCKER-USER -j REJECT --reject-with icmp-admin-prohibited'


def test_a_devcontainer_filters_egress_without_admitting_a_proxy(firewall: Firewall):
    result = firewall.run(AGENTDEV_RUNTIME_MODE='devcontainer', AGENTDEV_TRUSTED_PROXY_CIDRS='')
    assert result.returncode == 0, result.stderr
    calls = firewall.calls()
    assert calls[0] == f'init-firewall.sh  {firewall.allowlist}'
    assert not any(' INPUT ' in call for call in calls)
    assert calls[-1].startswith('iptables -A DOCKER-USER -j REJECT')


@pytest.mark.parametrize(
    ('env', 'message'),
    [
        ({'AGENTDEV_TRUSTED_PROXY_CIDRS': ''}, 'requires AGENTDEV_TRUSTED_PROXY_CIDRS'),
        ({'AGENTDEV_TRUSTED_PROXY_CIDRS': '10.0.0.0/33'}, 'is not an IPv4 CIDR'),
        ({'FIREWALL_ALLOWLIST': '/nonexistent'}, 'does not exist'),
    ],
)
def test_invalid_configuration_fails_before_any_rule(firewall: Firewall, env, message):
    result = firewall.run(**env)
    assert result.returncode == 1
    assert message in result.stderr
    assert firewall.calls() == []


def test_invalid_allowlist_entries_fail(firewall: Firewall):
    firewall.allowlist.write_text('github-meta\nhttps://evil.example/path\n')
    result = firewall.run()
    assert result.returncode == 1
    assert "allowlist.txt:2: 'https://evil.example/path'" in result.stderr


def test_self_check_failure_propagates(firewall: Firewall):
    assert firewall.run(STUB_EXIT='1').returncode == 1


def test_bootstrap_applies_the_firewall_last():
    bootstrap = (SCRIPTS / 'runtime-bootstrap.sh').read_text()
    assert bootstrap.rstrip().endswith('/runtime-firewall.sh"')


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
        pytest.skip('requires Docker and a local agent-desktop image')
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
FIREWALL_ALLOWLIST=/tmp/allowlist.txt /opt/agentdev-runtime/runtime-firewall.sh > /tmp/fw.log 2>&1 \\
  || { cat /tmp/fw.log; exit 1; }
echo firewall-ready
python3 -m http.server 4096 >/dev/null 2>&1 &
python3 -m http.server 5000 >/dev/null 2>&1 &
/opt/agentdev-runtime/runtime-docker.sh run > /tmp/dockerd.log 2>&1 &
for _ in $(seq 120); do docker info >/dev/null 2>&1 && break; sleep 0.5; done
docker run --rm hello-world >/dev/null && echo nested-pull-ok
gh_ip=$(dig +short A api.github.com | tail -1)
docker run --rm busybox nc -z -w 5 "$gh_ip" 443 && echo nested-github-ok
forbidden_ip=$(dig +short A example.com | tail -1)
docker run --rm busybox nc -z -w 5 "$forbidden_ip" 80 || echo nested-forbidden-blocked
curl -s --connect-timeout 5 https://example.com >/dev/null || echo egress-blocked
touch /tmp/done
sleep 600
"""


def probe(network: str, image: str, ip: str, target: str) -> str:
    result = subprocess.run(
        [
            'docker',
            'run',
            '--rm',
            '--network',
            network,
            '--ip',
            ip,
            '--entrypoint',
            'bash',
            image,
            '-c',
            f'curl -s -o /dev/null -w "%{{http_code}}" --max-time 5 {target} || true',
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    return result.stdout.strip()


def test_proxy_ingress_egress_and_nested_docker_together(network):
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
            '-e',
            'AGENTDEV_TRUSTED_PROXY_CIDRS=10.231.7.20/32',
            '-v',
            f'{SCRIPTS}:/opt/agentdev-runtime:ro',
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

    assert probe(name, image, '10.231.7.20', 'http://10.231.7.10:4096/') == '200'
    assert probe(name, image, '10.231.7.20', 'http://10.231.7.10:5000/') == '000'
    assert probe(name, image, '10.231.7.30', 'http://10.231.7.10:4096/') == '000'
