"""
Per-service probes, the aggregate readiness both healthchecks read, and a status report.

``agentdev-runtime health <service>|ready|status`` exits 0 when ready.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import pwd
import shlex
import subprocess
import sys

from agentdev_runtime import settings as env, state as files
from agentdev_runtime.supervisor import RETRY_COMMAND

SERVICES = ('dockerd', 'dbus', 'keyring', 'cbm', 'xpra', 'opencode', 'remote-control')
# The session bus and the CBM rendezvous admit only the account that owns them.
USER_SERVICES = frozenset({'dbus', 'keyring', 'cbm', 'opencode', 'xpra', 'remote-control'})
SELF = (sys.executable, '-m', 'agentdev_runtime')
USAGE = f'usage: agentdev-runtime health {"|".join(SERVICES)}|ready|status'


def _run(
    command: list[str], timeout: float | None = None, stdout: bool = True, stderr: bool = True
) -> bool:
    """Run a probe command; a timeout or a missing program is a failed probe."""
    try:
        result = subprocess.run(
            command,
            stdout=None if stdout else subprocess.DEVNULL,
            stderr=None if stderr else subprocess.DEVNULL,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return False
    except OSError as error:
        print(f'{command[0]}: {error}', file=sys.stderr)
        return False
    return result.returncode == 0


def _script(settings: env.Settings, name: str) -> str:
    """Return a runtime script not yet ported into the package."""
    return str(settings.path('AGENTDEV_RUNTIME_ROOT') / name)


def probe(settings: env.Settings, service: str) -> bool:
    if service == 'dockerd':
        return _run(['docker', 'info'], timeout=10, stdout=False, stderr=False)
    if service == 'dbus':
        return _run(
            [
                'gdbus',
                'call',
                '--session',
                '--dest',
                'org.freedesktop.DBus',
                '--object-path',
                '/org/freedesktop/DBus',
                '--method',
                'org.freedesktop.DBus.GetId',
            ],
            timeout=5,
            stdout=False,
            stderr=False,
        )
    if service == 'keyring':
        return _run([*SELF, 'keyring', 'check'], timeout=5)
    if service == 'cbm':
        return _run([_script(settings, 'runtime-cbm.sh'), 'check'], timeout=10, stderr=False)
    if service == 'xpra':
        port = settings.get('AGENTDEV_XPRA_PORT')
        return _run(
            ['curl', '-fsS', '-o', '/dev/null', '--max-time', '5', f'http://127.0.0.1:{port}/']
        )
    if service == 'opencode':
        return _run([*SELF, 'opencode', 'probe'])
    if service == 'remote-control':
        return _run([_script(settings, 'runtime-remote-control.sh'), 'check'])
    raise ValueError(service)


def _as_runtime_user(settings: env.Settings, service: str) -> int | None:
    """Re-run a user-scope probe as the runtime account when called as root; None to go on."""
    user = settings.raw('AGENTDEV_USER')
    if os.geteuid() != 0 or not user:
        return None
    try:
        account = pwd.getpwnam(user)
    except KeyError:
        print(f'id: {user}: no such user', file=sys.stderr)
        return 1
    if account.pw_uid == 0:
        return None
    home = settings.raw('AGENTDEV_HOME') or f'/home/{user}'
    command = [
        'setpriv',
        f'--reuid={user}',
        f'--regid={account.pw_gid}',
        '--init-groups',
        'env',
        f'HOME={home}',
        f'USER={user}',
        sys.executable,
        '-m',
        'agentdev_runtime',
        'health',
        service,
    ]
    os.execvp(command[0], command)
    return None


def ready(settings: env.Settings) -> int:
    """Pass only while a live controller reports ready and every core probe passes."""
    run = files.RunFiles(settings.path('AGENTDEV_RUN_DIR'))
    state, document = files.current(run.state)
    if state in {'stale', 'missing', 'unreadable'} or document.get('ready') is not True:
        print(f'runtime state: {state}')
        return 1
    probe_command = shlex.split(settings.raw('AGENTDEV_HEALTH_COMMAND')) or [
        sys.executable,
        '-m',
        'agentdev_runtime',
        'health',
    ]
    for core in document.get('probes') or []:
        if not _run([*probe_command, core], stdout=False, stderr=False):
            print(f'core probe failed: {core}')
            return 1
    return 0


def status(settings: env.Settings) -> int:
    run = files.RunFiles(settings.path('AGENTDEV_RUN_DIR'))
    state, _ = files.current(run.state)
    print(f'runtime state: {state}')
    try:
        document = json.loads(run.state.read_text())
    except FileNotFoundError:
        return 1
    except (OSError, json.JSONDecodeError):
        document = {}
    ready_word = 'true' if document.get('ready') else 'false'
    print(f'  profile: {document.get("profile") or "unknown"}, ready: {ready_word}')
    components = document.get('components') or {}
    for name, component in components.items():
        if component.get('status') not in {'failed', 'blocked'}:
            continue
        reason = f' ({component["reason"]})' if component.get('reason') else ''
        print(f'  {name}: {component["status"]}{reason}')
        if component['status'] == 'failed':
            print(f'    retry: docker exec <container> {RETRY_COMMAND} {name}')
    if 'remote-control' in components:
        runtime_dir = settings.raw('XDG_RUNTIME_DIR')
        try:
            rc_status = Path(f'{runtime_dir}/remote-control.status').read_text().strip()
        except OSError:
            rc_status = 'not started'
        print(f'  remote-control: {rc_status}')
    home = Path(settings.raw('AGENTDEV_HOME') or Path.home())
    record_path = files.failure_record(home)
    record = files.read_json(record_path) if record_path.is_file() else None
    if record is not None:
        exit_status = record.get('exit_status')
        print(
            f'last failure: {record.get("component")}, exit status '
            f'{"none" if exit_status is None else exit_status}, at {record.get("time")}'
        )
        print(f'  record: {record_path}')
    return 0 if files.current(run.state)[0] == 'ready' else 1


def main(argv: list[str]) -> int:
    """Dispatch ``agentdev-runtime health <service>|ready|status``."""
    service = argv[0] if argv else ''
    settings = env.Settings()
    if service in SERVICES:
        if service in USER_SERVICES:
            refused = _as_runtime_user(settings, service)
            if refused is not None:
                return refused
        return 0 if probe(settings, service) else 1
    if service == 'ready':
        return ready(settings)
    if service == 'status':
        return status(settings)
    print(USAGE, file=sys.stderr)
    return 2
