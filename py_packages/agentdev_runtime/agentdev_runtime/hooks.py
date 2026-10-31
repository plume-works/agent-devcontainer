"""
A phase's image-installed executable hooks, run in C-locale name order.

A mounted workspace never contributes hooks. Spec: agentdev-runtime-images.
"""

from __future__ import annotations

import os
import subprocess
import sys

from agentdev_runtime import settings as env

PREFIX = 'agentdev-runtime lifecycle hooks'
PHASES = ('created', 'started', 'attached')


class HookError(Exception):
    """A hook failed, or the hook directory is not the image's."""


def run(settings: env.Settings, phase: str) -> None:
    hooks_dir = settings.path('AGENTDEV_HOOKS_ROOT') / f'{phase}.d'
    if not hooks_dir.is_dir():
        return
    workspace = settings.raw('DEV_WORKSPACE_FOLDER')
    if workspace:
        resolved = os.path.realpath(hooks_dir)
        checkout = os.path.realpath(workspace)
        if resolved == checkout or resolved.startswith(checkout.rstrip('/') + '/'):
            raise HookError(
                f'hook directory {hooks_dir} is inside the workspace {workspace}; hooks come '
                'from the image'
            )
    # C-locale order is byte order.
    for hook in sorted(hooks_dir.iterdir(), key=lambda path: os.fsencode(path.name)):
        if not hook.is_file() or not os.access(hook, os.X_OK):
            print(f'{PREFIX}: skipping {hook.name} in the {phase} phase: not an executable file')
            continue
        print(f'{PREFIX}: running {hook.name} in the {phase} phase', flush=True)
        status = subprocess.run(
            [str(hook)], env={**os.environ, 'AGENTDEV_LIFECYCLE_PHASE': phase}, check=False
        ).returncode
        if status != 0:
            raise HookError(f'hook {hook.name} failed in the {phase} phase (exit status {status})')


def main(argv: list[str]) -> int:
    if len(argv) != 1 or argv[0] not in PHASES:
        print(f'usage: agentdev-runtime lifecycle hooks {"|".join(PHASES)}', file=sys.stderr)
        return 2
    try:
        run(env.Settings(), argv[0])
    except HookError as error:
        print(f'{PREFIX}: {error}', file=sys.stderr)
        return 1
    return 0
