"""
Root bootstrap that ``agentdev-bootstrap.service`` runs before the Docker engine starts.

It hands the container's environment to the image's systemd units, initializes the runtime
account's storage, trusts the extra CA, and applies the firewall. The runtime never changes
ownership recursively. See ADR-0070 and ADR-0107.
"""

from __future__ import annotations

import fcntl
import os
from pathlib import Path
import pwd
import subprocess
import sys
import time
from typing import NoReturn

from agentdev_runtime import firewall as egress, integrity, settings as env, trust

PREFIX = 'agentdev-runtime bootstrap'
AGENTS = ('claude', 'opencode')
CONTAINER_ENVIRON = Path('/proc/1/environ')
ENVIRONMENT_FILE = Path('/run/agentdev/container.env')
# Set per process by the container engine or systemd; a unit gets its own.
NOT_FORWARDED = frozenset(
    {'HOME', 'USER', 'LOGNAME', 'SHELL', 'PWD', 'SHLVL', 'TERM', '_', 'NOTIFY_SOCKET'}
)


class BootstrapError(Exception):
    """The bootstrap refuses to continue; the message names the remedy."""


def log(message: str) -> None:
    print(f'{PREFIX}: {message}', flush=True)


def fail(message: str) -> NoReturn:
    raise BootstrapError(message)


def container_environment(source: Path = CONTAINER_ENVIRON) -> dict[str, str]:
    """Return the environment the container engine gave PID 1: ``-e`` and ``containerEnv``."""
    pairs = (item.split(b'=', 1) for item in source.read_bytes().split(b'\0') if b'=' in item)
    return {key.decode(): value.decode(errors='replace') for key, value in pairs}


def quote(value: str) -> str:
    """Quote a value for a systemd ``EnvironmentFile=``, which may span lines inside quotes."""
    escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('$', '\\$')
    return f'"{escaped.replace("`", "\\`")}"'


def write_environment_file(environ: dict[str, str], target: Path, gid: int) -> None:
    """Write the container's environment for the units, readable by the runtime account only."""
    lines = [
        f'{name}={quote(value)}\n'
        for name, value in sorted(environ.items())
        if name not in NOT_FORWARDED and name.replace('_', 'a').isalnum()
    ]
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = target.with_name(target.name + '.new')
    staged.write_text(''.join(lines))
    os.chown(staged, -1, gid)
    staged.chmod(0o640)
    staged.replace(target)


def is_empty_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    with os.scandir(path) as entries:
        return next(entries, None) is None


def as_user(account: pwd.struct_passwd, *command: str) -> int:
    return subprocess.run(
        [
            'setpriv',
            f'--reuid={account.pw_uid}',
            f'--regid={account.pw_gid}',
            '--init-groups',
            '--',
            *command,
        ],
        check=False,
    ).returncode


def claim_empty(path: Path, account: pwd.struct_passwd, purpose: str) -> None:
    """Make an empty mount root the runtime account's; a populated one must already be."""
    if not path.is_dir():
        fail(f'{path} ({purpose}) is missing')
    owner = path.stat().st_uid
    if owner == account.pw_uid:
        return
    if is_empty_dir(path):
        os.chown(path, account.pw_uid, account.pw_gid)
        log(f'initialized empty {purpose} at {path}')
        return
    fail(
        f'{path} ({purpose}) is owned by UID {owner}, not {account.pw_uid}; '
        'it belongs to another identity'
    )


def validate_workspace(settings: env.Settings, account: pwd.struct_passwd) -> None:
    folder = settings.raw('DEV_WORKSPACE_FOLDER')
    if not folder:
        return
    workspace = Path(folder)
    if not workspace.is_dir():
        fail(f'workspace {workspace} is missing; mount a checkout or a volume there')
    if is_empty_dir(workspace) and workspace.stat().st_uid != account.pw_uid:
        os.chown(workspace, account.pw_uid, account.pw_gid)
        log(f'initialized empty workspace at {workspace}')
    if as_user(account, 'test', '-w', str(workspace)) != 0:
        fail(
            f'workspace {workspace} is not writable by UID {account.pw_uid}; '
            'open the Dev Container as the host user who owns the checkout'
        )


def lock(descriptor: int, timeout: float, path: Path) -> None:
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return
        except BlockingIOError:
            if time.monotonic() >= deadline:
                fail(f'timed out waiting for the lock on {path}')
            time.sleep(0.1)


def prepare_shared_auth(settings: env.Settings, account: pwd.struct_passwd) -> None:
    """Serialize containers sharing one credential volume; only the first writes."""
    auth = settings.path('AGENTDEV_AGENTS_AUTH_DIR')
    # Without the auth volume, credentials live in container storage until a rebuild.
    auth.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(auth, os.O_RDONLY)
    try:
        lock(descriptor, float(settings.get('AGENTDEV_AUTH_LOCK_TIMEOUT')), auth)
        if is_empty_dir(auth):
            os.chown(auth, account.pw_uid, account.pw_gid)
            auth.chmod(0o700)
            for agent in AGENTS:
                if as_user(account, 'install', '-d', '-m', '700', str(auth / agent)) != 0:
                    fail(f'could not create {auth / agent}')
            log(f'initialized empty shared auth volume at {auth}')
            return
        for entry in [auth, *sorted(auth.iterdir())]:
            uid = entry.lstat().st_uid
            if uid != account.pw_uid:
                fail(
                    f'shared auth entry {entry} is owned by UID {uid}; containers '
                    f'sharing {auth} must all run as UID {uid}'
                )
    finally:
        os.close(descriptor)


def prepare_storage(settings: env.Settings, account: pwd.struct_passwd) -> None:
    if account.pw_uid != 0:
        claim_empty(Path(account.pw_dir), account, 'home and client configuration')
        validate_workspace(settings, account)
        prepare_shared_auth(settings, account)
    # Container storage: it survives a restart and is gone after a rebuild, like the create phase.
    lifecycle = settings.path('AGENTDEV_LIFECYCLE_DIR')
    lifecycle.mkdir(parents=True, exist_ok=True)
    os.chown(lifecycle, account.pw_uid, account.pw_gid)


def install_extra_ca(settings: env.Settings) -> None:
    """Trust the extra CA bundle before any service or tool makes a TLS connection."""
    source = settings.path('AGENTDEV_EXTRA_CA_CERTS')
    try:
        count = trust.install(source)
    except (trust.TrustError, OSError) as error:
        fail(f'extra CA bundle {source}: {error}')
    if count:
        log(f'trusted {count} extra CA certificate(s) from {source}')


def run(settings: env.Settings, environment_file: Path = ENVIRONMENT_FILE) -> int:
    integrity.verify()
    user = settings.get('AGENTDEV_USER')
    try:
        account = pwd.getpwnam(user)
    except KeyError:
        fail(f'account {user} does not exist; AGENTDEV_USER must name an account in the image')
    write_environment_file(dict(settings.environ), environment_file, account.pw_gid)
    prepare_storage(settings, account)
    install_extra_ca(settings)
    log(f'account {user} ({account.pw_uid}:{account.pw_gid}) ready')
    return egress.apply(settings)


def firewall_requested(environ: dict[str, str]) -> bool:
    """Read ``ENABLE_FIREWALL`` as ``Settings.boolean`` does; refuse an unrecognized value."""
    settings = env.Settings(environ=environ)
    requested = settings.boolean('ENABLE_FIREWALL')
    if settings.errors:
        fail(settings.errors[0])
    return requested


def main(argv: list[str]) -> int:
    if argv:
        print('usage: agentdev-runtime bootstrap', file=sys.stderr)
        return 2
    environ = container_environment()
    # An unrecognized ENABLE_FIREWALL value locks egress down until it is fixed.
    requested = True
    try:
        requested = firewall_requested(environ)
        # The firewall and the units read the exact word.
        environ['ENABLE_FIREWALL'] = 'true' if requested else 'false'
        return run(env.Settings(environ=environ))
    except (BootstrapError, integrity.IntegrityError, OSError) as error:
        print(f'{PREFIX}: {error}', file=sys.stderr, flush=True)
        if requested:
            egress.lock_down(egress.System())
        return 1
