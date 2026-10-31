#!/usr/bin/env python3

"""
Merge a local Git ref into the current branch with a non-fast-forward merge.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import result_codes as rc  # noqa: E402  (path set above so the plugin's bin/ resolves)
from skill_common import (  # noqa: E402
    print_error,
    require_git_repo,
    run_inherited,
    run_to_stderr,
    run_tool,
    Stop,
)

# These numbers and names are shared with update-branch.py, which runs this
# script and passes its verdict straight through. Keep the two tables aligned.
ALREADY_UP_TO_DATE = 3
MERGE_CONFLICTS = 4
PREFLIGHT_ERROR = 2

USAGE = """\
Merge a local Git ref into the current branch with a non-fast-forward merge.

Usage:
  git-merge-resolve.py [--message <text>] <source-ref>

Options:
  --message <text>  Merge commit message. Defaults to a generated message.
  -h, --help        Show this help text.

Output (key=value lines):
  RESULT
  Once preflight passes also: DESTINATION, SOURCE

Results (RESULT / exit code):
  SUCCESS            0  Merge succeeded
  ALREADY_UP_TO_DATE 3  Source ref is already merged into HEAD
  MERGE_CONFLICTS    4  Conflicts detected; resolve and commit them
  PREFLIGHT_ERROR    2  Usage, repository, ref, or working-tree preflight
                        failed, or the merge failed with no unresolved paths
  SCRIPT_FAILURE     1  Unhandled error

Examples:
  agent-code/git-merge-resolve.py topic
  agent-code/git-merge-resolve.py \\
    --message "Merge origin/main into feature" origin/main
"""


def parse_arguments(arguments: list[str]) -> tuple[str, str]:
    """Return the source ref and merge message, stopping at a usage error or help."""
    source, message = '', ''
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument == '--message':
            if not remaining:
                print_error('Missing value for --message')
                raise Stop(PREFLIGHT_ERROR)
            message = remaining.pop(0)
        elif argument in ('-h', '--help'):
            print(USAGE, end='')
            raise Stop(0)
        elif argument.startswith('--'):
            print_error(f'Unknown option: {argument}')
            print(USAGE, end='', file=sys.stderr)
            raise Stop(PREFLIGHT_ERROR)
        elif source:
            print_error('Only one source ref may be supplied.')
            print(USAGE, end='', file=sys.stderr)
            raise Stop(PREFLIGHT_ERROR)
        else:
            source = argument
    if not source:
        print_error('A source ref is required.')
        print(USAGE, end='', file=sys.stderr)
        raise Stop(PREFLIGHT_ERROR)
    return source, message


def git_out(*arguments: str) -> str:
    """Return a git command's stripped stdout, whatever its status."""
    return run_tool('git', *arguments).stdout.strip()


def refuse(message: str, show_status: bool = False) -> Stop:
    """Report a preflight failure, optionally with the short status, as a Stop."""
    print_error(message)
    if show_status:
        run_to_stderr('git', 'status', '--short')
    return Stop(PREFLIGHT_ERROR)


def run(arguments: list[str]) -> int:
    """Check the preconditions, merge, and report the result."""
    source, message = parse_arguments(arguments)
    require_git_repo()

    if git_out('rev-parse', '--abbrev-ref', 'HEAD') == 'HEAD':
        raise refuse('Detached HEAD cannot receive this merge. Check out a branch first.')
    if os.path.isfile(git_out('rev-parse', '--git-path', 'MERGE_HEAD')):
        raise refuse('A merge is already in progress. Resolve or complete it first.', True)
    if git_out('status', '--porcelain'):
        raise refuse('Working tree is dirty. Commit or stash changes before merging.', True)
    verified = run_tool('git', 'rev-parse', '--verify', '--quiet', f'{source}^{{commit}}')
    if verified.returncode != 0:
        raise refuse(f'Source ref does not resolve to a commit: {source}')

    destination = git_out('rev-parse', '--abbrev-ref', 'HEAD')
    source_sha = git_out('rev-parse', f'{source}^{{commit}}')
    print(f'DESTINATION={destination}')
    print(f'SOURCE={source}')

    if run_tool('git', 'merge-base', '--is-ancestor', source_sha, 'HEAD').returncode == 0:
        print(f'{source} is already merged into {destination}.', file=sys.stderr)
        return ALREADY_UP_TO_DATE

    message = message or f'Merge {source} into {destination}'
    print(f'Merging {source} into {destination}...', file=sys.stderr)
    if run_inherited('git', 'merge', '--no-ff', source, '--message', message) == 0:
        return run_inherited('git', 'log', '--oneline', '--decorate', '-n', '5')

    conflicted = git_out('diff', '--name-only', '--diff-filter=U')
    if not conflicted:
        raise refuse('Merge failed without unresolved paths. Inspect Git output and status.', True)

    print_error('Merge conflicts detected. Resolve the conflicts listed below.')
    print(f'\nConflicted files:\n{conflicted}', file=sys.stderr)
    return MERGE_CONFLICTS


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES.update(
        {ALREADY_UP_TO_DATE: 'ALREADY_UP_TO_DATE', MERGE_CONFLICTS: 'MERGE_CONFLICTS'}
    )
    rc.install()
    rc.run(main)
