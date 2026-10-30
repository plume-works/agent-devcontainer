#!/usr/bin/env python3

"""
Create and submit a GitHub PR review with all inline comments in one call.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import result_codes as rc  # noqa: E402  (path set above so the plugin's bin/ resolves)
from skill_common import print_error, run_tool, Stop  # noqa: E402

GH_CALL_FAILED = 3
PREFLIGHT_ERROR = 2

EVENTS = ('COMMENT', 'APPROVE', 'REQUEST_CHANGES')

USAGE = """\
Create and submit a GitHub PR review with all inline comments in a
single atomic call -- no pending-review/add-comment/submit dance.

Usage:
  post-review.py --pr <PR_NUMBER> --event <COMMENT|APPROVE|REQUEST_CHANGES> \\
    --summary-file <path> [--comments-file <path>] [--repo <owner/name>]

--summary-file must be a plain file (write it with the Write tool
first) containing only the short overall summary -- no per-finding
detail, since findings live in the inline comments.

--comments-file, if given, must be a plain JSON file (write it with
the Write tool first) containing an array of findings, e.g.:
  [
    {"path": "src/foo.py", "line": 42, "side": "RIGHT", "body": "..."},
    {"path": "src/bar.cpp", "line": 7, "side": "RIGHT", "body": "..."}
  ]
Omit --comments-file (or pass a file containing []) when there are no
validated findings to attach.

Output (key=value lines):
  RESULT
  On success the created review object is printed before the RESULT
  line, verbatim as the GitHub API returned it.

Results (RESULT / exit code):
  SUCCESS          0  The review was created and submitted
  GH_CALL_FAILED   3  A gh API call failed (repo/PR lookup, or the review POST)
  PREFLIGHT_ERROR  2  Usage error, a missing or malformed input file, or gh
                      missing or unauthenticated
  SCRIPT_FAILURE   1  Unhandled error
"""

OPTIONS = ('--pr', '--event', '--summary-file', '--comments-file', '--repo')


def preflight(message: str) -> Stop:
    """Report a preflight failure as a Stop."""
    print_error(message)
    return Stop(PREFLIGHT_ERROR)


def parse_arguments(arguments: list[str]) -> dict[str, str]:
    """Return the option values, stopping at a usage error or help."""
    values = dict.fromkeys(OPTIONS, '')
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument in values:
            value = remaining.pop(0) if remaining else ''
            if not value:
                raise preflight(f'Missing required argument: {argument}')
            values[argument] = value
        elif argument in ('-h', '--help'):
            print(USAGE, end='')
            raise Stop(0)
        else:
            print_error(f'Unknown argument: {argument}')
            print(USAGE, end='', file=sys.stderr)
            raise Stop(PREFLIGHT_ERROR)
    for required in ('--pr', '--event', '--summary-file'):
        if not values[required]:
            raise preflight(f'Missing required argument: {required}')
    return values


def require_body_file(path: str) -> None:
    """Stop unless `path` is a file the caller already wrote."""
    if not Path(path).is_file():
        raise preflight(
            f'Body file not found: {path}. Write the text with the Write tool first, '
            'then pass its path.'
        )


def json_values(text: str) -> list[Any]:
    """Decode every JSON value in `text`, as `jq --slurpfile` reads a file."""
    decoder = json.JSONDecoder()
    values, index = [], 0
    while True:
        while index < len(text) and text[index].isspace():
            index += 1
        if index == len(text):
            return values
        value, index = decoder.raw_decode(text, index)
        values.append(value)


def run(arguments: list[str]) -> int:
    """Build the review payload and post it in one call."""
    values = parse_arguments(arguments)
    require_body_file(values['--summary-file'])
    event = values['--event']
    if event not in EVENTS:
        raise preflight(
            f'Invalid --event: {event} (expected COMMENT, APPROVE, or REQUEST_CHANGES)'
        )
    if shutil.which('gh') is None:
        raise preflight('gh CLI not found on PATH.')
    if run_tool('gh', 'auth', 'status').returncode != 0:
        raise preflight('gh is not authenticated.')

    comments_file = values['--comments-file']
    if comments_file:
        require_body_file(comments_file)

    pr_number = values['--pr']
    repo = values['--repo']
    sys.stdout.flush()
    if not repo:
        view = subprocess.run(
            ['gh', 'repo', 'view', '--json', 'nameWithOwner', '-q', '.nameWithOwner'],
            check=False,
            stdout=subprocess.PIPE,
            text=True,
        )
        if view.returncode != 0:
            print_error(
                'gh repo view failed; could not resolve the current repository. '
                'Pass --repo <owner/name>.'
            )
            return GH_CALL_FAILED
        repo = view.stdout.rstrip('\n')

    head = subprocess.run(
        [
            'gh',
            'pr',
            'view',
            pr_number,
            '--repo',
            repo,
            '--json',
            'headRefOid',
            '-q',
            '.headRefOid',
        ],
        check=False,
        stdout=subprocess.PIPE,
        text=True,
    )
    if head.returncode != 0:
        print_error(f'gh pr view failed for pull request {pr_number} in {repo}.')
        return GH_CALL_FAILED

    try:
        comments_values = json_values(Path(comments_file).read_text()) if comments_file else [[]]
    except (json.JSONDecodeError, UnicodeDecodeError):
        print_error(
            f'Could not build the review payload; check that {comments_file} holds a valid JSON array.'
        )
        return PREFLIGHT_ERROR
    payload = {
        'commit_id': head.stdout.rstrip('\n'),
        'event': event,
        'body': Path(values['--summary-file']).read_text(),
        'comments': comments_values[0] if comments_values else None,
    }

    review = subprocess.run(
        [
            'gh',
            'api',
            f'repos/{repo}/pulls/{pr_number}/reviews',
            '--method',
            'POST',
            '--input',
            '-',
        ],
        check=False,
        input=json.dumps(payload),
        stdout=subprocess.PIPE,
        text=True,
    )
    if review.returncode != 0:
        print_error(f'gh api review POST failed for pull request {pr_number} in {repo}.')
        print(
            'If the error names a comment that cannot be placed inline, drop that entry from '
            'the comments file, rerun, and post it as a normal PR comment.',
            file=sys.stderr,
        )
        return GH_CALL_FAILED

    print(review.stdout.rstrip('\n'))
    return 0


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES[GH_CALL_FAILED] = 'GH_CALL_FAILED'
    rc.install()
    rc.run(main)
