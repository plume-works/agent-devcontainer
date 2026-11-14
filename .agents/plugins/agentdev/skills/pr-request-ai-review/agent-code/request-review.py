#!/usr/bin/env python3

"""
Request an AI review of a pull request's head commit by adding the request-ai-review label.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

from datetime import datetime
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
BLOCKED = 7
PREFLIGHT_ERROR = 2

RESPONDER = 'Claude PR Review Responder'
AI_REVIEWER = 'plume-works-quill[bot]'
REQUEST_LABEL = 'request-ai-review'
BLOCK_LABEL = 'block-ai-reviews'

EDITS_QUERY = (
    'query($owner: String!, $name: String!, $number: Int!) {'
    ' repository(owner: $owner, name: $name) { pullRequest(number: $number) {'
    ' lastEditedAt'
    ' timelineItems(itemTypes: [RENAMED_TITLE_EVENT], last: 1) {'
    ' nodes { ... on RenamedTitleEvent { createdAt } } } } } }'
)

USAGE = """\
Request an AI review of a pull request's head commit by adding the
request-ai-review label, at most once per head and title and description.

Usage:
  request-review.py --pr <number> [--rationale <one line>] [--repo <owner/repo>]

Options:
  --pr <number>          Pull request to request a review for. Required.
  --rationale <line>     One line naming what the reviewer has not seen yet,
                         posted as a plain comment after the label.
  --repo <owner/repo>    Repository. Default: the current checkout's repository.
  -h, --help             Show this help text.

A run of the responder removes the label when it picks the request up. A label
still on the pull request while a responder run on the head branch is
unfinished is a pending request; with no unfinished run it is stale, and the
script removes and re-adds it. A review covers the head
together with the title and description it saw, which its run reads when it
starts. Only responder runs started after the latest title or description edit,
and the reviews they submit, count. The request is refused when such an
accepted AI review names the head, or a Claude PR Review Responder check on the
head is queued, in progress, or started after that edit and completed other
than skipped or cancelled, or the label is waiting for an unfinished run.

Output:
  RESULT is always the last line of stdout.
  PR_NUMBER    the pull request number
  HEAD_SHA     the head commit the decision applies to
  CHECK_URL    the responder check behind ALREADY_REQUESTED; empty otherwise
  COMMENT_URL  the posted rationale comment; empty when none was posted

Results (RESULT / exit code):
  SUCCESS            0  The request-ai-review label was added, or re-sent, for the head
  ALREADY_REVIEWED   3  An accepted AI review newer than the last title or description edit
                        names the head
  ALREADY_REQUESTED  4  The label waits for an unfinished responder run, or a Claude PR
                        Review Responder check on the head counts as a request: running,
                        or started after the last title or description edit
  PR_NOT_OPEN        5  The pull request is closed, merged, or not found
  BLOCKED            7  The pull request carries block-ai-reviews; the request label was
                        added, or was already there, and waits until the block is lifted
  GH_UNAVAILABLE     6  gh is missing, unauthenticated, or an API call failed, the label too
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


def fetch_list(endpoint: str, key: str | None, *options: str) -> list[Any] | None:
    """Collect every page of a list endpoint; `key` names the item list inside each page."""
    pages = gh('api', '--paginate', *options, endpoint)
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


def timestamp(value: Any) -> datetime | None:
    """Parse a GitHub ISO 8601 timestamp; None when absent."""
    return datetime.fromisoformat(str(value).replace('Z', '+00:00')) if value else None


def edit_times(repo: str, pr_number: str) -> list[datetime] | None:
    """Return the latest description edit and title rename times; None when gh fails."""
    owner, _, name = repo.partition('/')
    response = gh(
        'api',
        'graphql',
        '-f',
        f'query={EDITS_QUERY}',
        '-f',
        f'owner={owner}',
        '-f',
        f'name={name}',
        '-F',
        f'number={pr_number}',
    )
    if response.returncode != 0:
        return None
    try:
        pull = json.loads(response.stdout)['data']['repository']['pullRequest']
        renames = pull['timelineItems']['nodes']
    except (json.JSONDecodeError, KeyError, TypeError):
        return None
    values = [pull.get('lastEditedAt'), *(node.get('createdAt') for node in renames)]
    return [parsed for parsed in map(timestamp, values) if parsed]


def after(value: Any, cutoff: datetime | None) -> bool:
    """Return whether `value` is newer than the metadata edit cutoff, if there is one."""
    moment = timestamp(value)
    return cutoff is None or (moment is not None and moment > cutoff)


Window = tuple[datetime, datetime | None]


def stale_windows(runs: list[dict[str, Any]], cutoff: datetime | None) -> list[Window]:
    """Return the start and end of each responder run that read metadata older than `cutoff`."""
    windows = []
    for run in runs:
        start = timestamp(run.get('started_at'))
        if run.get('name') == RESPONDER and start and cutoff and start <= cutoff:
            windows.append((start, timestamp(run.get('completed_at'))))
    return windows


def reviewed(
    reviews: list[dict[str, Any]], head_sha: str, cutoff: datetime | None, stale: list[Window]
) -> bool:
    """Return whether an accepted AI review saw the head's input."""

    def from_stale_run(item: dict[str, Any]) -> bool:
        moment = timestamp(item.get('submitted_at'))
        return moment is not None and any(
            start <= moment and (end is None or moment <= end) for start, end in stale
        )

    return any(
        (item.get('user') or {}).get('login') == AI_REVIEWER
        and str(item.get('state') or '').upper() in ('APPROVED', 'CHANGES_REQUESTED', 'COMMENTED')
        and item.get('commit_id') == head_sha
        and after(item.get('submitted_at'), cutoff)
        and not from_stale_run(item)
        for item in reviews
    )


def requesting_check(runs: list[dict[str, Any]], cutoff: datetime | None) -> str:
    """Return the URL of a responder check that counts as a request."""
    for run in runs:
        if run.get('name') == RESPONDER and (
            run.get('status') != 'completed'
            or (
                run.get('conclusion') not in ('skipped', 'cancelled')
                and after(run.get('started_at'), cutoff)
            )
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
    names = {item.get('name') for item in pull.get('labels') or []}
    labelled = REQUEST_LABEL in names
    print(f'HEAD_SHA={head_sha}')
    state = jq_raw(pull.get('state'))
    if state != 'open':
        print_error(f'Pull request {repo}#{pr_number} is {state}.')
        return finish('', '', PR_NOT_OPEN)

    blocked = BLOCK_LABEL in names
    # A run in the pull request's group takes the label; with none left to run, it is stale.
    if labelled and not blocked:
        workflow_runs = fetch_list(
            f'repos/{repo}/actions/workflows/ai-responder.yml/runs',
            'workflow_runs',
            '-X',
            'GET',
            '-f',
            f'branch={jq_raw((pull.get("head") or {}).get("ref"))}',
            '-f',
            'event=pull_request',
            '-f',
            'per_page=50',
        )
        if workflow_runs is None:
            print_error(f'Could not read the responder runs of {repo}#{pr_number}.')
            return GH_UNAVAILABLE
        if any(item.get('status') != 'completed' for item in workflow_runs):
            return finish('', '', ALREADY_REQUESTED)

    edits = edit_times(repo, pr_number)
    if edits is None:
        print_error(f'Could not read the title and description edits of {repo}#{pr_number}.')
        return GH_UNAVAILABLE
    cutoff = max(edits, default=None)

    # A reaction names no commit, so it cannot show that the head was reviewed.
    reviews = fetch_list(f'repos/{repo}/pulls/{pr_number}/reviews', None)
    if reviews is None:
        print_error(f'Could not read the reviews of {repo}#{pr_number}.')
        return GH_UNAVAILABLE
    runs = fetch_list(f'repos/{repo}/commits/{head_sha}/check-runs', 'check_runs')
    if runs is None:
        print_error(f'Could not read the check runs of {head_sha}.')
        return GH_UNAVAILABLE
    if reviewed(reviews, head_sha, cutoff, stale_windows(runs, cutoff)):
        return finish('', '', ALREADY_REVIEWED)

    existing_url = requesting_check(runs, cutoff)
    if existing_url:
        return finish(existing_url, '', ALREADY_REQUESTED)

    labels = f'repos/{repo}/issues/{pr_number}/labels'
    # No review runs while the block is on; the request waits, visibly, for its removal.
    if blocked:
        if (
            not labelled
            and gh('api', '-X', 'POST', labels, '-f', f'labels[]={REQUEST_LABEL}').returncode
        ):
            print_error(f'Could not add {REQUEST_LABEL} to {repo}#{pr_number}.')
            return GH_UNAVAILABLE
        print_error(f'{repo}#{pr_number} carries {BLOCK_LABEL}; the review waits for its removal.')
        return finish('', '', BLOCKED)
    if labelled and gh('api', '-X', 'DELETE', f'{labels}/{REQUEST_LABEL}').returncode:
        print_error(f'Could not remove the stale {REQUEST_LABEL} from {repo}#{pr_number}.')
        return GH_UNAVAILABLE
    if gh('api', '-X', 'POST', labels, '-f', f'labels[]={REQUEST_LABEL}').returncode:
        print_error(f'Could not add {REQUEST_LABEL} to {repo}#{pr_number}.')
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
            BLOCKED: 'BLOCKED',
            PR_NOT_OPEN: 'PR_NOT_OPEN',
            GH_UNAVAILABLE: 'GH_UNAVAILABLE',
        }
    )
    rc.install()
    rc.run(main)
