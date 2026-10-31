#!/usr/bin/env python3

"""
Find the pull request whose head is the current branch.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

from pathlib import Path
import shutil
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
    run_tool,
    Stop,
)

NO_PR_FOUND = 3
MULTIPLE_PRS = 4
PROTECTED_BRANCH = 5
GH_UNAVAILABLE = 6
PREFLIGHT_ERROR = 2

DESCRIPTION = 'Find the pull request whose head is the current branch.'

USAGE = """
Usage:
  find-branch-pr.py [--branch <name>] [--state open|all]

Options:
  --branch <name>    Head branch to look up. Default: current branch
  --state <state>    PR state filter: open (default) or all
  -h, --help         Show this help text.

Output (key=value lines):
  RESULT, HEAD_BRANCH, PR_FOUND
  On a match also: PR_NUMBER, PR_URL, PR_STATE, PR_IS_DRAFT, PR_BASE, PR_HEAD,
  PR_TITLE

HEAD_BRANCH is the pull request head to look up and to create against. It is
the configured upstream branch name when the local branch tracks a differently
named ref (local 'review-31' tracking 'fork/feature' resolves to 'feature'),
and the local branch name otherwise.

Results (RESULT / exit code):
  SUCCESS           0  Exactly one matching pull request was found
  NO_PR_FOUND       3  No matching pull request exists (the branch needs one)
  MULTIPLE_PRS      4  Multiple matching pull requests exist
  PROTECTED_BRANCH  5  Branch is a protected default branch
  GH_UNAVAILABLE    6  gh is missing, unauthenticated, or its API call failed
  PREFLIGHT_ERROR   2  Usage or preflight error (not a repo, detached HEAD)
  SCRIPT_FAILURE    1  Unhandled error

HEAD_BRANCH is printed before the gh checks, so it is available on GH_UNAVAILABLE
for a caller that falls back to a GitHub MCP server for the lookup.
"""

# A Go template keeps this dependent on `gh` alone, with no jq requirement.
# Each match starts with a PR_RECORD marker line so matches can be counted.
PR_TEMPLATE = """{{range .}}PR_RECORD
PR_NUMBER={{.number}}
PR_URL={{.url}}
PR_STATE={{.state}}
PR_IS_DRAFT={{.isDraft}}
PR_BASE={{.baseRefName}}
PR_HEAD={{.headRefName}}
PR_TITLE={{.title}}
{{end}}"""


def usage() -> str:
    """Return the full help text."""
    return help_header(DESCRIPTION, __file__) + USAGE


def parse_arguments(arguments: list[str]) -> tuple[str, str]:
    """Return the branch and state filter, stopping at a usage error or help."""
    branch, state = '', 'open'
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument in ('--branch', '--state'):
            if not remaining:
                print_error(f'Missing value for {argument}')
                raise Stop(PREFLIGHT_ERROR)
            if argument == '--branch':
                branch = remaining.pop(0)
            else:
                state = remaining.pop(0)
        elif argument in ('-h', '--help'):
            print(usage(), end='')
            raise Stop(0)
        else:
            print_error(f'Unknown argument: {argument}')
            print(usage(), end='', file=sys.stderr)
            raise Stop(PREFLIGHT_ERROR)
    if state not in ('open', 'all'):
        print_error(f'Unsupported --state value: {state} (use open or all)')
        raise Stop(PREFLIGHT_ERROR)
    return branch, state


def captured(text: str) -> str:
    """Return command output as a shell `$(...)` capture prints it with one newline."""
    return text.rstrip('\n') + '\n'


def run(arguments: list[str]) -> int:
    """Look up the branch's pull request and report it."""
    branch, state = parse_arguments(arguments)
    require_git_repo()
    branch = branch or current_branch()

    if branch == 'HEAD':
        print_error(
            'Detached HEAD: check out the pull request branch before looking up its pull request.'
        )
        return PREFLIGHT_ERROR
    if git_default_branch.is_default_branch(branch):
        print_error(
            f'Branch {branch} is a protected default branch; '
            'a pull request head must be a feature branch.'
        )
        return PROTECTED_BRANCH

    # The pull request head is the remote branch, which push-branch.py writes to.
    # It only matches the local branch name when the branch has no upstream or the
    # upstream carries the same name.
    head_branch = branch
    upstream = run_tool(
        'git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', f'{branch}@{{u}}'
    )
    upstream_ref = upstream.stdout.strip()
    if upstream.returncode == 0:
        head_branch = upstream_ref.partition('/')[2] if '/' in upstream_ref else upstream_ref
    if head_branch != branch and git_default_branch.is_default_branch(head_branch):
        print_error(
            f'Branch {branch} tracks {upstream_ref}; a pull request head must be a feature branch.'
        )
        return PROTECTED_BRANCH

    print(f'HEAD_BRANCH={head_branch}')

    # GH_UNAVAILABLE, not PREFLIGHT_ERROR: these are the conditions the skill's
    # GitHub MCP fallback exists for, so the caller must be able to tell them apart
    # from a preflight error that no fallback can rescue.
    if shutil.which('gh') is None:
        print_error('GitHub CLI (gh) is not installed.')
        return GH_UNAVAILABLE
    if run_tool('gh', 'auth', 'status').returncode != 0:
        print_error("GitHub CLI is not authenticated. Run 'gh auth login' and retry.")
        return GH_UNAVAILABLE

    listing = subprocess.run(
        [
            'gh', 'pr', 'list',
            '--head', head_branch,
            '--state', state,
            '--json', 'number,url,state,isDraft,baseRefName,headRefName,title',
            '--template', PR_TEMPLATE,
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )  # fmt: skip
    output = listing.stdout
    if listing.returncode != 0:
        # Also GH_UNAVAILABLE: a call that failed on scope, network, or rate limit
        # leaves gh just as unusable as a missing one, and the MCP fallback rescues it.
        print_error(f'gh pr list failed for head branch {head_branch}.')
        sys.stderr.write(captured(output))
        return GH_UNAVAILABLE

    lines = output.rstrip('\n').split('\n')
    count = lines.count('PR_RECORD')
    if count == 0:
        print('PR_FOUND=false')
        print(
            f'No {state} pull request found with head branch {head_branch}; '
            'the branch needs a new pull request.',
            file=sys.stderr,
        )
        return NO_PR_FOUND
    if count > 1:
        print_error(
            f"Found {count} pull requests with head branch '{head_branch}'; "
            'refusing to guess which one to update.'
        )
        sys.stderr.write(captured(output))
        return MULTIPLE_PRS

    print('PR_FOUND=true')
    for line in lines:
        if line and line != 'PR_RECORD':
            print(line)
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
            NO_PR_FOUND: 'NO_PR_FOUND',
            MULTIPLE_PRS: 'MULTIPLE_PRS',
            PROTECTED_BRANCH: 'PROTECTED_BRANCH',
            GH_UNAVAILABLE: 'GH_UNAVAILABLE',
        }
    )
    rc.install()
    rc.run(main)
