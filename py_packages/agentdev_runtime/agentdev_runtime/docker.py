"""
The runtime's own nested Docker engine, and the garbage collection that runs once it is up.

Exactly one root dockerd on a private Unix socket over per-instance storage, with no TCP
listener and no host socket. See ADR-0079.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
from typing import NoReturn

from agentdev_runtime import settings as env

PREFIX = 'agentdev-runtime docker'
# Without CAP_SYS_ADMIN, dockerd cannot mount its storage.
CAP_SYS_ADMIN = 21
GC_AGE = timedelta(hours=72)
CACHE_LIMIT = '10GB'
# Volumes a collection may remove; every other volume is never touched.
# See ADR-0073.
DISPOSABLE_VOLUME = re.compile(
    r'(^|_)dind-var-lib-(docker|containerd)-|_agentdev-(cache|cbm|codex)$'
)


class DockerError(Exception):
    """A preflight refused to start the engine."""


def require_privileges(proc_status: Path) -> None:
    if os.geteuid() != 0:
        raise DockerError('dockerd must run as root')
    for line in proc_status.read_text().splitlines():
        if line.startswith('CapEff:'):
            if (int(line.split()[1], 16) >> CAP_SYS_ADMIN) & 1:
                return
            break
    raise DockerError('nested Docker needs a privileged container (compose: privileged: true)')


def require_storage(data_dir: Path) -> None:
    data_dir.mkdir(parents=True, exist_ok=True)
    fs_type = subprocess.run(
        ['stat', '-f', '-c', '%T', str(data_dir)], check=True, capture_output=True, text=True
    ).stdout.strip()
    if fs_type == 'overlayfs':
        raise DockerError(
            f"{data_dir} is on the container's overlay filesystem; mount a volume there"
        )


def require_private_endpoint(config: Path, socket: Path) -> None:
    if not config.is_file():
        raise DockerError(f'{config} is missing')
    # dockerd also refuses a hosts key alongside --host, so any listener here is an error.
    try:
        hosts = json.loads(config.read_text()).get('hosts') or []
    except (ValueError, AttributeError) as error:
        raise DockerError(f'{config} is not a JSON object: {error}') from error
    if hosts:
        raise DockerError(
            f'{config} declares listeners (hosts); the engine listens only on {socket}'
        )


def require_single_engine(pidfile: Path, socket: Path) -> None:
    """Refuse when a live dockerd holds the pid file; clear a stale one."""
    if not pidfile.is_file():
        return
    pid = pidfile.read_text().strip()
    if pid:
        try:
            comm = Path(f'/proc/{pid}/comm').read_text().strip()
        except OSError:
            comm = ''
        if comm == 'dockerd':
            raise DockerError(f'dockerd is already running as pid {pid}')
    pidfile.unlink(missing_ok=True)
    socket.unlink(missing_ok=True)


def run(settings: env.Settings) -> NoReturn | int:
    data_dir = settings.path('AGENTDEV_DOCKER_DATA_DIR')
    socket = settings.path('AGENTDEV_DOCKER_SOCKET')
    config = settings.path('AGENTDEV_DOCKER_CONFIG')
    pidfile = settings.path('AGENTDEV_DOCKER_PIDFILE')
    try:
        require_privileges(settings.path('AGENTDEV_PROC_STATUS'))
        require_storage(data_dir)
        require_private_endpoint(config, socket)
        require_single_engine(pidfile, socket)
    except DockerError as error:
        print(f'{PREFIX}: {error}', file=sys.stderr, flush=True)
        return 1
    command = [
        'dockerd',
        '--config-file',
        str(config),
        '--data-root',
        str(data_dir),
        '--exec-root',
        settings.get('AGENTDEV_DOCKER_EXEC_ROOT'),
        '--pidfile',
        str(pidfile),
        '--host',
        f'unix://{socket}',
        '--group',
        'docker',
    ]
    os.execvp(command[0], command)


def _docker(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ['docker', *args], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False
    )


def _step(name: str, *args: str) -> subprocess.CompletedProcess[str]:
    """Run one collection step; a failure is only a warning."""
    result = _docker(*args)
    if result.returncode != 0:
        print(result.stdout.rstrip('\n'), file=sys.stderr)
        print(f'Warning: {name} failed; continuing.', file=sys.stderr, flush=True)
    else:
        for line in result.stdout.splitlines():
            if line.startswith('Total'):
                print(f'{name}: {line}', flush=True)
    return result


def _old_disposable_volumes(now: datetime) -> list[str]:
    listed = _step('volume listing', 'volume', 'ls', '-q', '--filter', 'dangling=true')
    names = [n for n in listed.stdout.split() if DISPOSABLE_VOLUME.search(n)]
    if listed.returncode != 0 or not names:
        return []
    inspected = _step(
        'volume inspection', 'volume', 'inspect', '--format', '{{.Name}} {{.CreatedAt}}', *names
    )
    old = []
    for line in inspected.stdout.splitlines():
        name, _, created = line.partition(' ')
        try:
            if now - datetime.fromisoformat(created.strip()) > GC_AGE:
                old.append(name)
        except ValueError:
            print(f'Warning: unreadable creation time for volume {name}', file=sys.stderr)
    return old


def gc() -> int:
    """Run one collection pass: old unused images, cache over its cap, old disposable volumes."""
    if shutil.which('docker') is None:
        print('docker is not installed; skipping garbage collection.')
        return 0
    if subprocess.run(['docker', 'info'], capture_output=True, check=False).returncode != 0:
        print('The Docker daemon is unreachable; skipping garbage collection.')
        return 0
    hours = int(GC_AGE.total_seconds() // 3600)
    _step('image prune', 'image', 'prune', '-af', '--filter', f'until={hours}h')
    _step('build cache prune', 'builder', 'prune', '-f', '--max-used-space', CACHE_LIMIT)
    old = _old_disposable_volumes(datetime.now(timezone.utc))
    if old:
        _step('volume removal', 'volume', 'rm', *old)
    return 0


def gc_every(settings: env.Settings) -> NoReturn:
    """Run a collection pass now, then one every AGENTDEV_DOCKER_GC_INTERVAL seconds."""
    interval = settings.positive('AGENTDEV_DOCKER_GC_INTERVAL')
    for error in settings.errors:
        print(f'{PREFIX}: {error}', file=sys.stderr, flush=True)
    while True:
        gc()
        time.sleep(interval)


def main(argv: list[str]) -> int:
    if argv == ['run']:
        return run(env.Settings())
    if argv == ['gc']:
        return gc()
    if argv == ['gc', '--every']:
        gc_every(env.Settings())
    print('usage: agentdev-runtime docker run|gc [--every]', file=sys.stderr)
    return 2
