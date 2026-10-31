#!/usr/bin/env python3

"""
Request an AI review of a pull request's head commit by toggling the author's assignment.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import result_codes as rc  # noqa: E402  (path set above so the plugin's bin/ resolves)
from skill_common import print_error, Stop  # noqa: E402

ALREADY_REVIEWED = 3
ALREADY_REQUESTED = 4
PR_NOT_OPEN = 5
GH_UNAVAILABLE = 6
PREFLIGHT_ERROR = 2

RESPONDER = 'Claude PR Review Responder'

USAGE = """\
Request an AI review of a pull request's head commit by toggling the author's
assignment, at most once per head.

Usage:
  request-review.py --pr <number> [--rationale <one line>] [--repo <owner/repo>]

Options:
  --pr <number>          Pull request to request a review for. Required.
  --rationale <line>     One line naming what the reviewer has not seen yet,
                         posted as a plain comment after the toggle.
  --repo <owner/repo>    Repository. Default: the current checkout's repository.
  -h, --help             Show this help text.

An assigned author is removed and added back; an unassigned one is added and
removed, so the assignees end as they were found. The request is refused when
an accepted AI review already names the head, or a Claude PR Review Responder
check on the head is queued, in progress, or completed other than skipped or
cancelled.

Output:
  RESULT is always the last line of stdout.
  PR_NUMBER    the pull request number
  HEAD_SHA     the head commit the decision applies to
  CHECK_URL    the responder check behind ALREADY_REQUESTED; empty otherwise
  COMMENT_URL  the posted rationale comment; empty when none was posted

Results (RESULT / exit code):
  SUCCESS            0  The author's assignment was toggled for the head
  ALREADY_REVIEWED   3  An accepted AI review's commit is the head
  ALREADY_REQUESTED  4  A Claude PR Review Responder check on the head counts as a request
  PR_NOT_OPEN        5  The pull request is closed, merged, or not found
  GH_UNAVAILABLE     6  gh is missing, unauthenticated, or an API call failed, the toggle too
  PREFLIGHT_ERROR    2  Missing --pr, unknown argument, or multi-line rationale
  SCRIPT_FAILURE     1  Unhandled error
  SIGNAL_HUP       129  Interrupted by HUP
  SIGNAL_INT       130  Interrupted by INT
  SIGNAL_TERM      143  Interrupted by TERM
"""


def parse_arguments(arguments: list[str]) -> tuple[str, str, str]:
    """Return the pull request number, rationale, and repository."""
    values = {'--pr': '', '--rationale': '', '--repo': ''}
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument in values:
            if not remaining:
                print_error(f'Missing value for {argument}')
                raise Stop(PREFLIGHT_ERROR)
            values[argument] = remaining.pop(0)
        elif argument in ('-h', '--help'):
            print(USAGE, end='')
            raise Stop(0)
        else:
            print_error(f'Unknown argument: {argument}')
            print(USAGE, end='', file=sys.stderr)
            raise Stop(PREFLIGHT_ERROR)
    return values['--pr'], values['--rationale'], values['--repo']


def gh(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run gh with stdout captured and stderr passed through."""
    sys.stdout.flush()
    return subprocess.run(['gh', *arguments], check=False, stdout=subprocess.PIPE, text=True)


def json_values(text: str) -> list[Any]:
    """Decode every JSON value in `text`, as --paginate concatenates one per page."""
    decoder = json.JSONDecoder()
    values, index = [], 0
    while True:
        while index < len(text) and text[index].isspace():
            index += 1
        if index == len(text):
            return values
        value, index = decoder.raw_decode(text, index)
        values.append(value)


def fetch_list(endpoint: str, key: str | None) -> list[Any] | None:
    """Collect every page of a list endpoint; `key` names the item list inside each page."""
    pages = gh('api', '--paginate', endpoint)
    if pages.returncode != 0:
        return None
    items: list[Any] = []
    for page in json_values(pages.stdout):
        items.extend(page[key] if key else page)
    return items


def finish(check_url: str, comment_url: str, code: int) -> int:
    """Print the two URL keys and return `code`."""
    print(f'CHECK_URL={check_url}')
    print(f'COMMENT_URL={comment_url}')
    return code


def reviewed(reviews: list[dict[str, Any]], head_sha: str) -> bool:
    """Return whether an accepted AI review names the head (reviewers: spec/ai-review-gate)."""
    return any(
        (item.get('user') or {}).get('login') in ('claude[bot]', 'github-actions[bot]')
        and str(item.get('state') or '').upper() in ('APPROVED', 'CHANGES_REQUESTED', 'COMMENTED')
        and item.get('commit_id') == head_sha
        for item in reviews
    )


def requesting_check(runs: list[dict[str, Any]]) -> str:
    """Return the URL of a responder check that counts as a request (spec/ai-review-refresh)."""
    for run in runs:
        if run.get('name') == RESPONDER and (
            run.get('status') != 'completed'
            or run.get('conclusion') not in ('skipped', 'cancelled')
        ):
            return run.get('html_url') or ''
    return ''


def jq_raw(value: Any) -> str:
    """Return `value` as `jq -r` prints it."""
    if value is None:
        return 'null'
    if isinstance(value, str):
        return value
    return json.dumps(value)


def run(arguments: list[str]) -> int:
    """Decide whether the head still needs a review, and request it when it does."""
    pr_number, rationale, repo = parse_arguments(arguments)
    if not re.fullmatch(r'[0-9]+', pr_number):
        print_error('--pr must be a pull request number.')
        return PREFLIGHT_ERROR
    if '\n' in rationale or '\r' in rationale:
        print_error('--rationale must be a single line.')
        return PREFLIGHT_ERROR
    if shutil.which('gh') is None:
        print_error('gh not found on PATH.')
        return GH_UNAVAILABLE

    if not repo:
        view = gh('repo', 'view', '--json', 'nameWithOwner', '--jq', '.nameWithOwner')
        repo = view.stdout.strip()
        if view.returncode != 0 or not repo:
            print_error('Could not resolve the repository; pass --repo.')
            return GH_UNAVAILABLE

    response = gh('api', f'repos/{repo}/pulls/{pr_number}')
    if response.returncode != 0:
        try:
            status = json.loads(response.stdout).get('status')
        except (json.JSONDecodeError, AttributeError):
            status = None
        if str(status) == '404':
            print_error(f'Pull request {repo}#{pr_number} was not found.')
            return PR_NOT_OPEN
        print_error(f'Could not read pull request {repo}#{pr_number}.')
        return GH_UNAVAILABLE

    pull = json.loads(response.stdout)
    print(f'PR_NUMBER={pr_number}')
    head_sha = jq_raw((pull.get('head') or {}).get('sha'))
    author = jq_raw((pull.get('user') or {}).get('login'))
    author_assigned = any(item.get('login') == author for item in pull.get('assignees') or [])
    print(f'HEAD_SHA={head_sha}')
    state = jq_raw(pull.get('state'))
    if state != 'open':
        print_error(f'Pull request {repo}#{pr_number} is {state}.')
        return finish('', '', PR_NOT_OPEN)

    # A reaction names no commit, so it cannot show that the head was reviewed.
    reviews = fetch_list(f'repos/{repo}/pulls/{pr_number}/reviews', None)
    if reviews is None:
        print_error(f'Could not read the reviews of {repo}#{pr_number}.')
        return GH_UNAVAILABLE
    if reviewed(reviews, head_sha):
        return finish('', '', ALREADY_REVIEWED)

    runs = fetch_list(f'repos/{repo}/commits/{head_sha}/check-runs', 'check_runs')
    if runs is None:
        print_error(f'Could not read the check runs of {head_sha}.')
        return GH_UNAVAILABLE
    existing_url = requesting_check(runs)
    if existing_url:
        return finish(existing_url, '', ALREADY_REQUESTED)

    # Adding fires pull_request/assigned; removing fires nothing the responder runs on.
    endpoint = f'repos/{repo}/issues/{pr_number}/assignees'
    if author_assigned:
        first, second, unrestored = 'DELETE', 'POST', f'{author} is no longer assigned'
    else:
        first, second, unrestored = 'POST', 'DELETE', f'{author} is still assigned'
    if gh('api', '-X', first, endpoint, '-f', f'assignees[]={author}').returncode:
        print_error(f"Could not toggle {author}'s assignment on {repo}#{pr_number}.")
        return GH_UNAVAILABLE
    if gh('api', '-X', second, endpoint, '-f', f'assignees[]={author}').returncode:
        print_error(f'Could not restore the assignees of {repo}#{pr_number}: {unrestored}.')
        return GH_UNAVAILABLE

    comment_url = ''
    if rationale:
        body = f'AI review requested for {head_sha}: {rationale}'
        posted = gh(
            'api', '-X', 'POST', f'repos/{repo}/issues/{pr_number}/comments', '-f', f'body={body}'
        )
        if posted.returncode:
            print_error(
                f'Requested the review but could not post the rationale on {repo}#{pr_number}.'
            )
            return GH_UNAVAILABLE
        comment_url = jq_raw(json.loads(posted.stdout).get('html_url'))
    return finish('', comment_url, 0)


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES.update(
        {
            ALREADY_REVIEWED: 'ALREADY_REVIEWED',
            ALREADY_REQUESTED: 'ALREADY_REQUESTED',
            PR_NOT_OPEN: 'PR_NOT_OPEN',
            GH_UNAVAILABLE: 'GH_UNAVAILABLE',
        }
    )
    rc.install()
    rc.run(main)
