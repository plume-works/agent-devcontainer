#!/usr/bin/env python3

"""
Shared GitHub issue helpers for agentdev skill scripts.

Every function returns a status instead of exiting, so the caller decides which
declared result a failure maps to. Runnable as well:

  github_issue.py parse <ref>                     print ISSUE_REPO and ISSUE_NUMBER
  github_issue.py close <repo> <number> <comment> close with a comment

Standard library only.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from typing import NamedTuple

from skill_common import help_header, print_error, require_git_repo, Stop

USAGE = """\
Usage:
  github_issue.py parse <ref>
  github_issue.py close <owner/repo> <number> <comment>
"""

# The codes close_issue_with_comment returns, as the closing scripts declare them.
CLOSED = 0
GH_FAILED = 3
NOT_FOUND = 4
ALREADY_CLOSED = 5

_URL = re.compile(r'https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/([0-9]+)/?(#.*)?')
_QUALIFIED = re.compile(r'([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)#([0-9]+)')
_BARE = re.compile(r'#?([0-9]+)')
_VIEW_TEMPLATE = 'ISSUE_URL={{.url}}\nISSUE_STATE={{.state}}'
_NOT_FOUND = re.compile(r'could not resolve to an issue|not found|no issue', re.IGNORECASE)


class IssueRef(NamedTuple):
    """An issue reference; `repo` is empty for the bare forms."""

    repo: str
    number: str


def parse_issue_ref(ref: str) -> IssueRef | None:
    """Parse a GitHub issue URL, OWNER/REPO#N, #N, or N; None when it is none of them."""
    for pattern in (_URL, _QUALIFIED):
        if match := pattern.fullmatch(ref):
            return IssueRef(match.group(1), match.group(2))
    if match := _BARE.fullmatch(ref):
        return IssueRef('', match.group(1))
    return None


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(arguments), check=False, capture_output=True, text=True)


def require_gh() -> bool:
    """Return whether gh is installed and authenticated; diagnostics go to stderr."""
    if shutil.which('gh') is None:
        print('ERROR: GitHub CLI (gh) is not installed.', file=sys.stderr)
        return False
    if _run('gh', 'auth', 'status').returncode != 0:
        print(
            "ERROR: GitHub CLI is not authenticated. Run 'gh auth login' and retry.",
            file=sys.stderr,
        )
        return False
    return True


def resolve_current_repo() -> str | None:
    """Return OWNER/REPO for the repository in the current directory, or None when gh fails."""
    sys.stdout.flush()
    completed = subprocess.run(
        ['gh', 'repo', 'view', '--json', 'nameWithOwner', '--jq', '.nameWithOwner'],
        check=False,
        stdout=subprocess.PIPE,
        text=True,
    )
    return completed.stdout.rstrip('\n') if completed.returncode == 0 else None


def gh_output_says_not_found(output: str) -> bool:
    """Return whether gh's output says the issue does not exist rather than gh failing."""
    return _NOT_FOUND.search(output) is not None


def close_issue_with_comment(repo: str, number: str, comment: str) -> int:
    """
    Close `repo`#`number` with `comment` unless it is already closed.

    Prints ISSUE_REPO, ISSUE_NUMBER, ISSUE_URL, and ISSUE_STATE lines, and
    returns CLOSED, GH_FAILED, NOT_FOUND, or ALREADY_CLOSED.
    """
    view = _run(
        'gh', 'issue', 'view', number, '--repo', repo,
        '--json', 'url,state', '--template', _VIEW_TEMPLATE,
    )  # fmt: skip
    output = view.stdout + view.stderr
    if view.returncode != 0:
        sys.stderr.write(output if output.endswith('\n') or not output else f'{output}\n')
        if gh_output_says_not_found(output):
            print(f'ERROR: Issue {repo}#{number} does not exist.', file=sys.stderr)
            return NOT_FOUND
        print(f'ERROR: gh issue view failed for {repo}#{number}.', file=sys.stderr)
        return GH_FAILED

    fields = dict(line.split('=', 1) for line in output.splitlines() if line.startswith('ISSUE_'))
    print(f'ISSUE_REPO={repo}')
    print(f'ISSUE_NUMBER={number}')
    print(f'ISSUE_URL={fields.get("ISSUE_URL", "")}')

    if fields.get('ISSUE_STATE') == 'CLOSED':
        print('ISSUE_STATE=CLOSED')
        print(f'Issue {repo}#{number} is already closed; no comment posted.', file=sys.stderr)
        return ALREADY_CLOSED

    sys.stdout.flush()
    close = subprocess.run(
        ['gh', 'issue', 'close', number, '--repo', repo, '--comment', comment],
        check=False,
        stdout=sys.stderr,
    )
    if close.returncode != 0:
        print(f'ERROR: gh issue close failed for {repo}#{number}.', file=sys.stderr)
        return GH_FAILED

    print('ISSUE_STATE=CLOSED')
    return CLOSED


class CloseCommand(NamedTuple):
    """The wording of one skill's close-issue entry point; the behavior is shared."""

    description: str
    option: str
    option_help: str
    comment_help: str
    missing_label: str
    not_found: str
    comment: str


CLOSE_USAGE = """
Usage:
  close-issue.py --issue <issue> {option} <path> [--comment <text>]

Options:
  --issue <issue>    An issue URL, OWNER/REPO#N, #N, or N. The bare forms
                     resolve against the repository in the current directory.
{option_help}
  --comment <text>   Replace the default closing comment, which names the
{comment_help}
  -h, --help         Show this help text.

Output (key=value lines):
  RESULT, ISSUE_REPO, ISSUE_NUMBER, ISSUE_URL, ISSUE_STATE

Results (RESULT / exit code):
  SUCCESS          0  The comment was posted and the issue is now closed
  ALREADY_CLOSED   5  The issue was already closed; nothing was changed
  ISSUE_NOT_FOUND  4  The repository has no issue with that number
  GH_UNAVAILABLE   3  gh is missing, unauthenticated, or its API call failed
  PREFLIGHT_ERROR  2  Usage or preflight error (not a repo, missing {missing_label})
  SCRIPT_FAILURE   1  Unhandled error
  SIGNAL_HUP     129  Interrupted by HUP
  SIGNAL_INT     130  Interrupted by INT
  SIGNAL_TERM    143  Interrupted by TERM
"""

CLOSE_RESULTS = {
    GH_FAILED: 'GH_UNAVAILABLE',
    NOT_FOUND: 'ISSUE_NOT_FOUND',
    ALREADY_CLOSED: 'ALREADY_CLOSED',
}


def run_close(command: CloseCommand, script: str, arguments: list[str]) -> int:
    """Close the issue a document now tracks, linking the document in a comment."""
    usage = help_header(command.description, script) + CLOSE_USAGE.format(**command._asdict())
    values = {'--issue': '', command.option: '', '--comment': ''}
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument in values:
            if not remaining:
                print_error(f'Missing value for {argument}')
                return 2
            values[argument] = remaining.pop(0)
        elif argument in ('-h', '--help'):
            print(usage, end='')
            return 0
        else:
            print_error(f'Unknown argument: {argument}')
            print(usage, end='', file=sys.stderr)
            return 2
    for required in ('--issue', command.option):
        if not values[required]:
            print_error(f'Missing {required}.')
            print(usage, end='', file=sys.stderr)
            return 2

    ref = parse_issue_ref(values['--issue'])
    if ref is None:
        print_error(
            f'Unrecognized issue reference: {values["--issue"]} '
            '(use a URL, OWNER/REPO#N, #N, or N).'
        )
        return 2
    try:
        repo_root = require_git_repo()
    except Stop as stop:
        return stop.code
    path = values[command.option]
    if not (repo_root / path).is_file():
        print_error(f'{command.not_found}: {path} (relative to {repo_root}).')
        return 2
    if not require_gh():
        return GH_FAILED

    comment, repo, current_repo = values['--comment'], ref.repo, ''
    if not repo or not comment:
        resolved = resolve_current_repo()
        if resolved is None:
            print_error(
                'Could not resolve the current repository; pass OWNER/REPO#N or an issue URL.'
            )
            return GH_FAILED
        current_repo = resolved
    repo = repo or current_repo
    if not comment:
        branch = _run('git', 'rev-parse', '--abbrev-ref', 'HEAD').stdout.strip()
        comment = command.comment.format(path=path, branch=branch, repo=current_repo)
    return close_issue_with_comment(repo, ref.number, comment)


def main(arguments: list[str]) -> int:
    """Run one command-line request; exit 1 for an unparsable reference, 2 for bad usage."""
    if len(arguments) == 2 and arguments[0] == 'parse':
        ref = parse_issue_ref(arguments[1])
        if ref is None:
            return 1
        print(f'ISSUE_REPO={ref.repo}')
        print(f'ISSUE_NUMBER={ref.number}')
        return 0
    if len(arguments) == 4 and arguments[0] == 'close':
        return close_issue_with_comment(*arguments[1:])
    if arguments in (['-h'], ['--help']):
        print(USAGE, end='')
        return 0
    print(USAGE, end='', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
