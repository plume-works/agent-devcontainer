#!/usr/bin/env python3

"""
Review working tree and branch changes for the pr-gen-description skill.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import result_codes as rc  # noqa: E402  (path set above so the plugin's bin/ resolves)
from skill_common import (  # noqa: E402
    current_branch,
    help_header,
    print_error,
    require_git_repo,
    run_inherited,
    run_tool,
    Stop,
)

NO_CHANGES = 3
PREFLIGHT_ERROR = 2

DESCRIPTION = 'Review working tree and branch changes for the pr-gen-description skill.'

USAGE = """
Usage:
  review-git-changes.py [--base-ref <ref>] [--range <range>] [--stat-only]

Options:
  --base-ref <ref>   Base ref used to find the merge base for the default
                     comparison range. Default: origin/main
  --range <range>    Explicit git revision range, for example main..HEAD.
  --stat-only        Skip the full patch and print summary sections only.
  -h, --help         Show this help text.

Output:
  RESULT, as the last line.
  Before it, the report sections the skill reads: '== Branch ==',
  '== Status ==', '== Diff Stat (<range>) ==', '== Commit Log (<range>) ==',
  plus '== Working Tree Diff ==' and '== Commit Range Diff (<range>) ==' unless
  --stat-only was passed.

Results (RESULT / exit code):
  SUCCESS          0  The change report was printed
  NO_CHANGES       3  Nothing to describe: no working tree changes and no
                      commits in the range. The report is still printed
  PREFLIGHT_ERROR  2  Usage or preflight error (not a repo, no commits,
                      unknown base ref or range, unrelated histories)
  SCRIPT_FAILURE   1  Unhandled error

Examples:
  agent-code/review-git-changes.py
  agent-code/review-git-changes.py --base-ref upstream/main
  agent-code/review-git-changes.py --range origin/main..HEAD --stat-only
"""


def usage() -> str:
    """Return the full help text."""
    return help_header(DESCRIPTION, __file__) + USAGE


def parse_arguments(arguments: list[str]) -> tuple[str, str, bool]:
    """Return the base ref, the explicit range, and whether to include patches."""
    base_ref, commit_range, include_patch = 'origin/main', '', True
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument in ('--base-ref', '--range'):
            if not remaining:
                print_error(f'Missing value for {argument}')
                raise Stop(PREFLIGHT_ERROR)
            if argument == '--base-ref':
                base_ref = remaining.pop(0)
            else:
                commit_range = remaining.pop(0)
        elif argument == '--stat-only':
            include_patch = False
        elif argument in ('-h', '--help'):
            print(usage(), end='')
            raise Stop(0)
        else:
            print_error(f'Unknown argument: {argument}')
            print(usage(), end='', file=sys.stderr)
            raise Stop(PREFLIGHT_ERROR)
    return base_ref, commit_range, include_patch


def resolve_range(base_ref: str, commit_range: str) -> str:
    """Return the explicit range once it resolves, or merge-base..HEAD against `base_ref`."""
    if commit_range:
        # Resolved before any git command consumes it, so an unknown range is a
        # preflight error rather than git's exit 128.
        if run_tool('git', 'rev-list', '--max-count=1', commit_range).returncode != 0:
            print_error(f'Commit range does not resolve: {commit_range}')
            raise Stop(PREFLIGHT_ERROR)
        return commit_range
    if run_tool('git', 'rev-parse', '--verify', '--quiet', base_ref).returncode != 0:
        print_error(f'Base ref not found: {base_ref}')
        raise Stop(PREFLIGHT_ERROR)
    merge_base = run_tool('git', 'merge-base', base_ref, 'HEAD')
    if merge_base.returncode != 0:
        print_error(f'Could not determine merge base between {base_ref} and HEAD.')
        print_error('Ensure both refs exist and have related commit histories.')
        raise Stop(PREFLIGHT_ERROR)
    return f'{merge_base.stdout.strip()}..HEAD'


def section(*command: str) -> None:
    """Print a git command's output, stopping the run with its status when it fails."""
    status = run_inherited('git', *command)
    if status:
        raise Stop(status)


def run(arguments: list[str]) -> int:
    """Print the change report sections and say whether there is anything to describe."""
    base_ref, commit_range, include_patch = parse_arguments(arguments)
    require_git_repo()
    if run_tool('git', 'rev-parse', '--verify', '--quiet', 'HEAD').returncode != 0:
        print_error('Repository does not contain any commits yet.')
        return PREFLIGHT_ERROR
    commit_range = resolve_range(base_ref, commit_range)

    print('== Branch ==')
    print(f'{current_branch()}\n')

    print('== Status ==')
    section('status', '--short', '--branch')
    print()

    print(f'== Diff Stat ({commit_range}) ==')
    section('--no-pager', 'diff', '--stat', commit_range)
    print()

    if include_patch:
        print('== Working Tree Diff ==')
        section('--no-pager', 'diff')
        print()

        print(f'== Commit Range Diff ({commit_range}) ==')
        section('--no-pager', 'diff', commit_range)
        print()

    print(f'== Commit Log ({commit_range}) ==')
    section('--no-pager', 'log', '--oneline', commit_range)

    if not run_tool('git', 'status', '--porcelain').stdout.strip() and not (
        run_tool('git', 'rev-list', '--max-count=1', commit_range).stdout.strip()
    ):
        print(
            f'NOTE: No working tree changes and no commits detected in {commit_range}.',
            file=sys.stderr,
        )
        return NO_CHANGES
    return 0


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES[NO_CHANGES] = 'NO_CHANGES'
    rc.install()
    rc.run(main)
