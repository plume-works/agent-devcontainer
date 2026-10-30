"""Tests for the dev container hostname that names the Remote Control environment."""

from collections.abc import Iterator
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest
from scratch import TMP_ROOT
import yaml

REPO_ROOT = Path(__file__).parents[2]
INIT = REPO_ROOT / '.devcontainer/devcontainer-init.sh'
COMPOSE = REPO_ROOT / '.devcontainer/docker-compose.yml'
CHECKOUT = 'agent-devcontainer'


@pytest.fixture
def checkout() -> Iterator[Path]:
    """Yield a git checkout holding only the init script, beside a stub docker."""
    root = TMP_ROOT / f'container-hostname-{uuid4().hex}'
    path = root / CHECKOUT
    (path / '.devcontainer').mkdir(parents=True)
    shutil.copy2(INIT, path / '.devcontainer/devcontainer-init.sh')
    subprocess.run(['git', 'init', '-q'], cwd=path, check=True)
    bin_dir = root / 'bin'
    bin_dir.mkdir()
    (bin_dir / 'docker').write_text('#!/bin/sh\nexit 0\n')
    (bin_dir / 'docker').chmod(0o755)
    yield path
    shutil.rmtree(root)


def hostname_for(checkout: Path, **env: str) -> str:
    """
    Run the init script with only PATH, HOME, and the given variables set.

    The script's later host-stub writes under /tmp may fail on a shared host, so only the
    `.env` it writes first is checked; the Dev Container acceptance tests run it whole.
    """
    subprocess.run(
        ['.devcontainer/devcontainer-init.sh'],
        cwd=checkout,
        env={
            'PATH': f'{checkout.parent / "bin"}:{os.environ["PATH"]}',
            'HOME': str(checkout.parent),
            **env,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    entries = dict(
        line.split('=', 1) for line in (checkout / '.devcontainer/.env').read_text().splitlines()
    )
    return entries['CONTAINER_HOSTNAME']


def test_coder_workspace_uses_the_workspace_name(checkout: Path) -> None:
    env = {
        'CODER_WORKSPACE_NAME': 'agent-dev2',
        'VSCODE_PID': '1',
        'VSCODE_IPC_HOOK': '/tmp/ipc',
        'VSCODE_PROXY_URI': 'https://x',
        'HOSTNAME': 'h',
    }
    assert hostname_for(checkout, **env) == 'coder-agent-dev2'


@pytest.mark.parametrize('marker', ['VSCODE_PID', 'VSCODE_IPC_HOOK'])
def test_vscode_uses_host_and_checkout(checkout: Path, marker: str) -> None:
    env = {marker: '1', 'HOSTNAME': 'Antons-MBP.local'}
    assert hostname_for(checkout, **env) == 'vscode-antons-mbp-agent-devcontainer'


def test_cli_uses_host_and_checkout(checkout: Path) -> None:
    assert hostname_for(checkout, HOSTNAME='builder') == 'cli-builder-agent-devcontainer'


def test_invalid_characters_become_hyphens(checkout: Path) -> None:
    assert hostname_for(checkout, CODER_WORKSPACE_NAME='My_WS!') == 'coder-my-ws'


def test_long_names_fit_one_dns_label_without_a_trailing_hyphen(checkout: Path) -> None:
    name = hostname_for(checkout, CODER_WORKSPACE_NAME='a' * 56 + '-bbbb')
    assert name == 'coder-' + 'a' * 56


def test_compose_sets_the_hostname() -> None:
    service = yaml.safe_load(COMPOSE.read_text())['services']['devcontainer']
    assert service['hostname'] == '${CONTAINER_HOSTNAME:-agentdev}'
