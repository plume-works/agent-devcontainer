"""Tests for the dev container Compose service, rendered with `docker compose config`."""

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
COMPOSE = REPO_ROOT / '.devcontainer/docker-compose.yml'

pytestmark = pytest.mark.skipif(
    shutil.which('docker') is None
    or subprocess.run(['docker', 'compose', 'version'], capture_output=True).returncode != 0,
    reason='requires the docker compose plugin',
)


def environment(**env: str) -> dict[str, str]:
    """Return the rendered `devcontainer` service environment under only ``env``."""
    result = subprocess.run(
        ['docker', 'compose', '-p', 'demo', '-f', str(COMPOSE), 'config', '--format', 'json'],
        env={'PATH': os.environ['PATH'], 'HOME': os.environ.get('HOME', '/root'), **env},
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)['services']['devcontainer']['environment']


def test_subagent_depth_defaults_to_five_and_takes_the_host_value():
    assert environment()['CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH'] == '5'
    overridden = environment(CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH='7')
    assert overridden['CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH'] == '7'
