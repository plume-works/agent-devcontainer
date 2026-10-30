#!/usr/bin/env python3

"""Stop (default) or delete the codespace recorded by codespace-ensure.py."""

from __future__ import annotations

import subprocess
import sys
import time

import codespace_common as cs
from codespace_common import print_error, Stop

TEARDOWN_FAILED = 4
STATE_WAIT_TIMEOUT = 5
GH_CALL_FAILED = 6
PREFLIGHT_ERROR = 2

DESCRIPTION = 'Stop (default) or delete the codespace recorded by codespace-ensure.py.'

USAGE = """
Usage:
  codespace-teardown.py [--delete] [--poll-interval <seconds>] [--poll-timeout <seconds>]

Options:
  --delete                    Fully delete the codespace instead of stopping it.
                               Skips gh's own interactive confirmation via --force.
  --poll-interval <seconds>   Seconds between state polls while waiting for the
                               terminal state. Integer >= 1. Default: 10
  --poll-timeout <seconds>    Total seconds to wait for the terminal state before
                               giving up. Integer >= 0. Default: 300
  -h, --help                  Show this help text.

Behavior:
  Default: 'gh codespace stop' -- stops compute billing, keeps storage so a
  later codespace-ensure.py can reuse it. Does not touch ./.tmp/codespace-name
  or ./.tmp/codespace-ssh-config. Waits (polling like codespace-ensure.py) until
  the codespace reports 'Shutdown', since 'gh codespace stop' returns while the
  codespace is still 'ShuttingDown'.
  --delete: 'gh codespace delete --force' -- fully deletes the codespace, waits
  until it disappears from 'gh codespace list', then removes
  ./.tmp/codespace-name and ./.tmp/codespace-ssh-config since they now refer to
  a codespace that no longer exists.

Output (key=value lines):
  RESULT, ACTION, CODESPACE
  ACTION=stop also prints: STATE

Results (RESULT / exit code):
  SUCCESS                  0  Stopped (reached Shutdown) or deleted (gone from the list)
  TEARDOWN_FAILED          4  The 'gh codespace stop' or 'gh codespace delete' call failed
  STATE_WAIT_TIMEOUT       5  Timed out waiting for the terminal state (Shutdown for stop,
                              gone for delete). The stop/delete itself was accepted; only
                              the wait timed out. Re-check with 'gh codespace list'
  GH_CALL_FAILED           6  A 'gh codespace list' lookup failed
  CODESPACE_SCOPE_MISSING  3  gh token is missing the 'codespace' OAuth scope
  PREFLIGHT_ERROR          2  Usage error, not a repo, gh missing or unauthenticated,
                              or no codespace name recorded
  SCRIPT_FAILURE           1  Unhandled error

Examples:
  agent-code/codespace-teardown.py
  agent-code/codespace-teardown.py --delete
  agent-code/codespace-teardown.py --poll-timeout 600
"""


def parse_arguments(arguments: list[str]) -> tuple[bool, int, int]:
    """Return --delete, the poll interval, and the poll timeout."""
    delete, poll_interval, poll_timeout = False, 10, 300
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument == '--delete':
            delete = True
        elif argument in ('--poll-interval', '--poll-timeout'):
            if not remaining:
                print_error(f'Missing value for {argument}')
                raise Stop(PREFLIGHT_ERROR)
            value = remaining.pop(0)
            if argument == '--poll-interval':
                poll_interval = cs.require_int_min(argument, value, 1)
            else:
                poll_timeout = cs.require_int_min(argument, value, 0)
        elif argument in ('-h', '--help'):
            print(cs.help_header(DESCRIPTION) + USAGE, end='')
            raise Stop(0)
        else:
            print_error(f'Unknown argument: {argument}')
            print(cs.help_header(DESCRIPTION) + USAGE, end='', file=sys.stderr)
            raise Stop(PREFLIGHT_ERROR)
    return delete, poll_interval, poll_timeout


def wait_for(
    owner_repo: str, name: str, done: str, verb: str, target: str, interval: int, timeout: int
) -> None:
    """Poll the codespace's state until it is `done`, stopping on a failure or the timeout."""
    elapsed = 0
    while True:
        state = cs.codespace_state_by_name(owner_repo, name)
        if state is None:
            print_error(
                f'Could not read the state of codespace {name}. '
                f"The {verb} was accepted; check 'gh codespace list'."
            )
            raise Stop(GH_CALL_FAILED)
        if state == done:
            return
        if elapsed >= timeout:
            print_error(
                f'Timed out after {timeout}s waiting for codespace {name} to {target} '
                f"(last state: {state}). The {verb} was accepted; check 'gh codespace list'."
            )
            raise Stop(STATE_WAIT_TIMEOUT)
        time.sleep(interval)
        elapsed += interval


def run(arguments: list[str]) -> int:
    """Stop or delete the recorded codespace and wait for its terminal state."""
    delete, poll_interval, poll_timeout = parse_arguments(arguments)
    cs.preflight()
    owner_repo = cs.resolve_owner_repo()
    name = cs.read_codespace_name()

    command = ['gh', 'codespace', 'delete', '-c', name, '--force'] if delete else [
        'gh', 'codespace', 'stop', '-c', name
    ]  # fmt: skip
    completed = cs.captured(*command, stderr=subprocess.STDOUT)
    if completed.returncode != 0:
        print_error(f'gh codespace {command[2]} failed: {completed.stdout.rstrip(chr(10))}')
        return TEARDOWN_FAILED

    if delete:
        wait_for(owner_repo, name, '', 'delete', 'be deleted', poll_interval, poll_timeout)
        for path in (cs.codespace_name_file(), cs.ssh_config_file()):
            path.unlink(missing_ok=True)
        print('ACTION=delete')
        print(f'CODESPACE={name}')
        return 0

    # 'gh codespace stop' returns while the codespace is still 'ShuttingDown'.
    wait_for(owner_repo, name, 'Shutdown', 'stop', 'reach Shutdown', poll_interval, poll_timeout)
    print('ACTION=stop')
    print(f'CODESPACE={name}')
    print('STATE=Shutdown')
    return 0


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    cs.install(
        {
            TEARDOWN_FAILED: 'TEARDOWN_FAILED',
            STATE_WAIT_TIMEOUT: 'STATE_WAIT_TIMEOUT',
            GH_CALL_FAILED: 'GH_CALL_FAILED',
        }
    )
    cs.rc.run(main)
