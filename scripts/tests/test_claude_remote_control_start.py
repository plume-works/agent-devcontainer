import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

import pytest
from scratch import TMP_ROOT

REPO_ROOT = Path(__file__).parents[2]
SCRIPT = [sys.executable, '-m', 'agentdev_runtime', 'remote-control', 'start']
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
    path = TMP_ROOT / f'claude-remote-control-{uuid.uuid4().hex}'
    path.mkdir(parents=True)
    return path


def run_with_fake_tmux(
    *,
    token: str = 'test-secret',
    session_exists: bool = False,
    status: dict[str, object] | None = None,
    status_exit: int = 0,
    workspace_name: str | None = None,
    spawn: str | None = None,
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
        'case "$*" in *has-session*) [ "$TMUX_HAS_SESSION" = 1 ] ;; esac\n'
    )
    (fake_bin / 'tmux').chmod(0o755)
    env = os.environ | {
        'PATH': f'{fake_bin}:{os.environ["PATH"]}',
        'CLAUDE_CODE_OAUTH_TOKEN': token,
        'CLAUDE_TEST_STATUS': json.dumps(CLAUDE_AI_LOGIN if status is None else status),
        'CLAUDE_TEST_STATUS_EXIT': str(status_exit),
        'DEV_WORKSPACE_FOLDER': '/workspaces/example',
        'TMUX_HAS_SESSION': '1' if session_exists else '0',
        'TMUX_TEST_LOG': str(log),
    }
    env.pop('CODER_WORKSPACE_NAME', None)
    env.pop('AGENTDEV_CLAUDE_RC_SPAWN', None)
    if workspace_name is not None:
        env['CODER_WORKSPACE_NAME'] = workspace_name
    if spawn is not None:
        env['AGENTDEV_CLAUDE_RC_SPAWN'] = spawn
    try:
        result = subprocess.run(SCRIPT, env=env, text=True, capture_output=True)
        return result, log.read_text() if log.exists() else ''
    finally:
        shutil.rmtree(test_dir)


SERVER = 'exec env -u CLAUDE_CODE_OAUTH_TOKEN claude remote-control --spawn'


def test_starts_on_claude_ai_login_and_removes_setup_token_from_claude():
    result, calls = run_with_fake_tmux()
    assert result.returncode == 0, result.stderr
    assert 'new-session -d -s claude-remote -c /workspaces/example' in calls
    assert calls.splitlines()[-1].endswith(f'{SERVER} worktree --permission-mode auto')
    assert 'update-environment' not in calls
    assert 'test-secret' not in calls
    assert_dedicated_socket(calls)


@pytest.mark.parametrize(
    ('spawn', 'spawn_mode'),
    [
        pytest.param(None, 'worktree', id='spawn-unset'),
        pytest.param('', 'worktree', id='spawn-empty'),
        pytest.param('worktree', 'worktree', id='spawn-worktree'),
        pytest.param('same-dir', 'same-dir', id='spawn-same-dir'),
        pytest.param('session', 'session', id='spawn-session'),
    ],
)
@pytest.mark.parametrize(
    ('workspace_name', 'server_args'),
    [
        pytest.param(None, '', id='no-workspace-name'),
        pytest.param(
            'agent-dev1',
            ' --name agent-dev1 --remote-control-session-name-prefix agent-dev1',
            id='workspace-name',
        ),
    ],
)
def test_starts_remote_control_server(workspace_name, server_args, spawn, spawn_mode):
    result, calls = run_with_fake_tmux(workspace_name=workspace_name, spawn=spawn)
    assert result.returncode == 0, result.stderr
    assert 'new-session -d -s claude-remote -c /workspaces/example' in calls
    assert calls.splitlines()[-1].endswith(
        f'{SERVER} {spawn_mode} --permission-mode auto{server_args}'
    )
    assert_dedicated_socket(calls)


def test_off_skips_without_tmux():
    result, calls = run_with_fake_tmux(spawn='off')
    assert result.returncode == 0, result.stderr
    assert 'off' in result.stdout
    assert calls == ''


@pytest.mark.parametrize('session_exists', [False, True])
def test_unrecognized_spawn_fails_without_tmux(session_exists):
    result, calls = run_with_fake_tmux(spawn='worktre', session_exists=session_exists)
    assert result.returncode != 0
    assert "'worktre'" in result.stderr
    for spawn in ('worktree', 'same-dir', 'session', 'off'):
        assert spawn in result.stderr
    assert calls == ''


def assert_dedicated_socket(calls: str) -> None:
    lines = calls.splitlines()
    assert lines
    assert all(line.startswith('-L claude-remote ') for line in lines), calls


@pytest.mark.parametrize(
    ('status', 'status_exit'),
    [
        pytest.param({'loggedIn': False, 'authMethod': 'none'}, 1, id='logged-out'),
        pytest.param({'loggedIn': False, 'authMethod': 'claude.ai'}, 0, id='expired'),
        pytest.param({'loggedIn': True, 'authMethod': 'oauth_token'}, 0, id='setup-token'),
        pytest.param(CLAUDE_AI_LOGIN, 2, id='status-fails'),
    ],
)
def test_skips_without_live_claude_ai_login(status, status_exit):
    result, calls = run_with_fake_tmux(status=status, status_exit=status_exit)
    assert result.returncode == 0, result.stderr
    assert calls == ''


def test_reuses_existing_session():
    result, calls = run_with_fake_tmux(session_exists=True)
    assert result.returncode == 0, result.stderr
    assert 'has-session -t =claude-remote' in calls
    assert 'new-session' not in calls
    assert_dedicated_socket(calls)


@pytest.mark.skipif(shutil.which('tmux') is None, reason='tmux is not installed')
@pytest.mark.parametrize('existing_server', [False, True])
def test_real_tmux_starts_claude_without_setup_token(existing_server):
    test_dir = make_test_dir()
    fake_bin = test_dir / 'bin'
    result_file = test_dir / 'result'
    fake_bin.mkdir()
    (fake_bin / 'claude').write_text(
        FAKE_CLAUDE_AUTH + 'test "${1:-}" = remote-control\n'
        'test -z "${CLAUDE_CODE_OAUTH_TOKEN:-}"\n'
        'printf "passed %s" "${CLAUDE_TMUX_TEST_MARKER:-}" >"$CLAUDE_TMUX_TEST_RESULT"\n'
        'sleep 10\n'
    )
    (fake_bin / 'claude').chmod(0o755)
    marker = uuid.uuid4().hex
    env = os.environ | {
        'PATH': f'{fake_bin}:{os.environ["PATH"]}',
        # Private tmux servers per test: see bugs/remote-control-tmux-test-shared-under-xdist.
        'TMUX_TMPDIR': str(test_dir),
        'CLAUDE_CODE_OAUTH_TOKEN': 'tmux-test-secret',
        'CLAUDE_TEST_STATUS': json.dumps(CLAUDE_AI_LOGIN),
        'CLAUDE_TMUX_TEST_RESULT': str(result_file),
        'CLAUDE_CONFIG_DIR': str(test_dir),
        'DEV_WORKSPACE_FOLDER': str(REPO_ROOT),
    }
    env.pop('TMUX', None)
    try:
        if existing_server:
            # The keeper server's environment lacks the marker the caller sets below.
            subprocess.run(
                ['tmux', 'new-session', '-d', '-s', 'keeper', 'sleep 10'],
                env=env,
                check=True,
            )
        caller_env = env | {'CLAUDE_TMUX_TEST_MARKER': marker}
        result = subprocess.run(SCRIPT, env=caller_env, text=True, capture_output=True)
        for _ in range(100):
            if result_file.exists():
                break
            time.sleep(0.1)
        assert result.returncode == 0, result.stderr
        assert result_file.read_text() == f'passed {marker}'
        assert 'tmux-test-secret' not in result.stdout + result.stderr
    finally:
        subprocess.run(['tmux', 'kill-server'], env=env, capture_output=True)
        subprocess.run(
            ['tmux', '-L', 'claude-remote', 'kill-server'], env=env, capture_output=True
        )
        shutil.rmtree(test_dir)
