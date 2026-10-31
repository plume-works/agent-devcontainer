#!/usr/bin/env python3

"""Run a command on the session's codespace over SSH, from its workspace directory."""

from __future__ import annotations

import subprocess
import sys

import codespace_common as cs
from codespace_common import print_error, Stop
from skill_common import bash_quote

REMOTE_COMMAND_FAILED = 4
PREFLIGHT_ERROR = 2

DESCRIPTION = (
    'Run a command on the codespace (created by codespace-ensure.py, synced by '
    'codespace-sync.py) via SSH.'
)

USAGE = """
Usage:
  codespace-exec.py <command> [args...]

Runs '<command> [args...]' on the codespace, inside the repo's workspace
directory, over 'gh codespace ssh'. Everything after the script name is
forwarded verbatim as the remote command -- including '-h'/'--help', which
is passed through to the remote command rather than being intercepted by
this script. This help text is therefore printed only when no command is
given at all.

Output:
  The remote command's own stdout, verbatim, then the key=value lines
  REMOTE_EXIT_CODE and RESULT.

REMOTE_EXIT_CODE is the status 'gh codespace ssh' returned -- normally the
remote command's own exit status. This script does NOT exit with it: its own
exit code names its own outcome, so a remote command exiting 3 cannot be read
as this script's CODESPACE_SCOPE_MISSING. Branch on REMOTE_EXIT_CODE when the
remote command's exact status matters (a test runner's 1 versus 5).

Results (RESULT / exit code):
  SUCCESS                  0  The remote command ran and exited 0
  REMOTE_COMMAND_FAILED    4  'gh codespace ssh' exited non-zero: the remote command
                              failed, or the connection to the codespace did.
                              REMOTE_EXIT_CODE carries the status
  CODESPACE_SCOPE_MISSING  3  gh token is missing the 'codespace' OAuth scope
  PREFLIGHT_ERROR          2  No command given, not a repo, gh missing or
                              unauthenticated, or no recorded codespace name
  SCRIPT_FAILURE           1  Unhandled error

Examples:
  codespace-exec.py uv run pytest py_packages/validate_agent_files
  codespace-exec.py bun test
"""


def run(arguments: list[str]) -> int:
    """Run the command remotely and report its status."""
    if not arguments:
        print(cs.help_header(DESCRIPTION) + USAGE, end='', file=sys.stderr)
        return PREFLIGHT_ERROR
    cs.preflight()
    name = cs.read_codespace_name()
    workspace_dir = cs.codespace_workspace_dir()

    # One string, not a 'bash -lc' triple: ssh flattens forwarded arguments into a
    # single string the remote shell re-parses, which would re-split the '&&'.
    remote_command = ' '.join([f'cd {workspace_dir} &&', *map(bash_quote, arguments)])
    sys.stdout.flush()
    status = subprocess.run(
        ['gh', 'codespace', 'ssh', '-c', name, '--', remote_command], check=False
    ).returncode

    print(f'\nREMOTE_EXIT_CODE={status}')
    if status != 0:
        print_error(f'Remote command exited {status} on codespace {name}.')
        return REMOTE_COMMAND_FAILED
    return 0


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    cs.install({REMOTE_COMMAND_FAILED: 'REMOTE_COMMAND_FAILED'})
    cs.rc.run(main)
