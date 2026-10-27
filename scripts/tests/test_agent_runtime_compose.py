"""Tests for the standalone Compose deployment, rendered with `docker compose config`."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
BASE = REPO_ROOT / 'compose.opencode.yml'
BIND = REPO_ROOT / 'compose.opencode.bind.yml'
PINS = REPO_ROOT / 'opencode-compose-pins.yml'
ENV_EXAMPLE = REPO_ROOT / 'docker/opencode/runtime.env.example'
SECRET = 'compose-test-secret'
REQUIRED = {'OPENCODE_SERVER_PASSWORD': SECRET, 'AGENTDEV_PROXY_NETWORK': 'edge-proxy'}
INSTANCE_TARGETS = {'/home/agent', '/uv', '/var/lib/docker'}

pytestmark = pytest.mark.skipif(
    shutil.which('docker') is None
    or subprocess.run(['docker', 'compose', 'version'], capture_output=True).returncode != 0,
    reason='requires the docker compose plugin',
)


def render(*files: Path, **env: str) -> subprocess.CompletedProcess[str]:
    """Render with only the given variables, so no host credential leaks into the result."""
    clean = {'PATH': os.environ['PATH'], 'HOME': os.environ.get('HOME', '/root'), **env}
    args = [arg for path in files for arg in ('-f', str(path))]
    return subprocess.run(
        ['docker', 'compose', '-p', 'demo', *args, 'config', '--format', 'json'],
        env=clean,
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )


def service(*files: Path, **env: str) -> tuple[dict, dict]:
    result = render(*files, **env)
    assert result.returncode == 0, result.stderr
    project = json.loads(result.stdout)
    return project['services']['opencode'], project


def mounts(svc: dict) -> dict[str, dict]:
    return {mount['target']: mount for mount in svc['volumes']}


def test_clone_deployment_uses_project_volumes_and_the_shared_auth_volume():
    svc, project = service(BASE, PINS, **REQUIRED)
    assert svc['image'] == yaml.safe_load(PINS.read_text())['services']['opencode']['image']
    by_target = mounts(svc)
    assert set(by_target) == INSTANCE_TARGETS | {'/workspaces/project', '/var/lib/agentdev/auth'}
    assert all(m['type'] == 'volume' for m in by_target.values())
    names = {key: value['name'] for key, value in project['volumes'].items()}
    assert names['workspace'] == 'demo_workspace' and names['home'] == 'demo_home'
    assert names['agents-auth'] == 'agentdev-opencode-auth'
    assert svc['privileged'] is True


def test_bind_override_replaces_the_workspace_mount():
    svc, project = service(BASE, PINS, BIND, AGENTDEV_CHECKOUT='/srv/checkouts/app', **REQUIRED)
    workspace = [m for m in svc['volumes'] if m['target'] == '/workspaces/project']
    assert workspace == [
        {'type': 'bind', 'source': '/srv/checkouts/app', 'target': '/workspaces/project'}
    ]
    assert 'workspace' not in project['volumes']


def test_publishes_no_ports_and_mounts_no_host_engine():
    svc, project = service(BASE, PINS, **REQUIRED)
    assert set(project['services']) == {'opencode'}
    assert not svc.get('ports')
    assert all('docker.sock' not in str(m.get('source', '')) for m in svc['volumes'])
    assert not svc.get('secrets') and not project.get('secrets')
    network = project['networks']['proxy']
    assert (network['name'], network['external']) == ('edge-proxy', True)


@pytest.mark.parametrize('missing', sorted(REQUIRED))
def test_required_settings_fail_rendering(missing: str):
    env = {key: value for key, value in REQUIRED.items() if key != missing}
    result = render(BASE, PINS, **env)
    assert result.returncode != 0
    assert missing in result.stderr
    assert SECRET not in result.stderr


def test_every_launch_needs_the_pin_override():
    result = render(BASE, **REQUIRED)
    assert result.returncode != 0
    assert 'neither an image nor a build context' in result.stderr


def test_custom_ids_cohort_volume_and_disabled_xpra_reach_the_container():
    svc, project = service(
        BASE,
        PINS,
        AGENTDEV_UID='2345',
        AGENTDEV_GID='3456',
        AGENTDEV_AUTH_VOLUME='agentdev-opencode-auth-2345',
        AGENTDEV_SKIP_XPRA='1',
        **REQUIRED,
    )
    env = svc['environment']
    assert (env['AGENTDEV_UID'], env['AGENTDEV_GID'], env['AGENTDEV_SKIP_XPRA']) == (
        '2345',
        '3456',
        '1',
    )
    assert project['volumes']['agents-auth']['name'] == 'agentdev-opencode-auth-2345'


def test_remote_control_settings_reach_the_container_and_default_to_off():
    unset, _ = service(BASE, PINS, **REQUIRED)
    assert unset['environment']['AGENTDEV_CLAUDE_RC_MODE'] == ''
    assert unset['environment']['AGENTDEV_CLAUDE_RC_SPAWN'] == ''
    present, _ = service(
        BASE,
        PINS,
        AGENTDEV_CLAUDE_RC_MODE='server',
        AGENTDEV_CLAUDE_RC_SPAWN='same-dir',
        **REQUIRED,
    )
    assert present['environment']['AGENTDEV_CLAUDE_RC_MODE'] == 'server'
    assert present['environment']['AGENTDEV_CLAUDE_RC_SPAWN'] == 'same-dir'


def test_xpra_password_reaches_the_container_and_is_checked_at_start_not_render():
    unset, _ = service(BASE, PINS, **REQUIRED)
    assert unset['environment']['XPRA_PASSWORD'] == ''
    present, _ = service(BASE, PINS, XPRA_PASSWORD='xpra-secret', **REQUIRED)
    assert present['environment']['XPRA_PASSWORD'] == 'xpra-secret'
    assert present['environment']['OPENCODE_SERVER_PASSWORD'] == SECRET


def test_tokens_and_git_identity_pass_through_only_when_set():
    unset, _ = service(BASE, PINS, **REQUIRED)
    # A null value is Compose's "pass through if set": nothing reaches the container.
    for name in ('GH_TOKEN', 'GITHUB_TOKEN', 'GIT_AUTHOR_NAME', 'GIT_COMMITTER_EMAIL'):
        assert unset['environment'][name] is None, name
    present, _ = service(BASE, PINS, GIT_AUTHOR_NAME='Ann', GH_TOKEN=SECRET, **REQUIRED)
    assert present['environment']['GIT_AUTHOR_NAME'] == 'Ann'
    assert present['environment']['GH_TOKEN'] == SECRET


def test_env_example_documents_every_interpolated_setting():
    documented = {
        line.split('=', 1)[0]
        for line in ENV_EXAMPLE.read_text().splitlines()
        if line and not line.startswith('#')
    }
    text = BASE.read_text() + BIND.read_text()
    interpolated = {
        part.split('}', 1)[0].split(':', 1)[0].split('-', 1)[0] for part in text.split('${')[1:]
    }
    assert interpolated <= documented, interpolated - documented
    assert all(
        value == '' or not value.startswith(('ghp_', 'github_pat_'))
        for value in (line.split('=', 1)[-1] for line in ENV_EXAMPLE.read_text().splitlines())
    )
