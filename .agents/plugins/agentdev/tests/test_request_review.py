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
AI_REVIEWER = 'plume-works-quill[bot]'
CHECK_URL = 'https://github.com/octo/repo/runs/700'
POSTED_URL = 'https://github.com/octo/repo/pull/42#issuecomment-900'
REQUEST_LABEL = 'request-ai-review'
BLOCK_LABEL = 'block-ai-reviews'
HEAD_REF = 'feature/retry'
RATIONALE = 'Reworked the retry backoff beyond the thread.'
EARLIER = '2026-01-01T09:00:00Z'
STARTED_AT = '2026-01-01T09:30:00Z'
REVIEWED_AT = '2026-01-01T10:00:00Z'
LATER = '2026-01-01T11:00:00Z'

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
    if argument in ('-f', '--raw-field', '-F', '--field'):
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
if endpoint == 'graphql':
    open(os.environ['GH_STUB_GRAPHQL'], 'w').write(json.dumps(arguments))
    if fixture.get('fail_graphql'):
        print('simulated graphql failure', file=sys.stderr)
        sys.exit(1)
    edits = fixture.get('edits', {})
    renames = [{'createdAt': edits['title']}] if edits.get('title') else []
    pull = {'lastEditedAt': edits.get('body'), 'timelineItems': {'nodes': renames}}
    print(json.dumps({'data': {'repository': {'pullRequest': pull}}}))
    sys.exit(0)
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
elif endpoint == base + 'issues/42/labels' and method == 'POST':
    print(json.dumps([{'name': fields.get('labels[]')}]))
elif endpoint == base + 'issues/42/labels/request-ai-review' and method == 'DELETE':
    print(json.dumps([]))
elif endpoint == base + 'actions/workflows/ai-responder.yml/runs' and method == 'GET':
    if fields.get('branch') != fixture['pr']['head']['ref']:
        sys.exit(1)
    print(json.dumps({'workflow_runs': fixture.get('workflow_runs', [])}))
elif endpoint == base + 'issues/42/comments' and method == 'POST':
    print(json.dumps({'html_url': fixture['posted_url']}))
else:
    print('unexpected endpoint ' + method + ' ' + str(endpoint), file=sys.stderr)
    sys.exit(1)
"""


def pull_request(
    *, state: str = 'open', assignees: tuple[str, ...] = (), labels: tuple[str, ...] = ()
) -> dict[str, Any]:
    """Build a pull request as the pulls endpoint returns it."""
    return {
        'state': state,
        'head': {'sha': HEAD_SHA, 'ref': HEAD_REF},
        'user': {'login': AUTHOR},
        'assignees': [{'login': login} for login in assignees],
        'labels': [{'name': name} for name in labels],
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


def review(
    login: str, commit_id: str, state: str = 'APPROVED', submitted_at: str = REVIEWED_AT
) -> dict[str, Any]:
    """Build a pull request review as the reviews endpoint returns it."""
    return {
        'user': {'login': login},
        'commit_id': commit_id,
        'state': state,
        'submitted_at': submitted_at,
    }


def check_run(
    status: str,
    conclusion: str | None = None,
    name: str = RESPONDER,
    completed_at: str = REVIEWED_AT,
    started_at: str = STARTED_AT,
) -> dict[str, Any]:
    """Build a check run on the head commit as the check-runs endpoint returns it."""
    return {
        'name': name,
        'status': status,
        'conclusion': conclusion,
        'html_url': CHECK_URL,
        'started_at': started_at if status != 'queued' else None,
        'completed_at': completed_at if status == 'completed' else None,
    }


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
    environment['GH_STUB_GRAPHQL'] = str(work_path / 'graphql.json')
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


def request_calls(calls: list[list[Any]]) -> list[str]:
    """Return each label the script added, in order."""
    return [
        fields['labels[]']
        for _, endpoint, fields in calls
        if endpoint.endswith('/issues/42/labels')
    ]


def label_removals(calls: list[list[Any]]) -> list[str]:
    """Return the endpoint of each label the script removed, in order."""
    return [
        endpoint for method, endpoint, _ in calls if method == 'DELETE' and '/labels/' in endpoint
    ]


def assignee_calls(calls: list[list[Any]]) -> list[list[Any]]:
    """Return every call that touched the pull request's assignees."""
    return [call for call in calls if 'assignees' in call[1]]


def comment_bodies(calls: list[list[Any]]) -> list[str]:
    """Return the body of every comment the script posted."""
    return [fields['body'] for _, endpoint, fields in calls if endpoint.endswith('/comments')]


def test_request_adds_the_label(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """Adding the request label is the whole request."""
    # Arrange
    fixture = make_fixture()

    # Act
    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert request_calls(calls) == [REQUEST_LABEL]
    assert comment_bodies(calls) == []
    lines = completed.stdout.splitlines()
    assert f'PR_NUMBER={PR_NUMBER}' in lines
    assert f'HEAD_SHA={HEAD_SHA}' in lines
    assert 'CHECK_URL=' in lines
    assert 'COMMENT_URL=' in lines


def test_assignees_are_never_touched(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """An assignment no longer requests a review, so the script leaves assignees alone."""
    fixture = make_fixture(pr=pull_request(assignees=('someone', AUTHOR)))

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert request_calls(calls) == [REQUEST_LABEL]
    assert assignee_calls(calls) == []


def test_blocked_pull_request_queues_the_request(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A blocked pull request gets the request label so it waits visibly, and reports BLOCKED."""
    fixture = make_fixture(pr=pull_request(labels=(BLOCK_LABEL,)))

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (7, 'RESULT=BLOCKED')
    assert request_calls(calls) == [REQUEST_LABEL]


def test_blocked_pull_request_with_waiting_request_adds_nothing(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A request already waiting on a blocked pull request is left as it is."""
    fixture = make_fixture(pr=pull_request(labels=(BLOCK_LABEL, REQUEST_LABEL)))

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (7, 'RESULT=BLOCKED')
    assert calls == []


def test_blocked_pull_request_already_reviewed_queues_nothing(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A blocked pull request whose head is already reviewed gets no label to run on unblock."""
    fixture = make_fixture(
        pr=pull_request(labels=(BLOCK_LABEL,)),
        reviews=[review(AI_REVIEWER, HEAD_SHA, 'COMMENTED')],
    )

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (3, 'RESULT=ALREADY_REVIEWED')
    assert calls == []


def test_label_waiting_for_a_run_is_already_requested(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """An unfinished run in the pull request's group will take the label, so nothing is sent."""
    fixture = make_fixture(
        pr=pull_request(labels=('bug', REQUEST_LABEL)),
        workflow_runs=[{'status': 'completed'}, {'status': 'pending'}],
    )

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (4, 'RESULT=ALREADY_REQUESTED')
    assert calls == []


def test_stale_label_is_removed_and_added_again(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A label no unfinished run will take is re-sent, which fires a new labeled event."""
    fixture = make_fixture(
        pr=pull_request(labels=(REQUEST_LABEL,)), workflow_runs=[{'status': 'completed'}]
    )

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert label_removals(calls) == [f'repos/octo/repo/issues/42/labels/{REQUEST_LABEL}']
    assert request_calls(calls) == [REQUEST_LABEL]
    assert [call[0] for call in calls] == ['DELETE', 'POST']


def test_failing_stale_label_removal_is_gh_unavailable(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A stale label that could not be removed is reported, and nothing is added."""
    fixture = make_fixture(pr=pull_request(labels=(REQUEST_LABEL,)), fail_writes=[1])

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (6, 'RESULT=GH_UNAVAILABLE')
    assert request_calls(calls) == []


def test_rationale_is_posted_as_plain_comment(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """The rationale names the head and opens with no mention the bridge would act on."""
    completed, calls = run_script(
        plugin_root, plugin_tmp_path, make_fixture(), '--pr', PR_NUMBER, '--rationale', RATIONALE
    )

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert comment_bodies(calls) == [f'AI review requested for {HEAD_SHA}: {RATIONALE}']
    assert f'COMMENT_URL={POSTED_URL}' in completed.stdout.splitlines()
    assert request_calls(calls) == [REQUEST_LABEL]


def test_no_review_trigger_comment_on_any_path(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """No path posts an `@claude` comment; no comment starts the responder."""
    cases = [
        make_fixture(),
        make_fixture(pr=pull_request(assignees=(AUTHOR,))),
        make_fixture(reviews=[review(AI_REVIEWER, HEAD_SHA)]),
        make_fixture(check_runs=[check_run('in_progress')]),
    ]
    for index, fixture in enumerate(cases):
        work_path = plugin_tmp_path / f'case-{index}'
        work_path.mkdir()
        _, calls = run_script(
            plugin_root, work_path, fixture, '--pr', PR_NUMBER, '--rationale', RATIONALE
        )
        assert not any(body.lower().startswith('@claude') for body in comment_bodies(calls))


def test_accepted_review_on_head_requests_nothing(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """The AI reviewer's review of the head means no request is needed."""
    fixture = make_fixture(reviews=[review(AI_REVIEWER, HEAD_SHA, 'COMMENTED')])

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (3, 'RESULT=ALREADY_REVIEWED')
    assert calls == []


def test_accepted_review_on_older_commit_still_requests(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A review of an earlier head does not cover the current one."""
    fixture = make_fixture(reviews=[review(AI_REVIEWER, OLD_SHA)])

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert request_calls(calls)


@pytest.mark.parametrize(
    'login', ['octocat', 'chatgpt-codex-connector[bot]', 'claude[bot]', 'github-actions[bot]']
)
def test_review_by_unaccepted_author_on_head_still_requests(
    plugin_root: Path, plugin_tmp_path: Path, login: str
) -> None:
    """A review of the head by anyone but the AI reviewer is not an accepted AI review."""
    fixture = make_fixture(reviews=[review(login, HEAD_SHA)])

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert request_calls(calls)


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
def test_skipped_or_cancelled_responder_still_requests(
    plugin_root: Path, plugin_tmp_path: Path, conclusion: str
) -> None:
    """A skipped responder is the gate-only run of a push; doubt resolves toward requesting."""
    fixture = make_fixture(check_runs=[check_run('completed', conclusion)])

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert request_calls(calls)


@pytest.mark.parametrize('edited', ['body', 'title'])
def test_review_on_head_before_metadata_edit_still_requests(
    plugin_root: Path, plugin_tmp_path: Path, edited: str
) -> None:
    """A review that saw an older title or description does not cover the head's input."""
    fixture = make_fixture(
        reviews=[review(AI_REVIEWER, HEAD_SHA, 'CHANGES_REQUESTED')], edits={edited: LATER}
    )

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert request_calls(calls)


def test_review_on_head_after_metadata_edit_requests_nothing(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A review submitted after the latest edit saw the current title and description."""
    fixture = make_fixture(
        reviews=[review(AI_REVIEWER, HEAD_SHA)], edits={'body': EARLIER, 'title': EARLIER}
    )

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (3, 'RESULT=ALREADY_REVIEWED')
    assert calls == []


def test_responder_check_completed_before_metadata_edit_still_requests(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """The metadata gate's own finished run does not count as a request for the edited input."""
    fixture = make_fixture(
        reviews=[review(AI_REVIEWER, HEAD_SHA, 'CHANGES_REQUESTED')],
        check_runs=[check_run('completed', 'success')],
        edits={'body': LATER},
    )

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert request_calls(calls)


@pytest.mark.parametrize('status', ['queued', 'in_progress'])
def test_running_responder_check_counts_despite_metadata_edit(
    plugin_root: Path, plugin_tmp_path: Path, status: str
) -> None:
    """A review still running covers the head whenever it started."""
    fixture = make_fixture(check_runs=[check_run(status)], edits={'body': LATER})

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (4, 'RESULT=ALREADY_REQUESTED')
    assert calls == []


def test_responder_check_completed_after_metadata_edit_counts(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A run that finished after the latest edit already answered the head's current input."""
    fixture = make_fixture(check_runs=[check_run('completed', 'failure')], edits={'body': EARLIER})

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (4, 'RESULT=ALREADY_REQUESTED')
    assert calls == []


@pytest.mark.parametrize(
    ('started_at', 'expected'),
    [
        ('2026-01-01T10:30:00Z', (0, 'RESULT=SUCCESS')),
        ('2026-01-01T11:10:00Z', (3, 'RESULT=ALREADY_REVIEWED')),
    ],
)
def test_review_from_a_run_started_before_the_edit_does_not_count(
    plugin_root: Path, plugin_tmp_path: Path, started_at: str, expected: tuple[int, str]
) -> None:
    """A run reads the title and description when it starts, whenever it finishes."""
    fixture = make_fixture(
        reviews=[review(AI_REVIEWER, HEAD_SHA, submitted_at='2026-01-01T11:20:00Z')],
        check_runs=[
            check_run(
                'completed', 'success', started_at=started_at, completed_at='2026-01-01T11:30:00Z'
            )
        ],
        edits={'body': LATER},
    )

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == expected
    assert bool(request_calls(calls)) == (expected[0] == 0)


def test_edit_time_query_sends_owner_and_name_as_strings(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A typed field would turn an all-digit owner or repository name into a number."""
    run_script(plugin_root, plugin_tmp_path, make_fixture(), '--pr', PR_NUMBER)

    arguments = json.loads((plugin_tmp_path / 'graphql.json').read_text())
    flags = {value.split('=', 1)[0]: arguments[index - 1] for index, value in enumerate(arguments)}
    assert (flags['owner'], flags['name'], flags['number']) == ('-f', '-f', '-F')


def test_failing_edit_time_query_is_gh_unavailable(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Without the edit times the script cannot tell what the head's review saw."""
    fixture = make_fixture(reviews=[review(AI_REVIEWER, HEAD_SHA)], fail_graphql=True)

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (6, 'RESULT=GH_UNAVAILABLE')
    assert calls == []


def test_other_check_on_head_still_requests(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """Only the responder check shows that a review was requested."""
    fixture = make_fixture(check_runs=[check_run('in_progress', name='ai-review-present')])

    completed, calls = run_script(plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert request_calls(calls)


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


def test_failing_label_call_is_gh_unavailable(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A label that could not be added is reported, and no rationale is posted."""
    fixture = make_fixture(fail_writes=[1])

    completed, calls = run_script(
        plugin_root, plugin_tmp_path, fixture, '--pr', PR_NUMBER, '--rationale', RATIONALE
    )

    assert outcome(completed) == (6, 'RESULT=GH_UNAVAILABLE')
    assert request_calls(calls) == [REQUEST_LABEL]
    assert comment_bodies(calls) == []


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
        'BLOCKED',
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
        make_fixture(reviews=[review(AI_REVIEWER, HEAD_SHA)]),
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
