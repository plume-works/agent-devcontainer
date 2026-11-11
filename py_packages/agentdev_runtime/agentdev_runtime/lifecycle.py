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
import subprocess
import sys
import time

from agentdev_runtime import (
    agent_state,
    catalog,
    git,
    health,
    hooks,
    project,
    settings as env,
    workspace as checkout,
    worktree,
)

PREFIX = 'agentdev-runtime lifecycle'
PROJECT_MOUNT = Path('/workspaces/project')


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


def claim_project(settings: env.Settings) -> None:
    """Re-own the sibling checkout volume once, so its uncommitted work stays editable."""
    uid, gid = os.getuid(), os.getgid()
    if uid == 0 or not os.path.ismount(PROJECT_MOUNT):
        return
    if Path(settings.get('DEV_WORKSPACE_FOLDER')).resolve() == PROJECT_MOUNT:
        return
    if PROJECT_MOUNT.stat().st_uid == uid:
        return
    subprocess.run(['sudo', 'chown', '-R', f'{uid}:{gid}', str(PROJECT_MOUNT)], check=True)
    print(f'Re-owned {PROJECT_MOUNT} to {uid}:{gid}.')


def prepare_venv_root(settings: env.Settings) -> None:
    """Create an environment root inside the home: link-venv skips a root whose parent is absent."""
    root = Path(settings.get('AGENTDEV_VENV_ROOT'))
    if root.is_relative_to(settings.home):
        root.mkdir(parents=True, exist_ok=True)


def check(status: int, step: str) -> None:
    if status != 0:
        raise LifecycleError(f'{step} failed (exit status {status})')


def created(settings: env.Settings) -> None:
    """Run the create phase once per container, then mark it done."""
    marker = created_marker(settings)
    if marker.is_file():
        print(f'{PREFIX}: the create phase already ran in this container.')
        return
    # Hooks inherit the working directory; supervisord starts this phase elsewhere.
    os.chdir(workspace_of(settings))
    claim_project(settings)
    # Before the project's hooks: pre-commit refuses a checkout another UID owns until trusted.
    git.safe_directory(settings)
    with agent_state.config_lock(settings):
        agent_state.create(settings)
    prepare_venv_root(settings)
    checkout.Workspace(settings).project()
    # The client-state volumes shadow the build-time install, so install the staged catalog
    # again at user scope; the attach phase layers a complete checkout catalog on top.
    staged = settings.raw('AGENTDEV_CATALOG_DIR')
    if staged and Path(staged).is_dir():
        with agent_state.config_lock(settings):
            catalog.install(settings, staged, 'user')
    else:
        print('No catalog staged in the image; skipping the image-scoped plugin install.')
    # Before Remote Control starts: it reads the worktree hooks only then.
    if not project.deploy(settings):
        with agent_state.config_lock(settings):
            worktree.register()
    hooks.run(settings, 'created')
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()


def runtime_failed(settings: env.Settings) -> bool:
    first = (quietly(health.status, settings)[1].splitlines() or [''])[0]
    return first == 'runtime state: failed'


def wait_created(settings: env.Settings) -> None:
    """Wait for the supervised create phase, which runs only after the root bootstrap."""
    timeout = float(settings.get('AGENTDEV_READY_TIMEOUT'))
    deadline = time.monotonic() + timeout
    marker = created_marker(settings)
    while not marker.is_file():
        if runtime_failed(settings):
            raise NotReady('the runtime failed before the create phase finished')
        if time.monotonic() >= deadline:
            raise NotReady(f'the create phase did not finish within {timeout:g}s')
        time.sleep(1)
    print(f'{PREFIX}: the create phase finished', flush=True)


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
        if runtime_failed(settings):
            raise NotReady('the runtime failed; the editor cannot attach')
        if time.monotonic() >= deadline:
            raise NotReady(f'the runtime was not ready within {timeout:g}s')
        time.sleep(1)
    print(f"{PREFIX}: the runtime's required services are ready", flush=True)


def ready(settings: env.Settings, wait: bool) -> None:
    """Run the start phase: wait for a supervisor when there is one, then repair per-start state."""
    workspace_of(settings)
    if wait:
        wait_ready(settings)
    git.safe_directory(settings)
    # After the keyring: gh may keep its login there.
    check(git.credential_helper(settings), 'the git credential helper setup')
    with agent_state.config_lock(settings):
        agent_state.apply_agent_policy()
    hooks.run(settings, 'started')


def attached(settings: env.Settings) -> None:
    """Run the attach phase: project environment, catalog, attached hooks."""
    folder = workspace_of(settings)
    subprocess.run(['git', 'config', '--global', 'gpg.ssh.program', 'ssh-keygen'], check=True)
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
