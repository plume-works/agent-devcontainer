"""
The Coder agent's start, run by the template's ``coder_script`` on every agent start.

Spec: devcontainer-git-credentials, opencode-web, devcontainer-docker-storage.
"""

from __future__ import annotations

import os
import subprocess
import sys

from agentdev_runtime import settings as env

STEPS = (
    (('agentdev-runtime', 'docker', 'prune'), 'Docker image prune failed'),
    (('{root}/setup-gh-credential-helper.sh',), 'git credential helper setup failed'),
    (('agentdev-runtime', 'opencode', 'coder-start'), 'OpenCode web startup failed'),
)


def start(settings: env.Settings) -> int:
    """Run each preparation step as a warning on failure, then hand over to Remote Control."""
    root = str(settings.path('AGENTDEV_RUNTIME_ROOT'))
    for command, failure in STEPS:
        argv = [part.format(root=root) for part in command]
        try:
            status = subprocess.run(argv, check=False).returncode
        except OSError as error:
            print(f'{argv[0]}: {error}', file=sys.stderr)
            status = 127
        if status != 0:
            print(
                f'Warning: {failure}; starting Remote Control anyway.', file=sys.stderr, flush=True
            )
    remote_control = f'{root}/claude-remote-control-start.sh'
    os.execvp(remote_control, [remote_control])


def main(argv: list[str]) -> int:
    if argv != ['start']:
        print('usage: agentdev-runtime coder start', file=sys.stderr)
        return 2
    return start(env.Settings())
