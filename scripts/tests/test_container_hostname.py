"""Tests for the dev container hostname that names the Remote Control environment."""

import os
from pathlib import Path
import subprocess

import pytest
import yaml

REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / '.devcontainer/scripts/container-hostname.sh'
COMPOSE = REPO_ROOT / '.devcontainer/docker-compose.yml'
CHECKOUT = '/Users/me/src/agent-devcontainer'


def hostname_for(**env: str) -> str:
    """Run the script with only PATH and the given variables set."""
    result = subprocess.run(
        [str(SCRIPT), CHECKOUT],
        env={'PATH': os.environ['PATH'], **env},
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_coder_workspace_uses_the_workspace_name() -> None:
    env = {
        'CODER_WORKSPACE_NAME': 'agent-dev2',
        'VSCODE_PID': '1',
        'VSCODE_IPC_HOOK': '/tmp/ipc',
        'VSCODE_PROXY_URI': 'https://x',
        'HOSTNAME': 'h',
    }
    assert hostname_for(**env) == 'coder-agent-dev2'


@pytest.mark.parametrize('marker', ['VSCODE_PID', 'VSCODE_IPC_HOOK'])
def test_vscode_uses_host_and_checkout(marker: str) -> None:
    assert hostname_for(**{marker: '1', 'HOSTNAME': 'mac'}) == 'vscode-mac-agent-devcontainer'


def test_cli_uses_host_and_checkout() -> None:
    assert hostname_for(HOSTNAME='builder') == 'cli-builder-agent-devcontainer'


def test_domain_and_case_are_normalised() -> None:
    assert hostname_for(HOSTNAME='Antons-MBP.local') == 'cli-antons-mbp-agent-devcontainer'


def test_invalid_characters_become_hyphens() -> None:
    assert hostname_for(CODER_WORKSPACE_NAME='My_WS!') == 'coder-my-ws'


def test_long_names_fit_one_dns_label() -> None:
    name = hostname_for(CODER_WORKSPACE_NAME='a' * 59 + '-bbbb')
    assert len(name) <= 63
    assert not name.endswith('-')


def test_compose_sets_the_hostname() -> None:
    service = yaml.safe_load(COMPOSE.read_text())['services']['devcontainer']
    assert service['hostname'].startswith('${CONTAINER_HOSTNAME')
