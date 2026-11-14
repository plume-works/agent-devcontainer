"""
The Coder agent's start, run by the template's ``coder_script`` on every agent start.

The template in plume-works/coder-ide-baseline uses ``agentdev-runtime coder start`` as the
default value of its ``agent_start_script`` parameter. A rename of this command breaks it.

See ADR-0072.
"""

from __future__ import annotations

import os
import subprocess
import sys

from agentdev_runtime import settings as env

STEPS = (
    (('agentdev-runtime', 'git', 'credential-helper'), 'git credential helper setup failed'),
    (('agentdev-runtime', 'opencode', 'coder-start'), 'OpenCode web startup failed'),
)


def start(settings: env.Settings) -> int:
    """Run each preparation step as a warning on failure, then hand over to Remote Control."""
    for command, failure in STEPS:
        argv = list(command)
        try:
            status = subprocess.run(argv, check=False).returncode
        except OSError as error:
            print(f'{argv[0]}: {error}', file=sys.stderr)
            status = 127
        if status != 0:
            print(
                f'Warning: {failure}; starting Remote Control anyway.', file=sys.stderr, flush=True
            )
    os.execvp('agentdev-runtime', ['agentdev-runtime', 'remote-control', 'start'])


def main(argv: list[str]) -> int:
    if argv != ['start']:
        print('usage: agentdev-runtime coder start', file=sys.stderr)
        return 2
    return start(env.Settings())
