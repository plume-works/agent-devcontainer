#!/usr/bin/env python3

"""
Create a commit, refusing on the repository's default branch.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import git_default_branch  # noqa: E402  (path set above so the plugin's bin/ resolves)
import result_codes as rc  # noqa: E402
from skill_common import print_error, require_git_repo, run_inherited, run_tool, Stop  # noqa: E402

PROTECTED_BRANCH = 3
COMMIT_FAILED = 4
DEFAULT_UNKNOWN = 5
PREFLIGHT_ERROR = 2

USAGE = """\
Create a commit, refusing on the repository's default branch.

Usage:
  git-commit.py [--remote <name>] -- <git commit arguments>

Options:
  --remote <name>  Remote whose default branch is protected. Default: origin
  -h, --help       Show this help text.

Protected: main, master, and the branch refs/remotes/<remote>/HEAD names (or,
when that is unset, the default branch gh reports for the remote's URL). When
the remote exists but neither source names its default branch, the commit is
refused; when the remote is not configured, only main and master are protected.

Output:
  The output of git commit, then key=value lines:
  BRANCH, GIT_EXIT_CODE (only when git commit ran), RESULT
  GIT_EXIT_CODE is git commit's own status; the script's exit code is RESULT's.

Results (RESULT / exit code):
  SUCCESS           0  The commit was created
  PROTECTED_BRANCH  3  The current branch is a default branch; git commit did not run
  COMMIT_FAILED     4  git commit ran and failed (nothing staged, hook failure)
  DEFAULT_UNKNOWN   5  The remote exists but its default branch could not be
                       determined; git commit did not run
  PREFLIGHT_ERROR   2  Bad usage, not a repository, or a detached HEAD
  SCRIPT_FAILURE    1  Unhandled error
  SIGNAL_HUP      129  Interrupted by HUP
  SIGNAL_INT      130  Interrupted by INT
  SIGNAL_TERM     143  Interrupted by TERM

Examples:
  agent-code/git-commit.py -- -m "fix(serial): handle reconnect timeout"
  agent-code/git-commit.py -- -F .tmp/commit-message.txt
"""


def parse_arguments(arguments: list[str]) -> tuple[str, list[str]]:
    """Return the remote and the git commit arguments after --."""
    remote = 'origin'
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument == '--remote':
            if not remaining:
                print_error('Missing value for --remote')
                raise Stop(PREFLIGHT_ERROR)
            remote = remaining.pop(0)
        elif argument in ('-h', '--help'):
            print(USAGE, end='')
            raise Stop(0)
        elif argument == '--':
            break
        else:
            print_error(f'Unknown argument: {argument} (pass git commit arguments after --)')
            print(USAGE, end='', file=sys.stderr)
            raise Stop(PREFLIGHT_ERROR)
    return remote, remaining


def run(arguments: list[str]) -> int:
    """Refuse a commit on a default branch; otherwise run git commit and report it."""
    remote, commit_arguments = parse_arguments(arguments)
    require_git_repo()

    symref = run_tool('git', 'symbolic-ref', '--quiet', '--short', 'HEAD')
    if symref.returncode != 0:
        print_error('HEAD is detached; commit on a feature branch instead.')
        return PREFLIGHT_ERROR
    branch = symref.stdout.strip()
    print(f'BRANCH={branch}')

    protected = git_default_branch.is_default_branch(branch)
    if not protected:
        default_branch = git_default_branch.remote_default_branch(remote)
        if default_branch is not None:
            protected = branch == default_branch
        elif run_tool('git', 'remote', 'get-url', remote).returncode == 0:
            print_error(f"Cannot tell whether '{branch}' is the default branch of '{remote}'.")
            print_error(
                f'Run: git remote set-head {remote} --auto, or authenticate gh (gh auth login).'
            )
            return DEFAULT_UNKNOWN
    if protected:
        print_error(f"Refusing to commit on the default branch '{branch}'.")
        print_error(
            'Create a work branch with /agentdev:git-new-branch; it carries uncommitted changes.'
        )
        return PROTECTED_BRANCH

    status = run_inherited('git', 'commit', *commit_arguments)
    print(f'\nGIT_EXIT_CODE={status}')
    return COMMIT_FAILED if status else 0


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES.update(
        {
            PROTECTED_BRANCH: 'PROTECTED_BRANCH',
            COMMIT_FAILED: 'COMMIT_FAILED',
            DEFAULT_UNKNOWN: 'DEFAULT_UNKNOWN',
        }
    )
    rc.install()
    rc.run(main)
