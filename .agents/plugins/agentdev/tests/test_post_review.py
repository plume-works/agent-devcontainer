#!/usr/bin/env python3

"""Behavior tests for the pr-review post-review script."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from git_fixtures import outcome
import pytest

SCRIPT_PATH = 'skills/pr-review/agent-code/post-review.py'
TOOLS = ('python3',)
HEAD_SHA = 'c' * 40
REVIEW = {'id': 501, 'state': 'COMMENTED', 'html_url': 'https://github.com/octo/repo/pull/7#r501'}

GH_STUB = """
import json
import os
import sys

fixture = json.loads(open(os.environ['GH_STUB_FIXTURE']).read())
arguments = sys.argv[1:]
if arguments[:2] == ['auth', 'status']:
    sys.exit(fixture.get('auth', 0))
if arguments[:2] == ['repo', 'view']:
    print('octo/repo')
    sys.exit(0)
if arguments[:2] == ['pr', 'view']:
    if fixture.get('view_fails'):
        sys.exit(1)
    print(fixture['head'])
    sys.exit(0)
if arguments[:1] == ['api']:
    payload = sys.stdin.read()
    open(os.environ['GH_STUB_FIXTURE'] + '.calls', 'a').write(
        json.dumps({'arguments': arguments, 'payload': json.loads(payload)}) + '\\n'
    )
    if fixture.get('post_fails'):
        print('gh: Unprocessable Entity (HTTP 422)', file=sys.stderr)
        sys.exit(1)
    print(json.dumps(fixture['review']))
    sys.exit(0)
sys.exit(1)
"""


def make_fixture(**overrides: Any) -> dict[str, Any]:
    """Build an authenticated gh whose pull request head and review POST succeed."""
    return {'head': HEAD_SHA, 'review': REVIEW, **overrides}


def run_script(
    plugin_root: Path,
    work: Path,
    fixture: dict[str, Any] | None,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    """Run the script in `work` with PATH limited to its tools and, unless None, a gh stub."""
    stubs = work / 'stub-bin'
    stubs.mkdir(exist_ok=True)
    for tool in TOOLS:
        if not (stubs / tool).exists():
            found = shutil.which(tool)
            assert found is not None
            (stubs / tool).symlink_to(found)
    environment = {**os.environ, 'PATH': str(stubs)}
    if fixture is not None:
        (work / 'gh-fixture.json').write_text(json.dumps(fixture))
        gh = stubs / 'gh'
        gh.write_text(f'#!{sys.executable}\n{GH_STUB}')
        gh.chmod(0o755)
        environment['GH_STUB_FIXTURE'] = str(work / 'gh-fixture.json')
    return subprocess.run(
        [str(plugin_root / SCRIPT_PATH), *arguments],
        cwd=work,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def posted(work: Path) -> list[dict[str, Any]]:
    """Return every gh api call the stub received."""
    calls = work / 'gh-fixture.json.calls'
    return [json.loads(line) for line in calls.read_text().splitlines()] if calls.exists() else []


@pytest.fixture
def work(plugin_tmp_path: Path) -> Path:
    """Create a directory holding a summary file."""
    (plugin_tmp_path / 'summary.md').write_text('Overall summary.\n')
    return plugin_tmp_path


def test_review_is_posted_with_comments_in_one_call(plugin_root: Path, work: Path) -> None:
    """The summary, event, head commit, and comments go out in a single review POST."""
    comments = [{'path': 'src/foo.py', 'line': 42, 'side': 'RIGHT', 'body': 'Finding.'}]
    (work / 'comments.json').write_text(json.dumps(comments))

    completed = run_script(
        plugin_root, work, make_fixture(),
        '--pr', '7', '--event', 'REQUEST_CHANGES',
        '--summary-file', 'summary.md', '--comments-file', 'comments.json',
    )  # fmt: skip

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert json.loads(completed.stdout.splitlines()[0]) == REVIEW
    [call] = posted(work)
    assert call['arguments'][:2] == ['api', 'repos/octo/repo/pulls/7/reviews']
    assert call['payload'] == {
        'commit_id': HEAD_SHA,
        'event': 'REQUEST_CHANGES',
        'body': 'Overall summary.\n',
        'comments': comments,
    }


def test_without_comments_an_empty_list_is_sent(plugin_root: Path, work: Path) -> None:
    """Omitting --comments-file posts the review with no inline comments."""
    completed = run_script(
        plugin_root, work, make_fixture(),
        '--pr', '7', '--event', 'COMMENT', '--summary-file', 'summary.md', '--repo', 'octo/other',
    )  # fmt: skip

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    [call] = posted(work)
    assert call['arguments'][1] == 'repos/octo/other/pulls/7/reviews'
    assert call['payload']['comments'] == []


@pytest.mark.parametrize(
    ('fixture', 'message'),
    [
        (make_fixture(view_fails=True), 'gh pr view failed for pull request 7 in octo/repo.'),
        (make_fixture(post_fails=True), 'gh api review POST failed for pull request 7'),
    ],
)
def test_gh_call_failures(
    plugin_root: Path, work: Path, fixture: dict[str, Any], message: str
) -> None:
    """A failing pull request lookup or review POST reports GH_CALL_FAILED."""
    completed = run_script(
        plugin_root,
        work,
        fixture,
        '--pr',
        '7',
        '--event',
        'APPROVE',
        '--summary-file',
        'summary.md',
    )

    assert outcome(completed) == (3, 'RESULT=GH_CALL_FAILED')
    assert f'ERROR: {message}' in completed.stderr


@pytest.mark.parametrize(
    ('arguments', 'fixture', 'message'),
    [
        (['--event', 'COMMENT', '--summary-file', 'summary.md'], make_fixture(),
         'Missing required argument: --pr'),
        (['--pr', '7', '--event', 'MERGE', '--summary-file', 'summary.md'], make_fixture(),
         'Invalid --event: MERGE'),
        (['--pr', '7', '--event', 'COMMENT', '--summary-file', 'absent.md'], make_fixture(),
         'Body file not found: absent.md.'),
        (['--pr', '7', '--event', 'COMMENT', '--summary-file', 'summary.md',
          '--comments-file', 'absent.json'], make_fixture(), 'Body file not found: absent.json.'),
        (['--pr', '7', '--event', 'COMMENT', '--summary-file', 'summary.md', '--bogus'],
         make_fixture(), 'Unknown argument: --bogus'),
        (['--pr', '7', '--event', 'COMMENT', '--summary-file', 'summary.md'], None,
         'gh CLI not found on PATH.'),
        (['--pr', '7', '--event', 'COMMENT', '--summary-file', 'summary.md'],
         make_fixture(auth=1), 'gh is not authenticated.'),
    ],
)  # fmt: skip
def test_preflight_errors(
    plugin_root: Path,
    work: Path,
    arguments: list[str],
    fixture: dict[str, Any] | None,
    message: str,
) -> None:
    """Usage errors, missing files, and an unusable gh stop before any review is posted."""
    completed = run_script(plugin_root, work, fixture, *arguments)

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert f'ERROR: {message}' in completed.stderr
    assert posted(work) == []


def test_malformed_comments_file_is_a_preflight_error(plugin_root: Path, work: Path) -> None:
    """A comments file that is not JSON cannot become a payload."""
    (work / 'comments.json').write_text('[{"path": ')

    completed = run_script(
        plugin_root, work, make_fixture(),
        '--pr', '7', '--event', 'COMMENT',
        '--summary-file', 'summary.md', '--comments-file', 'comments.json',
    )  # fmt: skip

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert 'ERROR: Could not build the review payload' in completed.stderr
    assert posted(work) == []
