"""Tests for runtime-remote-control.sh, the standalone runtime's Remote Control watcher."""

from __future__ import annotations

from collections.abc import Callable, Iterator
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
WATCHER = REPO_ROOT / '.devcontainer/scripts/runtime-remote-control.sh'
TMP_ROOT = REPO_ROOT / '.tmp'
CLAUDE_AI_LOGIN = {'loggedIn': True, 'authMethod': 'claude.ai'}
WAITING = 'waiting for a claude.ai login'
RUNNING = 'running in tmux session claude-remote'

# `claude auth status` prints $STATE/auth.json, or fails when there is none.
FAKE_CLAUDE = """#!/usr/bin/env bash
[[ ${1:-} == auth ]] || exit 0
test -z "${CLAUDE_CODE_OAUTH_TOKEN:-}" || exit 3
echo auth >> "$STATE/claude.log"
cat "$STATE/auth.json" 2>/dev/null
"""
# A live session is the file $STATE/session; new-session fails when $STATE/tmux.fail exists.
FAKE_TMUX = """#!/usr/bin/env bash
case "$*" in
  *new-session*)
    printf '%s\\n' "$*" >> "$STATE/tmux.log"
    if [[ -f $STATE/tmux.fail ]]; then echo "no server" >&2; exit 1; fi
    touch "$STATE/session"
    ;;
  *has-session*) [[ -f $STATE/session ]] ;;
esac
"""


class Watch:
    """One watcher process with fake claude and tmux under ``root``."""

    def __init__(self, root: Path, **settings: str) -> None:
        self.state = root / 'state'
        self.claude_dir = root / 'claude'
        bin_dir = root / 'bin'
        for path in (self.state, self.claude_dir, bin_dir, root / 'xdg'):
            path.mkdir(parents=True)
        for name, body in (('claude', FAKE_CLAUDE), ('tmux', FAKE_TMUX)):
            (bin_dir / name).write_text(body)
            (bin_dir / name).chmod(0o755)
        self.status_file = root / 'xdg/remote-control.status'
        self.env = {
            'PATH': f'{bin_dir}:{os.environ["PATH"]}',
            'HOME': str(root),
            'STATE': str(self.state),
            'CLAUDE_SECURESTORAGE_CONFIG_DIR': str(self.claude_dir),
            'XDG_RUNTIME_DIR': str(root / 'xdg'),
            'AGENTDEV_HEALTH_INTERVAL': '0.1',
            'DEV_WORKSPACE_FOLDER': str(root),
            'CLAUDE_CODE_OAUTH_TOKEN': 'setup-token',
            'AGENTDEV_CLAUDE_RC_MODE': 'server',
            **settings,
        }
        self.process: subprocess.Popen[str] | None = None

    def login(self, status: dict | None = None, credential: str = 'login') -> None:
        (self.state / 'auth.json').write_text(json.dumps(status or CLAUDE_AI_LOGIN))
        (self.claude_dir / '.credentials.json').write_text(credential)

    def start(self) -> None:
        self.process = subprocess.Popen(
            [WATCHER, 'run'], env=self.env, text=True, stderr=subprocess.PIPE
        )

    def status(self) -> str:
        try:
            return self.status_file.read_text().strip()
        except FileNotFoundError:
            return ''

    def auth_checks(self) -> int:
        path = self.state / 'claude.log'
        return len(path.read_text().splitlines()) if path.exists() else 0

    def starts(self) -> list[str]:
        path = self.state / 'tmux.log'
        return path.read_text().splitlines() if path.exists() else []

    def check(self) -> int:
        return subprocess.run([WATCHER, 'check'], env=self.env).returncode

    def wait_for(self, predicate: Callable[[], bool], timeout: float = 10) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            time.sleep(0.05)
        pytest.fail(f'condition not met; status={self.status()!r} starts={self.starts()}')

    def wait_exit(self, timeout: float = 10) -> int:
        assert self.process is not None
        return self.process.wait(timeout=timeout)

    def stop(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.process.wait(timeout=10)


@pytest.fixture
def make() -> Iterator[Callable[..., Watch]]:
    TMP_ROOT.mkdir(exist_ok=True)
    roots: list[Path] = []
    watches: list[Watch] = []

    def factory(**settings: str) -> Watch:
        root = TMP_ROOT / f'rc-{uuid4().hex[:8]}'
        roots.append(root)
        watches.append(Watch(root, **settings))
        return watches[-1]

    yield factory
    for watch in watches:
        watch.stop()
    for root in roots:
        shutil.rmtree(root, ignore_errors=True)


def test_without_a_login_it_waits_and_checks_auth_only_once(make):
    watch = make()
    assert watch.check() == 1
    watch.start()
    watch.wait_for(lambda: watch.status() == WAITING)
    assert watch.check() == 0
    time.sleep(0.6)
    assert watch.auth_checks() == 1
    assert watch.starts() == []


def test_a_later_login_starts_the_session_once(make):
    watch = make()
    watch.start()
    watch.wait_for(lambda: watch.status() == WAITING)
    watch.login()
    watch.wait_for(lambda: watch.status() == RUNNING)
    time.sleep(0.5)
    assert len(watch.starts()) == 1
    assert f'-c {watch.env["DEV_WORKSPACE_FOLDER"]}' in watch.starts()[0]
    assert 'claude remote-control --spawn worktree' in watch.starts()[0]


def test_a_setup_token_login_keeps_waiting(make):
    watch = make()
    watch.login({'loggedIn': True, 'authMethod': 'oauth_token'})
    watch.start()
    watch.wait_for(lambda: watch.status() == WAITING)
    time.sleep(0.3)
    assert watch.starts() == []


def test_an_expired_login_returns_to_waiting(make):
    watch = make()
    watch.login()
    watch.start()
    watch.wait_for(lambda: watch.status() == RUNNING)
    watch.login({'loggedIn': False}, credential='cleared credential')
    watch.wait_for(lambda: watch.status() == WAITING)
    assert watch.process is not None and watch.process.poll() is None


def test_a_live_session_is_adopted(make):
    watch = make()
    watch.login()
    (watch.state / 'session').touch()
    watch.start()
    watch.wait_for(lambda: watch.status() == RUNNING)
    time.sleep(0.3)
    assert watch.starts() == []


def test_a_session_that_disappears_ends_the_watcher(make):
    watch = make()
    watch.login()
    watch.start()
    watch.wait_for(lambda: watch.status() == RUNNING)
    (watch.state / 'session').unlink()
    assert watch.wait_exit() == 1
    assert len(watch.starts()) == 1


def test_a_failing_start_ends_the_watcher_with_its_status(make):
    watch = make()
    watch.login()
    (watch.state / 'tmux.fail').touch()
    watch.start()
    assert watch.wait_exit() == 1
    assert watch.process is not None and watch.process.stderr is not None
    assert 'Failed to start Claude Remote Control' in watch.process.stderr.read()


def test_an_empty_spawn_mode_does_not_reach_the_start_script(make):
    watch = make(AGENTDEV_CLAUDE_RC_SPAWN='')
    watch.login()
    watch.start()
    watch.wait_for(lambda: watch.status() == RUNNING)
    assert 'claude remote-control --spawn worktree' in watch.starts()[0]
