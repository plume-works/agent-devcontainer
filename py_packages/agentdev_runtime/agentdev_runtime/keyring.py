"""
Instance-local D-Bus session and GNOME Keyring Secret Service, one supervised piece each.

The login keyring is created with an empty password, so its secrets are stored unencrypted:
the container boundary, not the keyring, protects them. Spec: standalone-opencode-runtime.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import time

from agentdev_runtime import settings as env

PREFIX = 'agentdev-runtime keyring'
BUS_ID = (
    'gdbus',
    'call',
    '--session',
    '--dest',
    'org.freedesktop.DBus',
    '--object-path',
    '/org/freedesktop/DBus',
)
LOGIN_KEYRING = """[keyring]
display-name=login
ctime={ctime}
mtime=0
lock-on-idle=false
lock-after=false
"""


def bus_answers(environ: dict[str, str], *method: str) -> bool:
    command = [*BUS_ID, '--method', *method]
    return subprocess.run(command, env=environ, capture_output=True, check=False).returncode == 0


def session_ready(environ: dict[str, str]) -> bool:
    """Return whether the Secret Service owns its name on the session bus."""
    if not environ.get('DBUS_SESSION_BUS_ADDRESS'):
        return False
    return bus_answers(environ, 'org.freedesktop.DBus.GetNameOwner', 'org.freedesktop.secrets')


def ensure_login_keyring(home: Path) -> None:
    """Create the login keyring once; an existing one is the secret store itself."""
    directory = home / '.local/share/keyrings'
    directory.mkdir(parents=True, exist_ok=True)
    keyring = directory / 'login.keyring'
    if keyring.exists():
        return
    keyring.write_text(LOGIN_KEYRING.format(ctime=int(time.time())))
    keyring.chmod(0o600)


def wait_until(predicate, timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while not predicate():
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.1)
    return True


def main(argv: list[str]) -> int:
    command = argv[0] if argv else ''
    if command not in {'dbus', 'keyring', 'check', 'wait'} or (
        len(argv) > 1 and command != 'wait'
    ):
        print('usage: agentdev-runtime keyring dbus|keyring|check|wait [seconds]', file=sys.stderr)
        return 2
    settings = env.Settings()
    runtime_dir = settings.raw('XDG_RUNTIME_DIR')
    if not runtime_dir:
        print(f'{PREFIX}: XDG_RUNTIME_DIR is required', file=sys.stderr)
        return 1
    bus_socket = Path(runtime_dir) / 'bus'
    environ = {**os.environ, 'DBUS_SESSION_BUS_ADDRESS': f'unix:path={bus_socket}'}
    timeout = float(settings.get('AGENTDEV_SERVICE_START_TIMEOUT'))
    if command == 'dbus':
        Path(runtime_dir).mkdir(parents=True, exist_ok=True)
        Path(runtime_dir).chmod(0o700)
        # A socket left by a killed daemon would make the bind fail.
        bus_socket.unlink(missing_ok=True)
        daemon = ['dbus-daemon', '--session', '--nofork', '--nopidfile']
        os.execvpe(
            daemon[0], [*daemon, f'--address={environ["DBUS_SESSION_BUS_ADDRESS"]}'], environ
        )
    if command == 'keyring':
        if not wait_until(lambda: bus_answers(environ, 'org.freedesktop.DBus.GetId'), timeout):
            print(f'{PREFIX}: D-Bus session bus at {bus_socket} is not available', file=sys.stderr)
            return 1
        ensure_login_keyring(Path(os.environ.get('HOME') or Path.home()))
        daemon = ['gnome-keyring-daemon', '--foreground', '--components=secrets']
        os.execvpe(daemon[0], daemon, environ)
    if command == 'check':
        return 0 if session_ready(environ) else 1
    seconds = float(argv[1]) if len(argv) > 1 else timeout
    if not wait_until(lambda: session_ready(environ), seconds):
        print('Timeout waiting for org.freedesktop.secrets to become available', file=sys.stderr)
        return 1
    return 0
