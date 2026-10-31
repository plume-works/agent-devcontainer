"""
Claude Remote Control: the supervised watcher, its start, the pinned pane, and the pin hook.

The watcher waits for a claude.ai login, starts ``claude-remote``, and exits once a session it
started is gone or never came up, so the controller's recovery budget restarts it. Spec:
claude-remote-control.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

from agentdev_runtime import settings as env

PREFIX = 'agentdev-runtime remote-control'
SESSION = 'claude-remote'
MODES = ('server', 'session')
SPAWNS = ('worktree', 'same-dir')
PANE = 'agentdev-runtime remote-control session'
PIN_HOOK = 'agentdev-runtime remote-control pin'
ID_FILE = 'remote-control-session-id'
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


def pane_command(mode: str, spawn: str, workspace_name: str) -> str:
    """Return the pane's command; server mode refuses --settings and prompts without --spawn."""
    if mode == 'server':
        command = f'claude remote-control --spawn {spawn}'
        if workspace_name:
            name = shlex.quote(workspace_name)
            command += f' --name {name} --remote-control-session-name-prefix {name}'
        return command
    return f'{PANE} {shlex.quote(workspace_name)}' if workspace_name else PANE


def start() -> int:
    """Start Remote Control in its own tmux server, or leave a live session alone."""
    mode = os.environ.get('AGENTDEV_CLAUDE_RC_MODE', 'session')
    if mode not in MODES:
        print(
            f"Unrecognized AGENTDEV_CLAUDE_RC_MODE '{mode}'; valid options: server, session.",
            file=sys.stderr,
        )
        return 1
    spawn = os.environ.get('AGENTDEV_CLAUDE_RC_SPAWN', 'worktree')
    if mode == 'server' and spawn not in SPAWNS:
        print(
            f"Unrecognized AGENTDEV_CLAUDE_RC_SPAWN '{spawn}'; valid options: worktree, same-dir.",
            file=sys.stderr,
        )
        return 1
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
    pane = pane_command(mode, spawn, os.environ.get('CODER_WORKSPACE_NAME', ''))
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


def session(name: str | None) -> int:
    """Resume the pinned conversation, or pin a new one when there is none or it fails."""
    id_file = config_dir() / ID_FILE
    hook = {'hooks': {'SessionStart': [{'hooks': [{'type': 'command', 'command': PIN_HOOK}]}]}}
    remote_control = ['--remote-control', *([name] if name else [])]
    remote_control += ['--settings', json.dumps(hook, separators=(',', ':'))]
    try:
        stored = id_file.read_text().strip()
    except OSError:
        stored = ''
    if stored:
        sys.stdout.flush()
        if (
            subprocess.run(['claude', *remote_control, '--resume', stored], check=False).returncode
            == 0
        ):
            return 0
    new_id = str(uuid.uuid4())
    id_file.parent.mkdir(parents=True, exist_ok=True)
    id_file.write_text(f'{new_id}\n')
    os.execvp('claude', ['claude', *remote_control, '--session-id', new_id])


def pin() -> int:
    """SessionStart hook keeping the pin on the pane's conversation; it never fails."""
    try:
        session_id = json.loads(sys.stdin.read()).get('session_id') or ''
    except (ValueError, AttributeError):
        print('SessionStart input is not JSON; Remote Control pin unchanged.', file=sys.stderr)
        return 0
    if not session_id:
        print(
            'SessionStart input has no session_id; Remote Control pin unchanged.', file=sys.stderr
        )
        return 0
    id_file = config_dir() / ID_FILE
    id_file.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp = tempfile.mkstemp(dir=id_file.parent, prefix=f'{ID_FILE}.')
    with os.fdopen(descriptor, 'w') as handle:
        handle.write(f'{session_id}\n')
    os.replace(temp, id_file)
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
    # Compose passes a set-but-empty spawn mode through; the start would reject it.
    if not os.environ.get('AGENTDEV_CLAUDE_RC_SPAWN'):
        os.environ.pop('AGENTDEV_CLAUDE_RC_SPAWN', None)
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
    if command == 'session' and len(argv) <= 2:
        return session(argv[1] if len(argv) == 2 else None)
    if command == 'pin' and len(argv) == 1:
        return pin()
    if command in ('run', 'check') and len(argv) == 1:
        runtime_dir = os.environ.get('XDG_RUNTIME_DIR')
        if not runtime_dir:
            log('XDG_RUNTIME_DIR is required')
            return 1
        status_file = Path(runtime_dir) / 'remote-control.status'
        if command == 'check':
            return 0 if status_file.is_file() and status_file.stat().st_size > 0 else 1
        return run(status_file)
    print(
        'usage: agentdev-runtime remote-control run|check|start|session [name]|pin',
        file=sys.stderr,
    )
    return 2
