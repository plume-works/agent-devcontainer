"""
Claude Remote Control: the supervised watcher and the start of its server.

The watcher waits for a claude.ai login, starts ``claude-remote``, and exits once a session it
started stopped or did not start. The recovery budget of the ``controller`` event listener
then restarts it.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import time

from agentdev_runtime import settings as env

PREFIX = 'agentdev-runtime remote-control'
SESSION = 'claude-remote'
SPAWNS = ('worktree', 'same-dir', 'session', 'off')
SETUP_TOKEN = 'CLAUDE_CODE_OAUTH_TOKEN'
WAITING = 'waiting for a claude.ai login'
RUNNING = f'running in tmux session {SESSION}'


def log(message: str) -> None:
    print(f'{PREFIX}: {message}', file=sys.stderr, flush=True)


def without_setup_token() -> dict[str, str]:
    """Return the environment without a setup token, which masks the saved login."""
    return {key: value for key, value in os.environ.items() if key != SETUP_TOKEN}


def auth_status() -> tuple[int, str]:
    result = subprocess.run(
        ['claude', 'auth', 'status', '--json'],
        env=without_setup_token(),
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout


def auth_method(output: str) -> str:
    """Return the login's auth method, ``none`` without a login; raise on unreadable output."""
    status = json.loads(output)
    return str(status.get('authMethod')) if status.get('loggedIn') is True else 'none'


def logged_in() -> bool:
    code, output = auth_status()
    try:
        return code == 0 and auth_method(output) == 'claude.ai'
    except (ValueError, AttributeError):
        return False


def live() -> bool:
    command = ['tmux', '-L', SESSION, 'has-session', '-t', f'={SESSION}']
    return subprocess.run(command, capture_output=True, check=False).returncode == 0


def config_dir() -> Path:
    home = Path(os.environ.get('HOME') or Path.home())
    return Path(os.environ.get('CLAUDE_CONFIG_DIR') or home / '.claude')


def pane_command(spawn: str, workspace_name: str) -> str:
    """Return the pane's command; the server prompts without --spawn."""
    command = f'claude remote-control --spawn {spawn} --permission-mode auto'
    if workspace_name:
        name = shlex.quote(workspace_name)
        command += f' --name {name} --remote-control-session-name-prefix {name}'
    return command


def start() -> int:
    """Start Remote Control in its own tmux server, or leave a live session alone."""
    spawn = env.Settings().get('AGENTDEV_CLAUDE_RC_SPAWN')
    if spawn not in SPAWNS:
        print(
            f"Unrecognized AGENTDEV_CLAUDE_RC_SPAWN '{spawn}'; valid options: {', '.join(SPAWNS)}.",
            file=sys.stderr,
        )
        return 1
    if spawn == 'off':
        print('AGENTDEV_CLAUDE_RC_SPAWN is off; skipping Remote Control.')
        return 0
    for command in ('claude', 'tmux'):
        if shutil.which(command) is None:
            print(
                f'{command} is not installed; skipping Claude Remote Control startup.',
                file=sys.stderr,
            )
            return 0
    code, output = auth_status()
    if code != 0:
        print('Claude is not logged in; skipping Remote Control.')
        return 0
    try:
        method = auth_method(output)
    except (ValueError, AttributeError):
        print(
            "Could not parse 'claude auth status --json'; skipping Remote Control.",
            file=sys.stderr,
        )
        return 0
    if method != 'claude.ai':
        print(f'No claude.ai login (auth method: {method}); skipping Remote Control.')
        return 0
    running = f"Claude Remote Control tmux session '{SESSION}' is already running."
    pane = pane_command(spawn, os.environ.get('CODER_WORKSPACE_NAME', ''))
    if live():
        print(running)
        return 0
    workspace = env.Settings().get('DEV_WORKSPACE_FOLDER')
    # Setup tokens cannot establish Remote Control; keep one out of that process.
    tmux = [
        'tmux',
        '-L',
        SESSION,
        'start-server',
        ';',
        'new-session',
        '-d',
        '-s',
        SESSION,
        '-c',
        workspace,
        f'exec env -u {SETUP_TOKEN} {pane}',
    ]
    result = subprocess.run(tmux, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        if live():
            print(running)
            return 0
        print(
            f'Failed to start Claude Remote Control: {(result.stdout + result.stderr).strip()}',
            file=sys.stderr,
        )
        return 1
    print(f"Started Claude Remote Control in tmux session '{SESSION}'.", flush=True)
    return 0


def signature(credentials: Path) -> str:
    """Fingerprint the credential file, which a login, refresh, or expiry rewrites."""
    try:
        info = credentials.stat()
    except OSError:
        return 'none'
    return f'{info.st_ino} {int(info.st_mtime)} {info.st_size}'


def report(status_file: Path, text: str) -> None:
    staged = status_file.with_name(status_file.name + '.tmp')
    staged.write_text(text + '\n')
    staged.replace(status_file)


def run(status_file: Path) -> int:
    for command in ('claude', 'tmux'):
        if shutil.which(command) is None:
            log(f'{command} is not installed')
            return 1
    settings = env.Settings()
    credentials = Path(settings.get('CLAUDE_SECURESTORAGE_CONFIG_DIR')) / '.credentials.json'
    interval = float(settings.get('AGENTDEV_HEALTH_INTERVAL'))
    checked = ''
    login = False
    seen = False
    while True:
        current = signature(credentials)
        if current != checked:
            checked = current
            login = logged_in()
        if not login:
            seen = False
            report(status_file, WAITING)
        elif live():
            seen = True
            report(status_file, RUNNING)
        elif seen:
            log(f'tmux session {SESSION} is gone')
            return 1
        else:
            status = start()
            if status != 0:
                return status
            # A start that leaves no session counts as the session exiting.
            if not live():
                log(f'tmux session {SESSION} did not come up')
                return 1
            seen = True
            report(status_file, RUNNING)
        time.sleep(interval)


def main(argv: list[str]) -> int:
    command = argv[0] if argv else ''
    if command == 'start' and len(argv) == 1:
        return start()
    if command in ('run', 'check') and len(argv) == 1:
        runtime_dir = os.environ.get('XDG_RUNTIME_DIR')
        if not runtime_dir:
            log('XDG_RUNTIME_DIR is required')
            return 1
        status_file = Path(runtime_dir) / 'remote-control.status'
        if command == 'check':
            return 0 if status_file.is_file() and status_file.stat().st_size > 0 else 1
        return run(status_file)
    print('usage: agentdev-runtime remote-control run|check|start', file=sys.stderr)
    return 2
