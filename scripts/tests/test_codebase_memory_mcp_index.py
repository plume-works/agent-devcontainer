"""codebase-memory-mcp-index.sh submits a background index and never waits for it."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / '.devcontainer/scripts'
# Answers each call from $STUB_RESPONSE; `index_repository` with `--status` would mean a wait.
STUB = """#!/usr/bin/env bash
echo "$*" >> "$STUB_LOG"
[[ $1 == cli ]] || exit 0
printf '%s' "$STUB_RESPONSE"
exit "${STUB_EXIT:-0}"
"""


def envelope(**content) -> str:
    return json.dumps({'structuredContent': content, 'isError': False})


@pytest.fixture
def stub(tmp_path: Path) -> Path:
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    cbm = bin_dir / 'codebase-memory-mcp'
    cbm.write_text(STUB)
    cbm.chmod(0o755)
    return tmp_path


def run(stub: Path, script: str, response: str, **extra: str) -> subprocess.CompletedProcess[str]:
    env = {
        'PATH': f'{stub / "bin"}:/usr/bin:/bin',
        'HOME': str(stub),
        'CBM_CACHE_DIR': str(stub / 'cache'),
        'DEV_WORKSPACE_FOLDER': '/workspaces/project',
        'STUB_LOG': str(stub / 'calls.log'),
        'STUB_RESPONSE': response,
        **extra,
    }
    return subprocess.run([SCRIPTS / script], env=env, capture_output=True, text=True, timeout=30)


def calls(stub: Path) -> list[str]:
    log = stub / 'calls.log'
    return log.read_text().splitlines() if log.exists() else []


REQUEST = 'cli --json index_repository --repo-path /workspaces/project --async true'


@pytest.mark.parametrize(
    'accepted',
    [
        envelope(state='queued', joined=False),
        envelope(state='running', joined=False),
        envelope(state='queued', joined=True),
    ],
    ids=['queued', 'running', 'joined'],
)
def test_the_request_returns_once_cbm_accepts_the_job(stub: Path, accepted: str):
    result = run(stub, 'codebase-memory-mcp-index.sh', accepted)
    assert result.returncode == 0, result.stderr
    assert calls(stub) == [REQUEST]
    assert 'in the background' in result.stdout


@pytest.mark.parametrize(
    ('response', 'extra'),
    [
        (
            json.dumps({'content': [{'type': 'text', 'text': 'needs a daemon'}], 'isError': True}),
            {},
        ),
        (envelope(state='failed'), {}),
        ('not json', {}),
        (envelope(state='queued'), {'STUB_EXIT': '3'}),
    ],
    ids=['mcp-error', 'failed-state', 'garbage', 'nonzero-exit'],
)
def test_a_refused_request_fails(stub: Path, response: str, extra: dict[str, str]):
    result = run(stub, 'codebase-memory-mcp-index.sh', response, **extra)
    assert result.returncode == 1
    assert '/workspaces/project' in result.stderr


def test_start_launches_the_daemon_then_submits_without_waiting(stub: Path):
    result = run(stub, 'codebase-memory-mcp-start.sh', envelope(state='queued', joined=False))
    assert result.returncode == 0, result.stderr
    assert calls(stub) == ['daemon start', REQUEST]


def test_no_startup_path_runs_a_blocking_index():
    for script in SCRIPTS.glob('*.sh'):
        for line in script.read_text().splitlines():
            if 'index_repository' in line and not line.lstrip().startswith('#'):
                assert '--async true' in line, f'{script.name}: {line.strip()}'
