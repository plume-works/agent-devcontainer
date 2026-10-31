"""
The Dev Container lifecycle commands: create, start, and attach phases.

``created`` prepares client state, project dependencies and hooks, and the staged catalog;
``ready`` waits for the supervised runtime and repairs per-start state; ``attached`` indexes,
syncs, and layers a complete checkout catalog. Spec: agentdev-runtime-images, catalog-lifecycle.
"""

from __future__ import annotations

import contextlib
import io
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from agentdev_runtime import (
    agent_state,
    catalog,
    cbm,
    git,
    health,
    hooks,
    project,
    settings as env,
    workspace as checkout,
)

PREFIX = 'agentdev-runtime lifecycle'
UV_MOUNT = Path('/uv')


class LifecycleError(Exception):
    """A phase cannot complete; the message names why."""


class NotReady(LifecycleError):
    """The supervised runtime failed or did not become ready in time."""


def workspace_of(settings: env.Settings) -> str:
    """Return the checkout and export it, so every step and hook sees the same one."""
    folder = settings.get('DEV_WORKSPACE_FOLDER')
    os.environ['DEV_WORKSPACE_FOLDER'] = folder
    return folder


def created_marker(settings: env.Settings) -> Path:
    """Container storage, made by the bootstrap: gone after a rebuild, kept across a restart."""
    return settings.path('AGENTDEV_LIFECYCLE_DIR') / 'created'


def claim_ancestors(owner: str, directory: str) -> None:
    """Own a checkout's or home's ancestors; CBM rejects one another UID owns."""
    while directory and directory != '/':
        subprocess.run(['sudo', 'chown', owner, directory], check=True)
        directory = os.path.dirname(directory)


def claim_mounts(owner: str) -> None:
    """Named volumes are created root-owned; claim /uv only when it is mounted."""
    if UV_MOUNT.exists():
        subprocess.run(['sudo', 'chown', '-R', owner, str(UV_MOUNT)], check=True)
    else:
        print(f'{UV_MOUNT} is not mounted; skipping its ownership fix.')


def check(status: int, step: str) -> None:
    if status != 0:
        raise LifecycleError(f'{step} failed (exit status {status})')


def created(settings: env.Settings) -> None:
    """Run the create phase, idempotently, then mark it done."""
    folder = workspace_of(settings)
    owner = f'{os.getuid()}:{os.getgid()}'
    if os.getuid() == 0:
        claim_ancestors(owner, folder)
        claim_ancestors(owner, str(Path.home()))
    claim_mounts(owner)
    # Before the project's hooks: pre-commit refuses a checkout another UID owns until trusted.
    git.safe_directory(settings)
    with agent_state.config_lock(settings):
        agent_state.create(settings)
    checkout.Workspace(settings).project()
    # The client-state volumes shadow the build-time install, so install the staged catalog
    # again at user scope; the attach phase layers a complete checkout catalog on top.
    staged = settings.raw('AGENTDEV_CATALOG_DIR')
    if staged and Path(staged).is_dir():
        with agent_state.config_lock(settings):
            catalog.install(settings, staged, 'user')
    else:
        print('No catalog staged in the image; skipping the image-scoped plugin install.')
    hooks.run(settings, 'created')
    marker = created_marker(settings)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()


def wait_created(settings: env.Settings) -> None:
    marker = created_marker(settings)
    while not marker.is_file():
        time.sleep(1)


def quietly(call, *args) -> tuple[int, str]:
    """Run a health call, returning its status and what it printed."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        status = call(*args)
    return status, out.getvalue()


def wait_ready(settings: env.Settings) -> None:
    timeout = float(settings.get('AGENTDEV_READY_TIMEOUT'))
    deadline = time.monotonic() + timeout
    while quietly(health.ready, settings)[0] != 0:
        first = (quietly(health.status, settings)[1].splitlines() or [''])[0]
        if first == 'runtime state: failed':
            raise NotReady('the runtime failed; the editor cannot attach')
        if time.monotonic() >= deadline:
            raise NotReady(f'the runtime was not ready within {timeout:g}s')
        time.sleep(1)
    print(f"{PREFIX}: the runtime's required services are ready", flush=True)


def start_cbm(settings: env.Settings) -> None:
    """Start the CBM daemon a start with no supervisor has, when the image ships CBM."""
    if shutil.which('codebase-memory-mcp') is None:
        print('codebase-memory-mcp is not installed; skipping the CBM daemon start.')
        return
    try:
        cbm.Daemon(settings).start()
    except cbm.CbmError as error:
        raise LifecycleError(f'the CBM daemon did not start: {error}') from error


def ready(settings: env.Settings, wait: bool) -> None:
    """Run the start phase; without a supervisor, start CBM, then repair per-start state."""
    workspace_of(settings)
    if wait:
        wait_ready(settings)
    else:
        start_cbm(settings)
    git.safe_directory(settings)
    # After the keyring: gh may keep its login there.
    check(git.credential_helper(settings), 'the git credential helper setup')
    # Repairs the shared auth.json symlink a `codex logout` can destroy.
    agent_state.link_codex_auth(settings)
    with agent_state.config_lock(settings):
        agent_state.apply_agent_policy()
    hooks.run(settings, 'started')


def attached(settings: env.Settings) -> None:
    """Run the attach phase: index request, project environment, catalog, attached hooks."""
    folder = workspace_of(settings)
    subprocess.run(['git', 'config', '--global', 'gpg.ssh.program', 'ssh-keygen'], check=True)
    if shutil.which('codebase-memory-mcp') is not None:
        try:
            cbm.Daemon(settings).index(folder)
        except cbm.CbmError as error:
            raise LifecycleError(str(error)) from error
    if (Path(folder) / 'pyproject.toml').is_file():
        check(project.sync(settings), 'uv sync')
    if catalog.complete(Path(folder)):
        with agent_state.config_lock(settings):
            catalog.install(settings, folder, None)
    else:
        print(f'{folder} ships no complete agentdev catalog; keeping the staged catalog.')
    hooks.run(settings, 'attached')


def main(argv: list[str]) -> int:
    usage = (
        'usage: agentdev-runtime lifecycle created [--wait] | ready [--no-wait] | attached'
        ' | hooks created|started|attached'
    )
    if argv[:1] == ['hooks']:
        return hooks.main(argv[1:])
    settings = env.Settings()
    commands = {
        ('created',): lambda: created(settings),
        ('created', '--wait'): lambda: wait_created(settings),
        ('ready',): lambda: ready(settings, wait=True),
        ('ready', '--no-wait'): lambda: ready(settings, wait=False),
        ('attached',): lambda: attached(settings),
    }
    command = commands.get(tuple(argv))
    if command is None:
        print(usage, file=sys.stderr)
        return 2
    try:
        command()
    except (
        LifecycleError,
        hooks.HookError,
        checkout.WorkspaceError,
        agent_state.StateError,
        catalog.CatalogError,
        subprocess.CalledProcessError,
    ) as error:
        print(f'{PREFIX}: {error}', file=sys.stderr, flush=True)
        if isinstance(error, NotReady):
            with contextlib.redirect_stdout(sys.stderr):
                health.status(settings)
        return 1
    return 0
