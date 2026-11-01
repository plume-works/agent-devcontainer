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

SCRIPT_PATH = 'skills/pr-request-ai-review/agent-code/request-review.py'

REPO = 'octo/repo'
PR_NUMBER = '42'
AUTHOR = 'octocat'
HEAD_SHA = 'a' * 40
OLD_SHA = 'b' * 40
RESPONDER = 'Claude PR Review Responder'
CHECK_URL = 'https://github.com/octo/repo/runs/700'
POSTED_URL = 'https://github.com/octo/repo/pull/42#issuecomment-900'
RATIONALE = 'Reworked the retry backoff beyond the thread.'

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
if method != 'GET':
    log_path = os.environ['GH_STUB_CALLS']
    calls = json.loads(open(log_path).read()) if os.path.exists(log_path) else []
    calls.append([method, endpoint, fields])
    open(log_path, 'w').write(json.dumps(calls))
    if len(calls) in fixture.get('fail_writes', []):
        print('simulated write failure', file=sys.stderr)
        sys.exit(1)
if endpoint == base + 'pulls/42':
    if fixture['pr'] is None:
        print(json.dumps({'message': 'Not Found', 'status': '404'}))
        print('gh: Not Found (HTTP 404)', file=sys.stderr)
        sys.exit(1)
    print(json.dumps(fixture['pr']))
elif endpoint == base + 'pulls/42/reviews':
    print(json.dumps(fixture['reviews']))
elif endpoint == base + 'commits/' + fixture['pr']['head']['sha'] + '/check-runs':
    runs = fixture['check_runs']
    print(json.dumps({'total_count': len(runs), 'check_runs': runs}))
elif endpoint == base + 'issues/42/assignees' and method in ('POST', 'DELETE'):
    print(json.dumps({'number': 42}))
elif endpoint == base + 'issues/42/comments' and method == 'POST':
    print(json.dumps({'html_url': fixture['posted_url']}))
else:
    print('unexpected endpoint ' + method + ' ' + str(endpoint), file=sys.stderr)
    sys.exit(1)
"""


def pull_request(*, state: str = 'open', assignees: tuple[str, ...] = ()) -> dict[str, Any]:
    """Build a pull request as the pulls endpoint returns it."""
    return {
        'state': state,
        'head': {'sha': HEAD_SHA},
        'user': {'login': AUTHOR},
        'assignees': [{'login': login} for login in assignees],
    }


def make_fixture(**overrides: Any) -> dict[str, Any]:
    """Build an open, unassigned pull request with no reviews and no check runs."""
    fixture: dict[str, Any] = {
        'pr': pull_request(),
        'reviews': [],
        'check_runs': [],
        'posted_url': POSTED_URL,
    }
    fixture.update(overrides)
    return fixture


def review(login: str, commit_id: str, state: str = 'APPROVED') -> dict[str, Any]:
    """Build a pull request review as the reviews endpoint returns it."""
    return {'user': {'login': login}, 'commit_id': commit_id, 'state': state}


def check_run(status: str, conclusion: str | None = None, name: str = RESPONDER) -> dict[str, Any]:
    """Build a check run on the head commit as the check-runs endpoint returns it."""
    return {'name': name, 'status': status, 'conclusion': conclusion, 'html_url': CHECK_URL}


def install_stub_path(path: Path, *, with_gh: bool = True) -> Path:
    """Create a PATH directory holding only the commands the script needs."""
    stub_directory = path / 'stub-bin'
    stub_directory.mkdir(parents=True, exist_ok=True)
    for command in ('cat', 'dirname', 'python3'):
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
) -> tuple[subprocess.CompletedProcess[str], list[list[Any]]]:
    """Run the trigger script against `fixture`; return it and every write call it made."""
    fixture_file = work_path / 'fixture.json'
    fixture_file.write_text(json.dumps(fixture))
    calls_file = work_path / 'calls.json'
    environment = dict(os.environ)
    environment['PATH'] = str(install_stub_path(work_path, with_gh=with_gh))
    environment['GH_STUB_FIXTURE'] = str(fixture_file)
    environment['GH_STUB_CALLS'] = str(calls_file)
    completed = subprocess.run(
        [str(plugin_root / SCRIPT_PATH), *arguments],
        cwd=work_path,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    calls = json.loads(calls_file.read_text()) if calls_file.exists() else []
    return completed, calls


def outcome(completed: subprocess.CompletedProcess[str]) -> tuple[int, str]:
    """Return the exit code and the last stdout line."""
    return completed.returncode, completed.stdout.splitlines()[-1]


def toggle_calls(calls: list[list[Any]]) -> list[tuple[str, str]]:
    """Return the method and assignee of each assignees call, in order."""
    return [
        (method, fields['assignees[]'])
        for method, endpoint, fields in calls
        if endpoint.endswith('/issues/42/assignees')
    ]


def comment_bodies(calls: list[list[Any]]) -> list[str]:
    """Return the body of every comment the script posted."""
    return [fields['body'] for _, endpoint, fields in calls if endpoint.endswith('/comments')]


def test_unassigned_author_is_added_then_removed(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """Adding fires the review; removing restores the assignees the script found."""
    # Arrange
    fixture = make_fixture()

    # Act
    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert toggle_calls(calls) == [('POST', AUTHOR), ('DELETE', AUTHOR)]
    assert comment_bodies(calls) == []
    lines = completed.stdout.splitlines()
    assert f'PR_NUMBER={PR_NUMBER}' in lines
    assert f'HEAD_SHA={HEAD_SHA}' in lines
    assert 'CHECK_URL=' in lines
    assert 'COMMENT_URL=' in lines


def test_assigned_author_is_removed_then_added_back(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """An assigned author is removed first, so adding them back fires the event."""
    fixture = make_fixture(pr=pull_request(assignees=('someone', AUTHOR)))

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert toggle_calls(calls) == [('DELETE', AUTHOR), ('POST', AUTHOR)]


def test_rationale_is_posted_as_plain_comment(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """The rationale names the head and opens with no mention the bridge would act on."""
    completed, calls = run_script(
        plugin_root, plugin_tmp_path, make_fixture(), '--pr', PR_NUMBER, '--rationale', RATIONALE
    )

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert comment_bodies(calls) == [f'AI review requested for {HEAD_SHA}: {RATIONALE}']
    assert f'COMMENT_URL={POSTED_URL}' in completed.stdout.splitlines()
    assert toggle_calls(calls) == [('POST', AUTHOR), ('DELETE', AUTHOR)]


def test_no_review_trigger_comment_on_any_path(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """No path posts an `@claude` comment; the bridge rejects `@claude review`."""
    cases = [
        make_fixture(),
        make_fixture(pr=pull_request(assignees=(AUTHOR,))),
        make_fixture(reviews=[review('claude[bot]', HEAD_SHA)]),
        make_fixture(check_runs=[check_run('in_progress')]),
    ]
    for index, fixture in enumerate(cases):
        work_path = plugin_tmp_path / f'case-{index}'
        work_path.mkdir()
        _, calls = run_script(
            plugin_root, work_path, fixture, '--pr', PR_NUMBER, '--rationale', RATIONALE
        )
        assert not any(body.lower().startswith('@claude') for body in comment_bodies(calls))


@pytest.mark.parametrize('login', ['claude[bot]', 'github-actions[bot]'])
def test_accepted_review_on_head_toggles_nothing(
    plugin_root: Path, plugin_tmp_path: Path, login: str
) -> None:
    """An accepted reviewer's review of the head means no request is needed."""
    fixture = make_fixture(reviews=[review(login, HEAD_SHA, 'COMMENTED')])

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (3, 'RESULT=ALREADY_REVIEWED')
    assert calls == []


def test_accepted_review_on_older_commit_still_toggles(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A review of an earlier head does not cover the current one."""
    fixture = make_fixture(reviews=[review('claude[bot]', OLD_SHA)])

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert toggle_calls(calls)


@pytest.mark.parametrize('login', ['octocat', 'chatgpt-codex-connector[bot]'])
def test_review_by_unaccepted_author_on_head_still_toggles(
    plugin_root: Path, plugin_tmp_path: Path, login: str
) -> None:
    """A human or a bot other than Claude reviewing the head is not an accepted AI review."""
    fixture = make_fixture(reviews=[review(login, HEAD_SHA)])

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert toggle_calls(calls)


@pytest.mark.parametrize(
    ('status', 'conclusion'),
    [('queued', None), ('in_progress', None), ('completed', 'success'), ('completed', 'failure')],
)
def test_responder_check_on_head_counts_as_request(
    plugin_root: Path, plugin_tmp_path: Path, status: str, conclusion: str | None
) -> None:
    """A responder run on the head, running or finished, is the head's request."""
    fixture = make_fixture(check_runs=[check_run(status, conclusion)])

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (4, 'RESULT=ALREADY_REQUESTED')
    assert f'CHECK_URL={CHECK_URL}' in completed.stdout.splitlines()
    assert calls == []


@pytest.mark.parametrize('conclusion', ['skipped', 'cancelled'])
def test_skipped_or_cancelled_responder_still_toggles(
    plugin_root: Path, plugin_tmp_path: Path, conclusion: str
) -> None:
    """A skipped responder is the gate-only run of a push; doubt resolves toward requesting."""
    fixture = make_fixture(check_runs=[check_run('completed', conclusion)])

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert toggle_calls(calls)


def test_other_check_on_head_still_toggles(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """Only the responder check shows that a review was requested."""
    fixture = make_fixture(check_runs=[check_run('in_progress', name='ai-review-present')])

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert toggle_calls(calls)


def test_closed_pull_request_is_not_open(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A closed or merged pull request gets no request."""
    fixture = make_fixture(pr=pull_request(state='closed'))

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (5, 'RESULT=PR_NOT_OPEN')
    assert calls == []


def test_missing_pull_request_is_not_open(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A pull request the API cannot find is reported like a closed one."""
    fixture = make_fixture(pr=None)

    completed, _ = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (5, 'RESULT=PR_NOT_OPEN')


def test_failing_gh_call_is_gh_unavailable(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A gh call that fails for any other reason routes to the fallback code."""
    fixture = make_fixture(fail=True)

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (6, 'RESULT=GH_UNAVAILABLE')
    assert calls == []


def test_failing_first_toggle_call_is_gh_unavailable(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A toggle that never started changes nothing and stops before the second call."""
    fixture = make_fixture(fail_writes=[1])

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (6, 'RESULT=GH_UNAVAILABLE')
    assert toggle_calls(calls) == [('POST', AUTHOR)]


@pytest.mark.parametrize(
    ('assignees', 'unrestored'),
    [((), f'{AUTHOR} is still assigned'), ((AUTHOR,), f'{AUTHOR} is no longer assigned')],
)
def test_failing_second_toggle_call_names_unrestored_assignment(
    plugin_root: Path, plugin_tmp_path: Path, assignees: tuple[str, ...], unrestored: str
) -> None:
    """A half-done toggle reports which assignment it could not restore."""
    fixture = make_fixture(pr=pull_request(assignees=assignees), fail_writes=[2])

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (6, 'RESULT=GH_UNAVAILABLE')
    assert len(toggle_calls(calls)) == 2
    assert unrestored in completed.stderr


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
    """The rationale must stay one line."""
    completed, calls = run_script(
        plugin_root, plugin_tmp_path, make_fixture(), '--pr', PR_NUMBER, '--rationale', 'one\ntwo'
    )

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert calls == []


def test_help_lists_options_keys_and_results(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """Help names every option, output key, and result."""
    completed, _ = run_script(plugin_root, plugin_tmp_path, make_fixture(), '--help')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    for word in (
        '--pr',
        '--rationale',
        '--repo',
        'CHECK_URL',
        'COMMENT_URL',
        'HEAD_SHA',
        'ALREADY_REVIEWED',
        'ALREADY_REQUESTED',
        'PR_NOT_OPEN',
        'GH_UNAVAILABLE',
        'SIGNAL_HUP',
        'SIGNAL_INT',
        'SIGNAL_TERM',
    ):
        assert word in completed.stdout


def test_result_is_last_stdout_line_on_every_path(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Every run ends stdout with exactly one RESULT line."""
    cases = [
        make_fixture(),
        make_fixture(reviews=[review('claude[bot]', HEAD_SHA)]),
        make_fixture(check_runs=[check_run('in_progress')]),
        make_fixture(pr=pull_request(state='closed')),
        make_fixture(fail=True),
        make_fixture(fail_writes=[2]),
    ]
    for index, fixture in enumerate(cases):
        work_path = plugin_tmp_path / f'case-{index}'
        work_path.mkdir()
        completed, _ = run_script(plugin_root, work_path, fixture, '--pr', PR_NUMBER)
        lines = completed.stdout.splitlines()
        assert lines[-1].startswith('RESULT=')
        assert sum(line.startswith('RESULT=') for line in lines) == 1
