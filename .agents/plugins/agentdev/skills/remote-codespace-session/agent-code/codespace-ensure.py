#!/usr/bin/env python3

"""Find-or-create the Codespace used as this session's remote build/test machine."""

from __future__ import annotations

import subprocess
import sys
import time

import codespace_common as cs
from codespace_common import print_error, Stop

CREATE_FAILED = 4
STATE_WAIT_TIMEOUT = 5
GH_CALL_FAILED = 6
PREFLIGHT_ERROR = 2

DESCRIPTION = "Find-or-create the Codespace used as this session's remote build/test machine."

USAGE = """
Usage:
  codespace-ensure.py [--branch <name>] [--machine <name>] [--idle-timeout <dur>]
                       [--retention-period <dur>] [--poll-interval <seconds>]
                       [--poll-timeout <seconds>] [--dry-run]

Options:
  --branch <name>             Branch to create/find the codespace for. Default: current branch
  --machine <name>            gh codespace create -m value. Default: standardLinux32gb
  --idle-timeout <dur>        gh codespace create --idle-timeout value. Default: 30m
  --retention-period <dur>    gh codespace create --retention-period value. Go-style
                               duration (h/m/s only, no 'd'; max 720h). Default: 24h
  --poll-interval <seconds>   Seconds between state polls while waiting for a new codespace.
                               Integer >= 1. Default: 10
  --poll-timeout <seconds>    Total seconds to wait before giving up. Integer >= 0. Default: 300
  --dry-run                   Print what would happen without creating anything or writing
                               ./.tmp/codespace-name
  -h, --help                  Show this help text.

Output (key=value lines):
  RESULT, ACTION
  ACTION=reuse, and ACTION=create outside --dry-run, also print: CODESPACE, STATE
  ACTION=create under --dry-run instead prints: DISPLAY_NAME, MACHINE,
  IDLE_TIMEOUT, RETENTION_PERIOD, BRANCH

Results (RESULT / exit code):
  SUCCESS                  0  Resolved (reused or created), or dry-run report printed
  CREATE_FAILED            4  'gh codespace create' failed
  STATE_WAIT_TIMEOUT       5  Timed out waiting for the new codespace to reach Available.
                              Its name was still recorded; check 'gh codespace list'
  GH_CALL_FAILED           6  A 'gh codespace list' lookup failed
  CODESPACE_SCOPE_MISSING  3  gh token is missing the 'codespace' OAuth scope
  PREFLIGHT_ERROR          2  Usage error, not a repo, detached HEAD, or gh missing
                              or unauthenticated
  SCRIPT_FAILURE           1  Unhandled error

Examples:
  agent-code/codespace-ensure.py
  agent-code/codespace-ensure.py --dry-run
  agent-code/codespace-ensure.py --branch feature/my-change --machine premiumLinux
"""

VALUE_OPTIONS = (
    '--branch',
    '--machine',
    '--idle-timeout',
    '--retention-period',
    '--poll-interval',
    '--poll-timeout',
)


def parse_arguments(arguments: list[str]) -> dict[str, str]:
    """Return the option values and --dry-run, stopping at a usage error or help."""
    values = {
        '--branch': '',
        '--machine': 'standardLinux32gb',
        '--idle-timeout': '30m',
        '--retention-period': '24h',
        '--poll-interval': '10',
        '--poll-timeout': '300',
        '--dry-run': '',
    }
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument in VALUE_OPTIONS:
            if not remaining:
                print_error(f'Missing value for {argument}')
                raise Stop(PREFLIGHT_ERROR)
            value = remaining.pop(0)
            if argument == '--poll-interval':
                cs.require_int_min(argument, value, 1)
            elif argument == '--poll-timeout':
                cs.require_int_min(argument, value, 0)
            values[argument] = value
        elif argument == '--dry-run':
            values['--dry-run'] = 'yes'
        elif argument in ('-h', '--help'):
            print(cs.help_header(DESCRIPTION) + USAGE, end='')
            raise Stop(0)
        else:
            print_error(f'Unknown argument: {argument}')
            print(cs.help_header(DESCRIPTION) + USAGE, end='', file=sys.stderr)
            raise Stop(PREFLIGHT_ERROR)
    return values


def state_of(owner_repo: str, name: str) -> str:
    """Return the codespace's state, stopping when the lookup fails."""
    state = cs.codespace_state_by_name(owner_repo, name)
    if state is None:
        print_error(f"Could not read the state of codespace {name}. Check 'gh codespace list'.")
        raise Stop(GH_CALL_FAILED)
    return state


def reuse(owner_repo: str, name: str, dry_run: bool) -> int:
    """Report, and outside --dry-run record, the existing codespace."""
    state = state_of(owner_repo, name)
    if state not in ('Available', 'Shutdown'):
        print(
            f'NOTE: Codespace {name} has unexpected state {state}; reusing it anyway. '
            'A later ssh call is the real usability gate.',
            file=sys.stderr,
        )
    if not dry_run:
        cs.write_codespace_name(name)
    print('ACTION=reuse')
    print(f'CODESPACE={name}')
    print(f'STATE={state}')
    return 0


def create(values: dict[str, str], owner_repo: str, branch: str, display_name: str) -> int:
    """Create the codespace and poll until it is Available."""
    cs.repo_root_tmp_dir()
    created = cs.captured(
        'gh', 'codespace', 'create', '-R', owner_repo, '-b', branch,
        '--devcontainer-path', '.devcontainer/devcontainer.json',
        '-m', values['--machine'], '--idle-timeout', values['--idle-timeout'],
        '--retention-period', values['--retention-period'], '--default-permissions',
        '--display-name', display_name,
        stderr=subprocess.PIPE,
    )  # fmt: skip
    new_name = cs.strip_lines(created.stdout.rstrip('\n'))
    if created.returncode != 0 or not new_name:
        print_error(f'gh codespace create failed: {created.stderr.rstrip(chr(10))}')
        return CREATE_FAILED

    poll_interval = int(values['--poll-interval'])
    poll_timeout = int(values['--poll-timeout'])
    elapsed = 0
    while True:
        state = state_of(owner_repo, new_name)
        if state == 'Available':
            break
        if elapsed >= poll_timeout:
            cs.write_codespace_name(new_name)
            print_error(
                f'Timed out after {poll_timeout}s waiting for codespace {new_name} to become '
                f"Available (last state: {state}). Check 'gh codespace list' manually."
            )
            return STATE_WAIT_TIMEOUT
        time.sleep(poll_interval)
        elapsed += poll_interval

    cs.write_codespace_name(new_name)
    print('ACTION=create')
    print(f'CODESPACE={new_name}')
    print('STATE=Available')
    return 0


def run(arguments: list[str]) -> int:
    """Reuse the branch's codespace, or create it."""
    values = parse_arguments(arguments)
    cs.preflight()
    owner_repo = cs.resolve_owner_repo()

    branch = values['--branch']
    if not branch:
        branch = cs.current_branch()
        if not branch:
            print_error('Could not determine the current branch. Pass --branch <name>.')
            return PREFLIGHT_ERROR
        if branch == 'HEAD':
            print_error('Detached HEAD: check out a branch, or pass --branch <name>.')
            return PREFLIGHT_ERROR

    display_name = cs.codespace_display_name(branch)
    existing = cs.codespace_lookup_by_display_name(owner_repo, display_name)
    if existing is None:
        print_error(f"Could not list codespaces for {owner_repo}. Check 'gh codespace list'.")
        return GH_CALL_FAILED
    dry_run = bool(values['--dry-run'])
    if existing:
        return reuse(owner_repo, existing, dry_run)

    if dry_run:
        print('ACTION=create')
        print(f'DISPLAY_NAME={display_name}')
        print(f'MACHINE={values["--machine"]}')
        print(f'IDLE_TIMEOUT={values["--idle-timeout"]}')
        print(f'RETENTION_PERIOD={values["--retention-period"]}')
        print(f'BRANCH={branch}')
        return 0
    return create(values, owner_repo, branch, display_name)


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    cs.install(
        {
            CREATE_FAILED: 'CREATE_FAILED',
            STATE_WAIT_TIMEOUT: 'STATE_WAIT_TIMEOUT',
            GH_CALL_FAILED: 'GH_CALL_FAILED',
        }
    )
    cs.rc.run(main)
