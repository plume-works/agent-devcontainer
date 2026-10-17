import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

import pytest

REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / '.devcontainer/scripts/opencode-web-start.sh'
LOCAL_COMMAND = 'exec env -u DISPLAY opencode web --port 4096 --hostname 127.0.0.1'
EXPOSED_COMMAND = 'exec env -u DISPLAY opencode web --port 4096 --hostname 0.0.0.0'
PROXY_URI = 'https://{{port}}--repo--ws--me.example.com'
WORKSPACE_PATH = 'L3dvcmtzcGFjZXMvZXhhbXBsZQ/session'
CODER_LINK = f'https://4096--repo--ws--me.example.com/{WORKSPACE_PATH}'
LOCAL_LINK = f'http://127.0.0.1:4096/{WORKSPACE_PATH}'


def make_test_dir() -> Path:
    path = REPO_ROOT / '.tmp' / f'opencode-web-{uuid.uuid4().hex}'
    path.mkdir(parents=True)
    return path


def run_with_fake_tmux(
    *,
    password: str | None = None,
    session_exists: bool = False,
    missing: str | None = None,
    proxy_uri: str | None = None,
) -> tuple[subprocess.CompletedProcess[str], str]:
    """Run the script beside a fake tmux that logs its arguments."""
    test_dir = make_test_dir()
    log = test_dir / 'tmux.log'
    fake_bin = test_dir / 'bin'
    fake_bin.mkdir()
    fakes = {
        'opencode': '#!/bin/sh\nexit 0\n',
        'tmux': '#!/bin/sh\n'
        'printf "%s\\n" "$*" >>"$TMUX_TEST_LOG"\n'
        'case "$*" in *has-session*) [ "$TMUX_HAS_SESSION" = 1 ] ;; esac\n',
    }
    for name, body in fakes.items():
        if name == missing:
            continue
        (fake_bin / name).write_text(body)
        (fake_bin / name).chmod(0o755)
    # Only the fakes and the coreutils the script needs, so a real tmux cannot leak in.
    tools = test_dir / 'tools'
    tools.mkdir()
    for tool in ('base64', 'bash', 'env', 'printf', 'tr'):
        (tools / tool).symlink_to(shutil.which(tool))
    env = {
        'PATH': f'{fake_bin}:{tools}',
        'DEV_WORKSPACE_FOLDER': '/workspaces/example',
        'TMUX_HAS_SESSION': '1' if session_exists else '0',
        'TMUX_TEST_LOG': str(log),
    }
    if proxy_uri is not None:
        env['VSCODE_PROXY_URI'] = proxy_uri
    if password is not None:
        env['OPENCODE_SERVER_PASSWORD'] = password
    try:
        result = subprocess.run(
            [shutil.which('bash'), SCRIPT], env=env, text=True, capture_output=True
        )
        return result, log.read_text() if log.exists() else ''
    finally:
        shutil.rmtree(test_dir)


def assert_dedicated_socket(calls: str) -> None:
    lines = calls.splitlines()
    assert lines
    assert all(line.startswith('-L opencode ') for line in lines), calls


def test_binds_localhost_without_a_password():
    result, calls = run_with_fake_tmux()
    assert result.returncode == 0, result.stderr
    assert 'new-session -d -s opencode -c /workspaces/example' in calls
    assert calls.splitlines()[-1].endswith(LOCAL_COMMAND)
    assert_dedicated_socket(calls)


def test_binds_all_interfaces_with_a_password():
    result, calls = run_with_fake_tmux(password='s3cret')
    assert result.returncode == 0, result.stderr
    assert calls.splitlines()[-1].endswith(EXPOSED_COMMAND)
    assert 's3cret' not in calls


def test_empty_password_binds_localhost():
    result, calls = run_with_fake_tmux(password='')
    assert result.returncode == 0, result.stderr
    assert calls.splitlines()[-1].endswith(LOCAL_COMMAND)


def test_reuses_a_live_session():
    result, calls = run_with_fake_tmux(session_exists=True)
    assert result.returncode == 0, result.stderr
    assert 'new-session' not in calls
    assert_dedicated_socket(calls)


@pytest.mark.parametrize('missing', ['opencode', 'tmux'])
def test_skips_when_a_command_is_missing(missing):
    result, calls = run_with_fake_tmux(missing=missing)
    assert result.returncode == 0, result.stderr
    assert calls == ''
    assert missing in result.stdout + result.stderr


@pytest.mark.parametrize('session_exists', [False, True])
@pytest.mark.parametrize('password', [None, 's3cret'])
def test_prints_the_coder_link_into_the_workspace(session_exists, password):
    result, _ = run_with_fake_tmux(
        proxy_uri=PROXY_URI, session_exists=session_exists, password=password
    )
    assert result.returncode == 0, result.stderr
    assert CODER_LINK in result.stdout.split()


def test_trailing_slash_in_the_port_url_adds_no_empty_segment():
    result, _ = run_with_fake_tmux(proxy_uri=f'{PROXY_URI}/')
    assert result.returncode == 0, result.stderr
    assert CODER_LINK in result.stdout.split()


@pytest.mark.parametrize('proxy_uri', [None, ''])
def test_falls_back_to_localhost_outside_coder(proxy_uri):
    result, _ = run_with_fake_tmux(proxy_uri=proxy_uri)
    assert result.returncode == 0, result.stderr
    assert LOCAL_LINK in result.stdout.split()


@pytest.mark.parametrize('missing', ['opencode', 'tmux'])
def test_skip_prints_no_link(missing):
    result, _ = run_with_fake_tmux(missing=missing, proxy_uri=PROXY_URI)
    assert result.returncode == 0, result.stderr
    assert '/session' not in result.stdout + result.stderr


@pytest.mark.skipif(shutil.which('tmux') is None, reason='tmux is not installed')
def test_real_tmux_passes_the_password_and_drops_display():
    test_dir = make_test_dir()
    fake_bin = test_dir / 'bin'
    fake_bin.mkdir()
    result_file = test_dir / 'result'
    (fake_bin / 'opencode').write_text(
        '#!/bin/sh\n'
        'printf "%s|%s|%s" "$*" "${OPENCODE_SERVER_PASSWORD:-}" "${DISPLAY:-none}"'
        ' >"$OPENCODE_TEST_RESULT"\n'
        'sleep 10\n'
    )
    (fake_bin / 'opencode').chmod(0o755)
    env = os.environ | {
        'PATH': f'{fake_bin}:{os.environ["PATH"]}',
        'TMUX_TMPDIR': str(REPO_ROOT / '.tmp'),
        'OPENCODE_SERVER_PASSWORD': 'tmux-secret',
        'OPENCODE_TEST_RESULT': str(result_file),
        'DISPLAY': ':100',
        'DEV_WORKSPACE_FOLDER': str(REPO_ROOT),
    }
    env.pop('TMUX', None)
    try:
        result = subprocess.run([SCRIPT], env=env, text=True, capture_output=True)
        for _ in range(30):
            if result_file.exists() and result_file.read_text():
                break
            time.sleep(0.1)
        assert result.returncode == 0, result.stderr
        assert result_file.read_text() == 'web --port 4096 --hostname 0.0.0.0|tmux-secret|none'
    finally:
        subprocess.run(['tmux', '-L', 'opencode', 'kill-server'], env=env, capture_output=True)
        shutil.rmtree(test_dir)
