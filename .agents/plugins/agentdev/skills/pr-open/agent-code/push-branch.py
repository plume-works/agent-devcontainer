#!/usr/bin/env python3

"""
Push a branch to its pull request head ref without rewriting history.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import git_default_branch  # noqa: E402  (path set above so the plugin's bin/ resolves)
import result_codes as rc  # noqa: E402
from skill_common import (  # noqa: E402
    current_branch,
    help_header,
    print_error,
    require_git_repo,
    run_to_stderr,
    run_tool,
    Stop,
)

NOT_FAST_FORWARD = 3
PUSH_REJECTED = 4
PROTECTED_BRANCH = 5
MAP_STALE = 6
MAP_CHECK_FAILED = 7
PREFLIGHT_ERROR = 2

MAP_CHECK_SCRIPT = (
    Path(__file__).resolve().parents[2] / 'iwe-map' / 'agent-code' / 'stale-map-docs.py'
)

DESCRIPTION = 'Push a branch to its pull request head ref without rewriting history.'

USAGE = """
Usage:
  push-branch.py [--remote <name>] [--branch <name>] [--skip-map-check]

Options:
  --remote <name>    Remote to push to when no upstream is configured. Default: origin
  --branch <name>    Branch to push. Default: current branch
  --skip-map-check   Push without the codebase-map staleness check. Pass it only
                     when the user explicitly asks to push a stale map.
  -h, --help         Show this help text.

Output (key=value lines):
  RESULT, BRANCH, UPSTREAM, ACTION
  When the branch has an upstream also: AHEAD, BEHIND
  Unless blocked first also: MAP_CHECK=<fresh|skipped|stale|failed|overridden>

The iwe-map stale-map-docs.py check runs in a temporary detached worktree at the
branch head, including a head the upstream already has, since it may have been
pushed outside this script. It is skipped when that commit has no
.iwe/config.toml, the check script is absent, or the check finds no map docs.

ACTION says what was done: 'none' when the upstream already matched, 'push'
when an existing upstream was updated, and 'push-with-upstream' when the remote
branch was created and tracking configured.

Results (RESULT / exit code):
  SUCCESS           0  Pushed, or already up to date
  NOT_FAST_FORWARD  3  Branch is behind or diverged from its upstream
  PUSH_REJECTED     4  Push failed
  PROTECTED_BRANCH  5  Branch is a protected default branch
  MAP_STALE         6  The codebase map is stale at the branch head; nothing pushed
  MAP_CHECK_FAILED  7  The map check could not run to a verdict; nothing pushed
  PREFLIGHT_ERROR   2  Usage or preflight error
  SCRIPT_FAILURE    1  Unhandled error
"""


def usage() -> str:
    """Return the full help text."""
    return help_header(DESCRIPTION, __file__) + USAGE


def parse_arguments(arguments: list[str]) -> tuple[str, bool, str, bool]:
    """Return the remote, whether it was explicit, the branch, and --skip-map-check."""
    remote, explicit, branch, skip = 'origin', False, '', False
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument in ('--remote', '--branch'):
            if not remaining:
                print_error(f'Missing value for {argument}')
                raise Stop(PREFLIGHT_ERROR)
            if argument == '--remote':
                remote, explicit = remaining.pop(0), True
            else:
                branch = remaining.pop(0)
        elif argument == '--skip-map-check':
            skip = True
        elif argument in ('-h', '--help'):
            print(usage(), end='')
            raise Stop(0)
        else:
            print_error(f'Unknown argument: {argument}')
            print(usage(), end='', file=sys.stderr)
            raise Stop(PREFLIGHT_ERROR)
    return remote, explicit, branch, skip


def captured(text: str) -> str:
    """Return command output as a shell `$(...)` capture prints it with one newline."""
    return text.rstrip('\n') + '\n'


def merged_output(*arguments: str, cwd: str | None = None) -> tuple[int, str]:
    """Run a command with stderr folded into stdout; return its status and output."""
    sys.stdout.flush()
    completed = subprocess.run(
        list(arguments),
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=cwd,
    )
    return completed.returncode, completed.stdout


def check_map_freshness(commit: str, skip: bool) -> None:
    """
    Print MAP_CHECK for `commit`, stopping the run when the map is stale or unchecked.

    Map freshness gate: see spec/iwe-workflow-skills.
    """
    if skip:
        print('MAP_CHECK=overridden')
        return
    if (
        not MAP_CHECK_SCRIPT.is_file()
        or run_tool('git', 'cat-file', '-e', f'{commit}:.iwe/config.toml').returncode != 0
    ):
        print('MAP_CHECK=skipped')
        return

    repo_root = Path(run_tool('git', 'rev-parse', '--show-toplevel').stdout.strip())
    (repo_root / '.tmp').mkdir(parents=True, exist_ok=True)
    check_dir = tempfile.mkdtemp(prefix='push-map-check.', dir=repo_root / '.tmp')
    if run_to_stderr('git', 'worktree', 'add', '--quiet', '--detach', check_dir, commit):
        try:
            os.rmdir(check_dir)
        except OSError:
            print_error(f'Could not remove {check_dir}.')
        print_error(f'Could not create a worktree at {commit} for the map check.')
        print('MAP_CHECK=failed')
        raise Stop(MAP_CHECK_FAILED)
    status, output = merged_output(str(MAP_CHECK_SCRIPT), cwd=check_dir)
    if run_to_stderr('git', 'worktree', 'remove', '--force', check_dir):
        print_error(f'Could not remove worktree {check_dir}.')

    if status == 0:
        print('MAP_CHECK=fresh')
    elif status == 4:
        print('MAP_CHECK=skipped')
    elif status == 3:
        sys.stderr.write(captured(output))
        print_error(
            f'The codebase map is stale at {commit}. '
            'Refresh it with /agentdev:iwe-map, commit, and rerun.'
        )
        print('MAP_CHECK=stale')
        raise Stop(MAP_STALE)
    else:
        sys.stderr.write(captured(output))
        print_error(f'The codebase map check exited {status} without a verdict.')
        print('MAP_CHECK=failed')
        raise Stop(MAP_CHECK_FAILED)


def push(*arguments: str) -> int:
    """Push, printing git's merged output on stdout on success and stderr on failure."""
    status, output = merged_output('git', 'push', *arguments)
    if status == 0:
        print(captured(output), end='')
        return 0
    print_error('Git push failed. Check Git credentials and remote permissions.')
    sys.stderr.write(captured(output))
    return PUSH_REJECTED


def count(revisions: str) -> int:
    """Return the number of commits in a revision range."""
    return int(run_tool('git', 'rev-list', '--count', revisions).stdout.strip())


def push_to_upstream(
    branch: str, upstream_ref: str, remote: str, explicit: bool, skip: bool
) -> int:
    """Fast-forward the existing upstream, refusing a behind or diverged branch."""
    upstream_remote = upstream_ref.split('/', 1)[0]
    upstream_branch = upstream_ref.partition('/')[2] if '/' in upstream_ref else upstream_ref

    if explicit and upstream_remote != remote:
        print_error(
            f"Configured upstream remote '{upstream_remote}' does not match --remote '{remote}'."
        )
        print(
            f'Please either rerun the command with --remote {upstream_remote} '
            'or update the branch upstream before continuing.',
            file=sys.stderr,
        )
        return PREFLIGHT_ERROR

    run_tool('git', 'fetch', '--quiet', upstream_remote, upstream_branch)
    ahead = count(f'{upstream_ref}..{branch}')
    behind = count(f'{branch}..{upstream_ref}')
    print(f'UPSTREAM={upstream_ref}')
    print(f'AHEAD={ahead}')
    print(f'BEHIND={behind}')

    if behind > 0 and ahead > 0:
        print_error(
            'Local branch has diverged from its upstream; '
            'the pull request head would not fast-forward.'
        )
        print('Merge the upstream branch into the local branch:', file=sys.stderr)
        print(f'  git pull {upstream_remote} {upstream_branch}', file=sys.stderr)
        print(
            'Resolve any conflicts, commit the merge, and rerun. Never force-push here.',
            file=sys.stderr,
        )
        return NOT_FAST_FORWARD
    if behind > 0:
        print_error(
            'Local branch is behind its upstream; the pull request head would not fast-forward.'
        )
        print('Reconcile the branch first, then rerun:', file=sys.stderr)
        print(f'  git pull --ff-only {upstream_remote} {upstream_branch}', file=sys.stderr)
        print(
            'If the branches diverged, merge the upstream branch instead. Never force-push here.',
            file=sys.stderr,
        )
        return NOT_FAST_FORWARD

    check_map_freshness(run_tool('git', 'rev-parse', f'refs/heads/{branch}').stdout.strip(), skip)
    if ahead == 0:
        print('ACTION=none')
        return 0
    print('ACTION=push')
    return push(upstream_remote, f'refs/heads/{branch}:refs/heads/{upstream_branch}')


def run(arguments: list[str]) -> int:
    """Push the branch and report what was done."""
    remote, explicit, branch, skip = parse_arguments(arguments)
    require_git_repo()
    branch = branch or current_branch()

    if branch == 'HEAD':
        print_error('Detached HEAD: check out the pull request branch before pushing.')
        return PREFLIGHT_ERROR
    if git_default_branch.is_default_branch(branch):
        print_error(
            f'Refusing to push from {branch}; a pull request head must be a feature branch.'
        )
        return PROTECTED_BRANCH
    if run_tool('git', 'show-ref', '--verify', '--quiet', f'refs/heads/{branch}').returncode:
        print_error(f'Local branch not found: {branch}')
        return PREFLIGHT_ERROR

    print(f'BRANCH={branch}')

    upstream = run_tool(
        'git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', f'{branch}@{{u}}'
    )
    if upstream.returncode == 0:
        return push_to_upstream(branch, upstream.stdout.strip(), remote, explicit, skip)

    if run_tool('git', 'remote', 'get-url', remote).returncode != 0:
        print_error(f'Remote not found: {remote}')
        return PREFLIGHT_ERROR

    print(f'UPSTREAM={remote}/{branch}')
    check_map_freshness(run_tool('git', 'rev-parse', f'refs/heads/{branch}').stdout.strip(), skip)
    print('ACTION=push-with-upstream')

    if branch == current_branch():
        return push('-u', remote, branch)
    # Do not change the checked-out branch's upstream when --branch selects a
    # different local branch. The explicit refspec still creates that remote ref.
    return push(remote, f'refs/heads/{branch}:refs/heads/{branch}')


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES.update(
        {
            NOT_FAST_FORWARD: 'NOT_FAST_FORWARD',
            PUSH_REJECTED: 'PUSH_REJECTED',
            PROTECTED_BRANCH: 'PROTECTED_BRANCH',
            MAP_STALE: 'MAP_STALE',
            MAP_CHECK_FAILED: 'MAP_CHECK_FAILED',
        }
    )
    rc.install()
    rc.run(main)
