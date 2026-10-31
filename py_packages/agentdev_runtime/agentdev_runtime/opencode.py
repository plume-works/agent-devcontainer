"""
The OpenCode server: the supervised ``serve``, its probe, its link, and the Coder start.

Spec: opencode-web, standalone-opencode-runtime.
"""

from __future__ import annotations

import base64
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

from agentdev_runtime import settings as env

PREFIX = 'agentdev-runtime opencode'
SESSION = 'opencode'
PASSWORD_FILE = '.local/share/opencode/agentdev-server-password'
LOCAL_URL_TEMPLATE = 'http://127.0.0.1:{{port}}'


class OpenCodeError(Exception):
    """The server cannot be started or probed as configured."""


def password_file() -> Path:
    return Path(os.environ.get('HOME') or Path.home()) / PASSWORD_FILE


def link(settings: env.Settings) -> str:
    """Return the server's root URL; Coder's agent sets VSCODE_PROXY_URI to its port template."""
    base = settings.raw('VSCODE_PROXY_URI') or LOCAL_URL_TEMPLATE
    return base.replace('{{port}}', settings.get('AGENTDEV_OPENCODE_PORT')).rstrip('/')


def coder_hostname(settings: env.Settings) -> str:
    """Bind every interface for a Coder-provided password; a generated one stays local."""
    return '0.0.0.0' if settings.raw('OPENCODE_SERVER_PASSWORD') else '127.0.0.1'


def coder_pane(settings: env.Settings) -> str:
    """Return the tmux pane command; a generated password is read from its file, never argv."""
    serve = f'opencode serve --port {settings.get("AGENTDEV_OPENCODE_PORT")} --hostname'
    if settings.raw('OPENCODE_SERVER_PASSWORD'):
        return f'exec env -u DISPLAY {serve} 0.0.0.0'
    path = password_file()
    if not path.is_file() or path.stat().st_size == 0:
        path.parent.mkdir(parents=True, exist_ok=True)
        secret = base64.b64encode(os.urandom(32)).decode()
        secret = secret.translate(str.maketrans('', '', '\n/+='))
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(descriptor, 'w') as handle:
            handle.write(secret)
    return (
        'exec bash -c \'OPENCODE_SERVER_PASSWORD="$(cat "$1")" exec env -u DISPLAY '
        f"{serve} 127.0.0.1' opencode-web {shlex.quote(str(path))}"
    )


def coder_note(settings: env.Settings) -> str:
    return '' if settings.raw('OPENCODE_SERVER_PASSWORD') else f' (password in {password_file()})'


def require_password(settings: env.Settings) -> str:
    password = settings.raw('OPENCODE_SERVER_PASSWORD')
    if not password:
        raise OpenCodeError(
            'OPENCODE_SERVER_PASSWORD must be set to a nonempty value; the server listens on '
            'the proxy network'
        )
    return password


def probe(settings: env.Settings) -> bool:
    """Ready means an authenticated ``/api/info`` names a version; the web UI page is public."""
    password = require_password(settings)
    user = settings.get('OPENCODE_SERVER_USERNAME')
    token = base64.b64encode(f'{user}:{password}'.encode()).decode()
    request = urllib.request.Request(
        f'http://127.0.0.1:{settings.get("AGENTDEV_OPENCODE_PORT")}/api/info',
        headers={'Authorization': f'Basic {token}'},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            info = json.loads(response.read())
    except (OSError, ValueError) as error:
        print(f'{PREFIX}: probe failed: {error}', file=sys.stderr)
        return False
    version = info.get('version') if isinstance(info, dict) else None
    return isinstance(version, str) and bool(version)


def serve(settings: env.Settings) -> int:
    require_password(settings)
    if shutil.which('opencode') is None:
        raise OpenCodeError('opencode is not installed')
    os.chdir(settings.get('DEV_WORKSPACE_FOLDER'))
    # `serve` opens no browser, so DISPLAY stays for graphical tools OpenCode runs.
    port = settings.get('AGENTDEV_OPENCODE_PORT')
    os.execvp('opencode', ['opencode', 'serve', '--port', port, '--hostname', '0.0.0.0'])


def has_session() -> bool:
    command = ['tmux', '-L', SESSION, 'has-session', '-t', f'={SESSION}']
    return subprocess.run(command, capture_output=True, check=False).returncode == 0


def coder_start(settings: env.Settings) -> int:
    """Start the server in its own tmux server for the Coder agent, or report the live one."""
    for command in ('opencode', 'tmux'):
        if shutil.which(command) is None:
            print(f'{command} is not installed; skipping OpenCode web startup.', file=sys.stderr)
            return 0
    url, hostname, note = link(settings), coder_hostname(settings), coder_note(settings)
    running = f"OpenCode web tmux session '{SESSION}' is already running: {url}{note}"
    if has_session():
        print(running)
        return 0
    start = [
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
        settings.get('DEV_WORKSPACE_FOLDER'),
        coder_pane(settings),
    ]
    result = subprocess.run(start, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        if has_session():
            print(running)
            return 0
        print(
            f'Failed to start OpenCode web: {(result.stdout + result.stderr).strip()}',
            file=sys.stderr,
        )
        return 1
    print(f"Started OpenCode web in tmux session '{SESSION}' on {hostname}:4096: {url}{note}")
    return 0


def main(argv: list[str]) -> int:
    commands = {
        'serve': serve,
        'probe': lambda s: 0 if probe(s) else 1,
        'link': None,
        'coder-start': coder_start,
    }
    if len(argv) != 1 or argv[0] not in commands:
        print(f'usage: agentdev-runtime opencode {"|".join(commands)}', file=sys.stderr)
        return 2
    settings = env.Settings()
    if argv[0] == 'link':
        print(link(settings))
        return 0
    try:
        return commands[argv[0]](settings)
    except OpenCodeError as error:
        print(f'{PREFIX}: {error}', file=sys.stderr)
        return 1
