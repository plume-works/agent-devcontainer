#!/usr/bin/env python3

"""Behavior tests for the pr-request-ai-review trigger script."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

import pytest

SCRIPT_PATH = 'skills/pr-request-ai-review/agent-code/request-review.sh'

REPO = 'octo/repo'
PR_NUMBER = '42'
HEAD_SHA = 'a' * 40
OLD_SHA = 'b' * 40
ARRIVAL = '2026-09-01T10:00:00Z'
BEFORE_ARRIVAL = '2026-09-01T09:59:00Z'
AFTER_ARRIVAL = '2026-09-01T10:05:00Z'
POSTED_URL = 'https://github.com/octo/repo/pull/42#issuecomment-900'
EXISTING_URL = 'https://github.com/octo/repo/pull/42#issuecomment-100'

GH_STUB = """
import json
import os
import sys

fixture = json.loads(open(os.environ['GH_STUB_FIXTURE']).read())
arguments = sys.argv[1:]
if fixture.get('fail'):
    print('simulated network failure', file=sys.stderr)
    sys.exit(1)
if arguments[:2] == ['auth', 'status']:
    sys.exit(0)
if arguments[:2] == ['repo', 'view']:
    print('octo/repo')
    sys.exit(0)
if arguments[:1] != ['api']:
    sys.exit(1)
method = 'GET'
fields = {}
endpoint = None
index = 1
while index < len(arguments):
    argument = arguments[index]
    if argument in ('-X', '--method'):
        method = arguments[index + 1]
        index += 2
        continue
    if argument in ('-f', '--raw-field'):
        key, value = arguments[index + 1].split('=', 1)
        fields[key] = value
        index += 2
        continue
    if argument.startswith('-'):
        index += 1
        continue
    endpoint = argument
    index += 1
base = 'repos/octo/repo/'
if endpoint == base + 'pulls/42':
    if fixture['pr'] is None:
        print(json.dumps({'message': 'Not Found', 'status': '404'}))
        print('gh: Not Found (HTTP 404)', file=sys.stderr)
        sys.exit(1)
    print(json.dumps(fixture['pr']))
elif endpoint == base + 'pulls/42/reviews':
    print(json.dumps(fixture['reviews']))
elif endpoint == base + 'issues/42/comments' and method == 'POST':
    open(os.environ['GH_STUB_POSTED'], 'w').write(fields['body'])
    print(json.dumps({'html_url': fixture['posted_url']}))
elif endpoint == base + 'issues/42/comments':
    print(json.dumps(fixture['comments']))
elif endpoint == base + 'commits/' + fixture['pr']['head']['sha'] + '/check-suites':
    suites = fixture['check_suites']
    print(json.dumps({'total_count': len(suites), 'check_suites': suites}))
else:
    print('unexpected endpoint ' + str(endpoint), file=sys.stderr)
    sys.exit(1)
"""


def make_fixture(**overrides: Any) -> dict[str, Any]:
    """Build an open pull request with no reviews, no comments, and one check suite."""
    fixture: dict[str, Any] = {
        'pr': {'state': 'open', 'head': {'sha': HEAD_SHA}},
        'reviews': [],
        'comments': [],
        'check_suites': [{'created_at': ARRIVAL}],
        'posted_url': POSTED_URL,
    }
    fixture.update(overrides)
    return fixture


def review(login: str, commit_id: str, state: str = 'APPROVED') -> dict[str, Any]:
    """Build a pull request review as the reviews endpoint returns it."""
    return {'user': {'login': login}, 'commit_id': commit_id, 'state': state}


def comment(body: str, created_at: str, url: str = EXISTING_URL) -> dict[str, Any]:
    """Build an issue comment as the comments endpoint returns it."""
    return {'body': body, 'created_at': created_at, 'html_url': url}


def marker(sha: str) -> str:
    """Return the review-head marker the script appends to a trigger."""
    return f'<!-- review-head: {sha} -->'


def install_stub_path(path: Path, *, with_gh: bool = True) -> Path:
    """Create a PATH directory holding only the commands the script needs."""
    stub_directory = path / 'stub-bin'
    stub_directory.mkdir(parents=True, exist_ok=True)
    for command in ('bash', 'cat', 'dirname', 'jq'):
        executable = shutil.which(command)
        assert executable is not None
        (stub_directory / command).symlink_to(executable)
    if with_gh:
        stub = stub_directory / 'gh'
        stub.write_text(f'#!{sys.executable}\n{GH_STUB}')
        stub.chmod(0o755)
    return stub_directory


def run_script(
    plugin_root: Path,
    work_path: Path,
    fixture: dict[str, Any],
    *arguments: str,
    with_gh: bool = True,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    """Run the trigger script against `fixture` with `PATH` limited to the stubs."""
    fixture_file = work_path / 'fixture.json'
    fixture_file.write_text(json.dumps(fixture))
    posted_file = work_path / 'posted.txt'
    environment = dict(os.environ)
    environment['PATH'] = str(install_stub_path(work_path, with_gh=with_gh))
    environment['GH_STUB_FIXTURE'] = str(fixture_file)
    environment['GH_STUB_POSTED'] = str(posted_file)
    completed = subprocess.run(
        [str(plugin_root / SCRIPT_PATH), *arguments],
        cwd=work_path,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    return completed, posted_file


def outcome(completed: subprocess.CompletedProcess[str]) -> tuple[int, str]:
    """Return the exit code and the last stdout line."""
    return completed.returncode, completed.stdout.splitlines()[-1]


def test_no_review_and_no_trigger_posts_marked_trigger(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A head with nothing on it gets one trigger carrying the rationale and marker."""
    # Arrange
    fixture = make_fixture()

    # Act
    completed, posted = run_script(
        plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER, '--rationale', 'New timer path.'
    )

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert f'COMMENT_URL={POSTED_URL}' in completed.stdout.splitlines()
    assert f'HEAD_SHA={HEAD_SHA}' in completed.stdout.splitlines()
    assert f'PR_NUMBER={PR_NUMBER}' in completed.stdout.splitlines()
    body = posted.read_text()
    assert body.startswith('@claude review\n')
    assert body.splitlines()[1] == 'New timer path.'
    assert body.endswith(marker(HEAD_SHA))


def test_trigger_without_rationale_is_command_then_marker(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Without a rationale the body is the command line followed by the marker."""
    completed, posted = run_script(
        plugin_root, plugin_tmp_path, make_fixture(), '--pr', PR_NUMBER, '--repo', REPO
    )

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert posted.read_text() == f'@claude review\n{marker(HEAD_SHA)}'


@pytest.mark.parametrize(
    'login', ['claude[bot]', 'github-actions[bot]', 'chatgpt-codex-connector[bot]']
)
def test_accepted_review_on_head_posts_nothing(
    plugin_root: Path, plugin_tmp_path: Path, login: str
) -> None:
    """An accepted reviewer's review of the head means no trigger is needed."""
    fixture = make_fixture(reviews=[review(login, HEAD_SHA, 'COMMENTED')])

    completed, posted = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (3, 'RESULT=ALREADY_REVIEWED')
    assert 'COMMENT_URL=' in completed.stdout.splitlines()
    assert not posted.exists()


def test_accepted_review_on_older_commit_still_posts(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A review of an earlier head does not cover the current one."""
    fixture = make_fixture(reviews=[review('claude[bot]', OLD_SHA)])

    completed, posted = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert posted.exists()


def test_review_by_unaccepted_author_on_head_still_posts(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A human or other bot reviewing the head is not an AI review."""
    fixture = make_fixture(reviews=[review('octocat', HEAD_SHA)])

    completed, posted = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert posted.exists()


def test_marked_trigger_for_head_posts_nothing_even_before_arrival(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A marker names its commit whatever the comment's date."""
    fixture = make_fixture(
        comments=[comment(f'@claude review\n{marker(HEAD_SHA)}', BEFORE_ARRIVAL)]
    )

    completed, posted = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (4, 'RESULT=ALREADY_REQUESTED')
    assert f'COMMENT_URL={EXISTING_URL}' in completed.stdout.splitlines()
    assert not posted.exists()


def test_marked_trigger_for_another_commit_still_posts_even_after_arrival(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A marker for another commit never counts for the head."""
    fixture = make_fixture(comments=[comment(f'@claude review\n{marker(OLD_SHA)}', AFTER_ARRIVAL)])

    completed, posted = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert posted.exists()


@pytest.mark.parametrize('command', ['@claude review', '@Claude Review', '@CLAUDE REVIEW light'])
def test_hand_typed_trigger_after_arrival_posts_nothing(
    plugin_root: Path, plugin_tmp_path: Path, command: str
) -> None:
    """An unmarked trigger created after the head arrived counts, in any letter case."""
    fixture = make_fixture(comments=[comment(command, AFTER_ARRIVAL)])

    completed, posted = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (4, 'RESULT=ALREADY_REQUESTED')
    assert f'COMMENT_URL={EXISTING_URL}' in completed.stdout.splitlines()
    assert not posted.exists()


def test_hand_typed_trigger_before_arrival_still_posts(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """An unmarked trigger older than the head may belong to the previous head."""
    fixture = make_fixture(comments=[comment('@claude review', BEFORE_ARRIVAL)])

    completed, posted = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert posted.exists()


def test_earliest_check_suite_dates_the_head(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """The head's arrival is the earliest suite, not the first one listed."""
    fixture = make_fixture(
        check_suites=[{'created_at': '2026-09-01T11:00:00Z'}, {'created_at': ARRIVAL}],
        comments=[comment('@claude review', AFTER_ARRIVAL)],
    )

    completed, posted = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (4, 'RESULT=ALREADY_REQUESTED')
    assert not posted.exists()


def test_hand_typed_trigger_on_head_without_check_suite_still_posts(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A head with no check suite has no arrival time, so no unmarked trigger counts."""
    fixture = make_fixture(check_suites=[], comments=[comment('@claude review', AFTER_ARRIVAL)])

    completed, posted = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert posted.exists()


def test_mid_body_mention_is_not_a_trigger(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """Only a comment that opens with the command is a trigger."""
    fixture = make_fixture(comments=[comment('Please run @claude review again.', AFTER_ARRIVAL)])

    completed, posted = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert posted.exists()


def test_closed_pull_request_is_not_open(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A closed or merged pull request gets no trigger."""
    fixture = make_fixture(pr={'state': 'closed', 'head': {'sha': HEAD_SHA}})

    completed, posted = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (5, 'RESULT=PR_NOT_OPEN')
    assert not posted.exists()


def test_missing_pull_request_is_not_open(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A pull request the API cannot find is reported like a closed one."""
    fixture = make_fixture(pr=None)

    completed, _ = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (5, 'RESULT=PR_NOT_OPEN')


def test_failing_gh_call_is_gh_unavailable(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A gh call that fails for any other reason routes to the fallback code."""
    fixture = make_fixture(fail=True)

    completed, posted = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (6, 'RESULT=GH_UNAVAILABLE')
    assert not posted.exists()


def test_missing_gh_is_gh_unavailable(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A PATH without gh produces the same fallback code."""
    completed, _ = run_script(
        plugin_root, plugin_tmp_path, make_fixture(), '--pr', PR_NUMBER, with_gh=False
    )

    assert outcome(completed) == (6, 'RESULT=GH_UNAVAILABLE')


def test_missing_pr_is_preflight_error(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """The pull request number is required."""
    completed, _ = run_script(plugin_root, plugin_tmp_path, make_fixture())

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')


def test_multi_line_rationale_is_preflight_error(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """The rationale must stay one line under the command."""
    completed, posted = run_script(
        plugin_root, plugin_tmp_path, make_fixture(), '--pr', PR_NUMBER, '--rationale', 'one\ntwo'
    )

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert not posted.exists()


def test_help_lists_options_keys_and_results(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """Help names every option, output key, and result."""
    completed, _ = run_script(plugin_root, plugin_tmp_path, make_fixture(), '--help')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    for word in (
        '--pr',
        '--rationale',
        '--repo',
        'COMMENT_URL',
        'HEAD_SHA',
        'ALREADY_REVIEWED',
        'ALREADY_REQUESTED',
        'PR_NOT_OPEN',
        'GH_UNAVAILABLE',
    ):
        assert word in completed.stdout


def test_result_is_last_stdout_line_on_every_path(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Every run ends stdout with exactly one RESULT line."""
    cases = [
        make_fixture(),
        make_fixture(reviews=[review('claude[bot]', HEAD_SHA)]),
        make_fixture(comments=[comment('@claude review', AFTER_ARRIVAL)]),
        make_fixture(pr={'state': 'closed', 'head': {'sha': HEAD_SHA}}),
        make_fixture(fail=True),
    ]
    for index, fixture in enumerate(cases):
        work_path = plugin_tmp_path / f'case-{index}'
        work_path.mkdir()
        completed, _ = run_script(plugin_root, work_path, fixture, '--pr', PR_NUMBER)
        lines = completed.stdout.splitlines()
        assert lines[-1].startswith('RESULT=')
        assert sum(line.startswith('RESULT=') for line in lines) == 1
