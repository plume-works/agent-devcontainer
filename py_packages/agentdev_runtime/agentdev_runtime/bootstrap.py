"""
Root bootstrap PID 1 runs before supervisord.

Deploy creates or reuses the runtime account, then validates and initializes only its own
storage; a Dev Container keeps the tool's account and mounts. Ownership is never rewritten
recursively. Spec: standalone-opencode-runtime, agentdev-runtime-images.
"""

from __future__ import annotations

from dataclasses import dataclass
import fcntl
import grp
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import sys
import time
from typing import NoReturn

from agentdev_runtime import firewall as egress, integrity, settings as env

PREFIX = 'agentdev-runtime bootstrap'
MAX_ID = 2147483647
AGENTS = ('claude', 'codex', 'opencode')


class BootstrapError(Exception):
    """The bootstrap refuses to continue; the message names the remedy."""


def log(message: str) -> None:
    print(f'{PREFIX}: {message}', flush=True)


def fail(message: str) -> NoReturn:
    raise BootstrapError(message)


def validate_id(name: str, value: str) -> int:
    if not re.fullmatch(r'[0-9]+', value):
        fail(f"{name} must be a numeric ID, got '{value}'")
    number = int(value, 10)
    if not 1 <= number <= MAX_ID:
        fail(f'{name} must be between 1 and {MAX_ID}; root (0) is not a runtime identity')
    return number


def owner_of(path: Path) -> tuple[int, int]:
    info = path.stat()
    return info.st_uid, info.st_gid


def is_empty_dir(path: Path) -> bool:
    if not path.is_dir():
        return False
    with os.scandir(path) as entries:
        return next(entries, None) is None


def group_by_gid(gid: int) -> grp.struct_group | None:
    try:
        return grp.getgrgid(gid)
    except KeyError:
        return None


def group_exists(name: str) -> bool:
    try:
        grp.getgrnam(name)
    except KeyError:
        return False
    return True


def account(name: str) -> pwd.struct_passwd | None:
    try:
        return pwd.getpwnam(name)
    except KeyError:
        return None


def account_by_uid(uid: int) -> pwd.struct_passwd | None:
    try:
        return pwd.getpwuid(uid)
    except KeyError:
        return None


def run(*command: str) -> None:
    subprocess.run(command, check=True)


@dataclass
class Identity:
    user: str
    uid: int
    gid: int
    home: Path

    @property
    def owner(self) -> tuple[int, int]:
        return self.uid, self.gid

    def as_user(self, *command: str) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            [
                'setpriv',
                f'--reuid={self.uid}',
                f'--regid={self.gid}',
                '--init-groups',
                '--',
                *command,
            ],
            check=False,
        )


def add_to_docker_group(user: str) -> None:
    if group_exists('docker'):
        run('usermod', '--append', '--groups', 'docker', user)


def reset_runtime_dir(runtime_dir: Path, identity: Identity) -> None:
    if runtime_dir.is_symlink() or runtime_dir.is_file():
        runtime_dir.unlink()
    elif runtime_dir.exists():
        shutil.rmtree(runtime_dir)
    run(
        'install',
        '-d',
        '-m',
        '700',
        '-o',
        str(identity.uid),
        '-g',
        str(identity.gid),
        str(runtime_dir),
    )


class Deploy:
    """The deploy profile's account and instance storage."""

    def __init__(self, settings: env.Settings) -> None:
        self.settings = settings
        user = settings.get('AGENTDEV_USER')
        self.identity = Identity(
            user=user,
            uid=validate_id('AGENTDEV_UID', settings.get('AGENTDEV_UID')),
            gid=validate_id('AGENTDEV_GID', settings.get('AGENTDEV_GID')),
            home=Path(settings.raw('AGENTDEV_HOME') or f'/home/{user}'),
        )
        self.require_mounts = settings.get('AGENTDEV_REQUIRE_MOUNTS') == '1'

    def ensure_group(self) -> None:
        ident = self.identity
        existing = group_by_gid(ident.gid)
        if existing is not None:
            log(f'reusing group {existing.gr_name} ({ident.gid}) as the primary group')
            return
        if group_exists(ident.user):
            fail(f'group {ident.user} exists with another GID; it cannot become GID {ident.gid}')
        run('groupadd', '--gid', str(ident.gid), ident.user)

    def ensure_account(self) -> None:
        ident = self.identity
        by_uid = account_by_uid(ident.uid)
        if by_uid is not None and by_uid.pw_name != ident.user:
            fail(
                f'UID {ident.uid} already belongs to account {by_uid.pw_name}; '
                'choose another AGENTDEV_UID'
            )
        by_name = account(ident.user)
        if by_name is not None:
            if (by_name.pw_uid, by_name.pw_gid, by_name.pw_dir) != (
                ident.uid,
                ident.gid,
                str(ident.home),
            ):
                fail(
                    f'account {ident.user} exists as {by_name.pw_uid}:{by_name.pw_gid} home '
                    f'{by_name.pw_dir}, not {ident.uid}:{ident.gid} home {ident.home}; '
                    'recreate the container'
                )
            log(f'reusing account {ident.user} ({ident.uid}:{ident.gid})')
        else:
            run(
                'useradd',
                '--no-create-home',
                '--uid',
                str(ident.uid),
                '--gid',
                str(ident.gid),
                '--home-dir',
                str(ident.home),
                '--shell',
                '/bin/bash',
                ident.user,
            )
            log(f'created account {ident.user} ({ident.uid}:{ident.gid})')
        add_to_docker_group(ident.user)

    def ensure_sudo(self) -> None:
        sudoers = self.settings.path('AGENTDEV_SUDOERS_FILE')
        staged = sudoers.with_name(sudoers.name + '.new')
        sudoers.parent.mkdir(parents=True, exist_ok=True)
        staged.write_text(f'{self.identity.user} ALL=(ALL:ALL) NOPASSWD: ALL\n')
        staged.chmod(0o440)
        if subprocess.run(['visudo', '-cqf', str(staged)], check=False).returncode != 0:
            fail('generated sudoers entry failed validation')
        staged.replace(sudoers)

    def require_mount(self, path: Path, purpose: str) -> None:
        if not self.require_mounts:
            return
        if subprocess.run(['mountpoint', '-q', str(path)], check=False).returncode != 0:
            fail(
                f'{path} is not a mounted volume; its {purpose} would be lost when the '
                'container is replaced'
            )

    def claim_instance_dir(self, path: Path, purpose: str) -> None:
        """Make an empty mount root the runtime user's; a populated one must already be."""
        self.require_mount(path, purpose)
        if not path.is_dir():
            fail(f'{path} ({purpose}) is missing')
        owner = owner_of(path)
        if owner == self.identity.owner:
            return
        if is_empty_dir(path):
            os.chown(path, *self.identity.owner)
            log(f'initialized empty {purpose} at {path}')
            return
        fail(
            f'{path} ({purpose}) is owned by {owner[0]}:{owner[1]}, not '
            f'{self.identity.uid}:{self.identity.gid}; it belongs to another identity'
        )

    def validate_workspace(self) -> None:
        workspace = self.settings.path('DEV_WORKSPACE_FOLDER')
        ident = self.identity
        self.require_mount(workspace, 'checkout')
        if not workspace.is_dir():
            fail(f'workspace {workspace} is missing; mount a checkout or a volume there')
        if is_empty_dir(workspace) and owner_of(workspace) != ident.owner:
            os.chown(workspace, *ident.owner)
            log(f'initialized empty workspace at {workspace}')
        if ident.as_user('test', '-w', str(workspace)).returncode != 0:
            fail(
                f'workspace {workspace} is not writable by {ident.uid}:{ident.gid}; '
                'match AGENTDEV_UID/AGENTDEV_GID to the checkout owner'
            )

    def prepare_shared_auth(self) -> None:
        """Serialize containers sharing one credential volume; only the first writes."""
        auth = self.settings.path('AGENTDEV_AGENTS_AUTH_DIR')
        self.require_mount(auth, 'shared agent credentials')
        if not auth.is_dir():
            fail(f'shared auth directory {auth} is missing')
        timeout = float(self.settings.get('AGENTDEV_AUTH_LOCK_TIMEOUT'))
        descriptor = os.open(auth, os.O_RDONLY)
        try:
            lock(descriptor, timeout, auth)
            if is_empty_dir(auth):
                os.chown(auth, *self.identity.owner)
                auth.chmod(0o700)
                for agent in AGENTS:
                    made = self.identity.as_user('install', '-d', '-m', '700', str(auth / agent))
                    if made.returncode != 0:
                        fail(f'could not create {auth / agent}')
                log(f'initialized empty shared auth volume at {auth}')
            else:
                for entry in [auth, *sorted(auth.iterdir())]:
                    uid = entry.lstat().st_uid
                    if uid != self.identity.uid:
                        fail(
                            f'shared auth entry {entry} is owned by UID {uid}; containers '
                            f'sharing {auth} must all use AGENTDEV_UID={uid}'
                        )
        finally:
            os.close(descriptor)

    def run(self) -> None:
        ident = self.identity
        self.ensure_group()
        self.ensure_account()
        self.ensure_sudo()
        self.claim_instance_dir(ident.home, 'home and client configuration')
        self.claim_instance_dir(self.settings.path('AGENTDEV_UV_DIR'), 'uv cache and environments')
        self.require_mount(self.settings.path('AGENTDEV_DOCKER_DATA_DIR'), 'nested Docker storage')
        self.validate_workspace()
        self.prepare_shared_auth()
        runtime_dir = Path(self.settings.raw('XDG_RUNTIME_DIR') or f'/run/user/{ident.uid}')
        reset_runtime_dir(runtime_dir, ident)
        log(f'identity {ident.user} ({ident.uid}:{ident.gid}) ready')


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


def devcontainer(settings: env.Settings) -> None:
    """Accept the Dev Container tool's account, mounts, and checkout as they are."""
    user = settings.get('AGENTDEV_USER')
    entry = account(user)
    if entry is None:
        fail(f'account {user} does not exist; AGENTDEV_USER must name an account in the image')
    ident = Identity(user, entry.pw_uid, entry.pw_gid, Path(entry.pw_dir))
    if ident.uid != 0:
        add_to_docker_group(user)
    # Container storage: it survives a restart and is gone after a rebuild, like the create phase.
    run(
        'install',
        '-d',
        '-m',
        '0755',
        '-o',
        str(ident.uid),
        '-g',
        str(ident.gid),
        settings.get('AGENTDEV_LIFECYCLE_DIR'),
    )
    reset_runtime_dir(Path(settings.raw('XDG_RUNTIME_DIR') or f'/run/user/{ident.uid}'), ident)
    workspace = settings.raw('DEV_WORKSPACE_FOLDER') or '/workspaces/project'
    log(f'accepted account {user} ({ident.uid}:{ident.gid}) and workspace {workspace} as mounted')


def firewall(settings: env.Settings) -> int:
    """Apply the firewall last, before supervisord starts dockerd."""
    return egress.apply(settings)


def main(argv: list[str]) -> int:
    if argv:
        print('usage: agentdev-runtime bootstrap', file=sys.stderr)
        return 2
    settings = env.Settings()
    try:
        integrity.verify()
        mode = settings.raw('AGENTDEV_RUNTIME_MODE')
        if mode == env.DEPLOY:
            Deploy(settings).run()
        elif mode == env.DEVCONTAINER:
            devcontainer(settings)
        else:
            fail(f"AGENTDEV_RUNTIME_MODE must be deploy or devcontainer; got '{mode}'")
    except BootstrapError as error:
        print(f'{PREFIX}: {error}', file=sys.stderr, flush=True)
        return 1
    except integrity.IntegrityError as error:
        print(f'{PREFIX}: {error}', file=sys.stderr, flush=True)
        return 1
    except subprocess.CalledProcessError as error:
        print(f'{PREFIX}: {error}', file=sys.stderr, flush=True)
        return 1
    return firewall(settings)
