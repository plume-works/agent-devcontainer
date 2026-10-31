#!/usr/bin/env python3

"""
Bring in the branch's upstream, then merge the remote base into the current branch.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import git_default_branch  # noqa: E402  (path set above so the plugin's bin/ resolves)
import result_codes as rc  # noqa: E402
from skill_common import (  # noqa: E402
    current_branch,
    help_header,
    print_error,
    require_git_repo,
    run_inherited,
    run_to_stderr,
    run_tool,
    Stop,
)

ALREADY_UP_TO_DATE = 3
MERGE_CONFLICTS = 4
PROTECTED_BRANCH = 5
FETCH_FAILED = 6
PREFLIGHT_ERROR = 2

MERGE_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / 'git-merge-resolve'
    / 'agent-code'
    / 'git-merge-resolve.py'
)

DESCRIPTION = "Bring in the branch's upstream, then merge origin/main into the current branch."

USAGE = """
Usage:
  update-branch.py [--remote <name>] [--base <branch>]

Options:
  --remote <name>    Remote to fetch from. Default: origin
  --base <branch>    Base branch to merge. Default: main
  -h, --help         Show this help text.

Output (key=value lines):
  RESULT, BRANCH, REMOTE, BASE, UPSTREAM, UPSTREAM_ACTION
  Each delegated merge also prints DESTINATION and SOURCE.

UPSTREAM_ACTION says how the branch's upstream was brought in before the base:
'none', 'fast-forward', 'merge', 'untracked' (no upstream), 'base' (the
upstream is the base ref), or 'gone' (deleted on its remote; a warning).

A run stops at the first conflicted merge, and SOURCE names it. Rerun after
the resolution is committed; the rerun continues with the next merge.

Results (RESULT / exit code):
  SUCCESS            0  A merge commit was created
  ALREADY_UP_TO_DATE 3  Branch already contains the base ref; no merge commit
  MERGE_CONFLICTS    4  Conflicts detected — use the git-merge-resolve workflow
  PROTECTED_BRANCH   5  Current branch is the default branch
  FETCH_FAILED       6  The configured or upstream remote could not be fetched
  PREFLIGHT_ERROR    2  Usage or preflight error (not a repo, dirty tree)
  SCRIPT_FAILURE     1  Unhandled error

Examples:
  agent-code/update-branch.py
  agent-code/update-branch.py --remote upstream --base main
"""


def usage() -> str:
    """Return the full help text."""
    return help_header(DESCRIPTION, __file__) + USAGE


def parse_arguments(arguments: list[str]) -> tuple[str, str]:
    """Return the remote and base branch, stopping at a usage error or help."""
    remote, base = 'origin', 'main'
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument in ('--remote', '--base'):
            if not remaining:
                print_error(f'Missing value for {argument}')
                raise Stop(PREFLIGHT_ERROR)
            if argument == '--remote':
                remote = remaining.pop(0)
            else:
                base = remaining.pop(0)
        elif argument in ('-h', '--help'):
            print(usage(), end='')
            raise Stop(0)
        else:
            print_error(f'Unknown argument: {argument}')
            print(usage(), end='', file=sys.stderr)
            raise Stop(PREFLIGHT_ERROR)
    return remote, base


def git_ok(*arguments: str) -> bool:
    """Return whether a quiet git command succeeds."""
    return run_tool('git', *arguments).returncode == 0


def merge_ref(source: str, branch: str) -> None:
    """
    Merge `source` through git-merge-resolve, forwarding its stdout but its RESULT line.

    Stops the run unless the merge succeeded.
    """
    sys.stdout.flush()
    helper = subprocess.run(
        [str(MERGE_SCRIPT), '--message', f'Merge {source} into {branch}', source],
        check=False,
        stdout=subprocess.PIPE,
        text=True,
    )
    for line in helper.stdout.rstrip('\n').split('\n'):
        if not line.startswith('RESULT='):
            print(line)
    if helper.returncode == 0:
        return
    raise Stop(helper.returncode if helper.returncode in (MERGE_CONFLICTS, PREFLIGHT_ERROR) else 1)


def classify_upstream(
    upstream_ref: str, upstream_remote: str, upstream_merge: str, base_ref: str, remote: str
) -> str:
    """Return how the upstream relates to HEAD, fetching a second upstream remote first."""
    if not upstream_ref:
        return 'untracked'
    if upstream_ref == base_ref:
        return 'base'
    if upstream_remote != '.':
        if upstream_remote != remote:
            print(f'Fetching {upstream_remote}...', file=sys.stderr)
            if run_to_stderr('git', 'fetch', upstream_remote):
                print_error(f"Failed to fetch upstream remote '{upstream_remote}'.")
                raise Stop(FETCH_FAILED)
        sys.stdout.flush()
        ls_remote = subprocess.run(
            [
                'git', 'ls-remote', '--exit-code', '--heads',
                upstream_remote, upstream_merge.removeprefix('refs/heads/'),
            ],
            check=False,
            stdout=subprocess.DEVNULL,
        ).returncode  # fmt: skip
        if ls_remote == 2:
            return 'gone'
        if ls_remote != 0:
            print_error(f"Failed to query upstream remote '{upstream_remote}'.")
            raise Stop(FETCH_FAILED)
    if run_to_stderr('git', 'merge-base', '--is-ancestor', upstream_ref, 'HEAD') == 0:
        return 'none'
    if run_to_stderr('git', 'merge-base', '--is-ancestor', 'HEAD', upstream_ref) == 0:
        return 'fast-forward'
    return 'merge'


def run(arguments: list[str]) -> int:
    """Bring in the upstream, then merge the base, and report the result."""
    remote, base = parse_arguments(arguments)
    require_git_repo()
    branch = current_branch()

    if git_default_branch.is_default_branch(branch):
        print_error(
            f"Current branch is '{branch}'. Refusing to merge '{base}' into the default branch."
        )
        return PROTECTED_BRANCH

    if run_tool('git', 'status', '--porcelain').stdout.strip():
        print_error('Working tree is dirty. Commit or stash changes before updating the branch.')
        run_to_stderr('git', 'status', '--short')
        return PREFLIGHT_ERROR

    print(f'BRANCH={branch}')
    print(f'REMOTE={remote}')
    print(f'BASE={remote}/{base}')

    print(f'Fetching {remote}...', file=sys.stderr)
    if run_inherited('git', 'fetch', remote):
        print_error(f"Failed to fetch remote '{remote}'.")
        return FETCH_FAILED

    base_ref = f'{remote}/{base}'
    if not git_ok('rev-parse', '--verify', '--quiet', f'{base_ref}^{{commit}}'):
        print_error(f"Base branch '{base_ref}' was not found after fetching '{remote}'.")
        return PREFLIGHT_ERROR

    if not os.access(MERGE_SCRIPT, os.X_OK):
        print_error(f'Merge helper is missing or not executable: {MERGE_SCRIPT}')
        return 1

    upstream_ref = run_tool(
        'git', 'for-each-ref', '--format=%(upstream:short)', f'refs/heads/{branch}'
    ).stdout.strip()
    upstream_remote = run_tool('git', 'config', '--get', f'branch.{branch}.remote').stdout.strip()
    upstream_merge = run_tool('git', 'config', '--get', f'branch.{branch}.merge').stdout.strip()

    action = classify_upstream(upstream_ref, upstream_remote, upstream_merge, base_ref, remote)
    print(f'UPSTREAM={upstream_ref}')
    print(f'UPSTREAM_ACTION={action}')

    merged = False
    if action == 'gone':
        print(
            f"WARNING: Upstream '{upstream_ref}' no longer exists on '{upstream_remote}'; "
            'continuing without it.',
            file=sys.stderr,
        )
    elif action == 'fast-forward':
        status = run_to_stderr('git', 'merge', '--ff-only', '--quiet', upstream_ref)
        if status:
            return status
    elif action == 'merge':
        merge_ref(upstream_ref, branch)
        merged = True

    if git_ok('merge-base', '--is-ancestor', base_ref, 'HEAD'):
        print(f'Already contains {base_ref}.', file=sys.stderr)
        return 0 if merged else ALREADY_UP_TO_DATE

    merge_ref(base_ref, branch)
    return 0


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES.update(
        {
            ALREADY_UP_TO_DATE: 'ALREADY_UP_TO_DATE',
            MERGE_CONFLICTS: 'MERGE_CONFLICTS',
            PROTECTED_BRANCH: 'PROTECTED_BRANCH',
            FETCH_FAILED: 'FETCH_FAILED',
        }
    )
    rc.install()
    rc.run(main)
