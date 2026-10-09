import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

import pytest

REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / '.devcontainer/scripts/claude-remote-control-start.sh'
COMPOSE = REPO_ROOT / '.devcontainer/docker-compose.yml'
CLAUDE_AI_LOGIN = {'loggedIn': True, 'authMethod': 'claude.ai'}
# Prints $CLAUDE_TEST_STATUS for `claude auth status`, refusing a leaked setup token.
FAKE_CLAUDE_AUTH = (
    '#!/bin/sh\n'
    'if [ "${1:-}" = auth ]; then\n'
    '  test -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" || exit 3\n'
    '  printf "%s\\n" "$CLAUDE_TEST_STATUS"\n'
    '  exit "${CLAUDE_TEST_STATUS_EXIT:-0}"\n'
    'fi\n'
)


def make_test_dir() -> Path:
    path = REPO_ROOT / '.tmp' / f'claude-remote-control-{uuid.uuid4().hex}'
    path.mkdir(parents=True)
    return path


def run_with_fake_tmux(
    *,
    autostart: str = '1',
    token: str = 'test-secret',
    session_exists: bool = False,
    status: dict[str, object] | None = None,
    status_exit: int = 0,
) -> tuple[subprocess.CompletedProcess[str], str]:
    test_dir = make_test_dir()
    log = test_dir / 'tmux.log'
    fake_bin = test_dir / 'bin'
    fake_bin.mkdir()
    (fake_bin / 'claude').write_text(FAKE_CLAUDE_AUTH + 'exit 0\n')
    (fake_bin / 'claude').chmod(0o755)
    (fake_bin / 'tmux').write_text(
        '#!/bin/sh\n'
        'printf "%s\\n" "$*" >>"$TMUX_TEST_LOG"\n'
        'if [ "$1" = has-session ]; then [ "$TMUX_HAS_SESSION" = 1 ]; fi\n'
    )
    (fake_bin / 'tmux').chmod(0o755)
    env = os.environ | {
        'PATH': f'{fake_bin}:{os.environ["PATH"]}',
        'AGENTDEV_CLAUDE_AUTOSTART': autostart,
        'CLAUDE_CODE_OAUTH_TOKEN': token,
        'CLAUDE_TEST_STATUS': json.dumps(CLAUDE_AI_LOGIN if status is None else status),
        'CLAUDE_TEST_STATUS_EXIT': str(status_exit),
        'DEV_WORKSPACE_FOLDER': '/workspaces/example',
        'TMUX_HAS_SESSION': '1' if session_exists else '0',
        'TMUX_TEST_LOG': str(log),
    }
    try:
        result = subprocess.run([SCRIPT], env=env, text=True, capture_output=True)
        return result, log.read_text() if log.exists() else ''
    finally:
        shutil.rmtree(test_dir)


def test_starts_on_claude_ai_login_and_removes_setup_token_from_claude():
    result, calls = run_with_fake_tmux()
    assert result.returncode == 0, result.stderr
    assert 'new-session -d -s claude-remote -c /workspaces/example' in calls
    assert 'exec env -u CLAUDE_CODE_OAUTH_TOKEN claude /remote-control' in calls
    assert 'update-environment' not in calls
    assert 'test-secret' not in calls


@pytest.mark.parametrize(
    ('autostart', 'status', 'status_exit'),
    [
        pytest.param('0', CLAUDE_AI_LOGIN, 0, id='autostart-unset'),
        pytest.param('1', {'loggedIn': False, 'authMethod': 'none'}, 1, id='logged-out'),
        pytest.param('1', {'loggedIn': False, 'authMethod': 'claude.ai'}, 0, id='expired'),
        pytest.param('1', {'loggedIn': True, 'authMethod': 'oauth_token'}, 0, id='setup-token'),
        pytest.param('1', CLAUDE_AI_LOGIN, 2, id='status-fails'),
    ],
)
def test_skips_without_live_claude_ai_login(autostart, status, status_exit):
    result, calls = run_with_fake_tmux(autostart=autostart, status=status, status_exit=status_exit)
    assert result.returncode == 0, result.stderr
    assert calls == ''


def test_compose_passes_only_nonsecret_autostart_environment():
    compose = COMPOSE.read_text()
    assert 'AGENTDEV_CLAUDE_AUTOSTART: ${AGENTDEV_CLAUDE_AUTOSTART:-}' in compose
    assert 'CLAUDE_CODE_OAUTH_TOKEN' not in compose


def test_reuses_existing_session():
    result, calls = run_with_fake_tmux(session_exists=True)
    assert result.returncode == 0, result.stderr
    assert 'has-session -t =claude-remote' in calls
    assert 'new-session' not in calls


@pytest.mark.skipif(shutil.which('tmux') is None, reason='tmux is not installed')
@pytest.mark.parametrize('existing_server', [False, True])
def test_real_tmux_starts_claude_without_setup_token(existing_server):
    test_dir = make_test_dir()
    fake_bin = test_dir / 'bin'
    tmux_dir = REPO_ROOT / '.tmp'
    result_file = test_dir / 'result'
    fake_bin.mkdir()
    tmux_dir.mkdir(exist_ok=True)
    (fake_bin / 'claude').write_text(
        FAKE_CLAUDE_AUTH + 'test "${1:-}" = /remote-control\n'
        'test -z "${CLAUDE_CODE_OAUTH_TOKEN:-}"\n'
        'printf passed >"$CLAUDE_TMUX_TEST_RESULT"\n'
        'sleep 10\n'
    )
    (fake_bin / 'claude').chmod(0o755)
    env = os.environ | {
        'PATH': f'{fake_bin}:{os.environ["PATH"]}',
        'TMUX_TMPDIR': str(tmux_dir),
        'AGENTDEV_CLAUDE_AUTOSTART': '1',
        'CLAUDE_CODE_OAUTH_TOKEN': 'tmux-test-secret',
        'CLAUDE_TEST_STATUS': json.dumps(CLAUDE_AI_LOGIN),
        'CLAUDE_TMUX_TEST_RESULT': str(result_file),
        'DEV_WORKSPACE_FOLDER': str(REPO_ROOT),
    }
    env.pop('TMUX', None)
    try:
        if existing_server:
            subprocess.run(
                ['tmux', 'new-session', '-d', '-s', 'keeper', 'sleep 10'],
                env=env,
                check=True,
            )
        result = subprocess.run([SCRIPT], env=env, text=True, capture_output=True)
        for _ in range(30):
            if result_file.exists():
                break
            time.sleep(0.1)
        assert result.returncode == 0, result.stderr
        assert result_file.read_text() == 'passed'
        assert 'tmux-test-secret' not in result.stdout + result.stderr
    finally:
        subprocess.run(['tmux', 'kill-server'], env=env, capture_output=True)
        shutil.rmtree(test_dir)
