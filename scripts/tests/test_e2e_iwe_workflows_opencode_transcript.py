"""An OpenCode run that did not complete names why, from its transcript alone."""

import importlib.util
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).parents[2]
SUITE = REPO_ROOT / 'scripts/e2e/iwe-workflows'
sys.path.insert(0, str(SUITE))
_spec = importlib.util.spec_from_file_location(
    'e2e_iwe_workflows_harness_opencode', SUITE / 'harness_opencode.py'
)
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)
sys.path.remove(str(SUITE))

USER = {'type': 'user', 'text': 'data/plans/20261008-e2e-hello'}
USAGE_LIMIT = {
    'type': 'assistant',
    'content': [],
    'error': {
        'type': 'provider.quota',
        'message': 'The ChatGPT user has reached their Subscription Sharing usage limit',
        'code': 'subscription_sharing_usage_limit_exceeded',
    },
}
AUTH = {'type': 'assistant', 'content': [], 'error': {'type': 'provider.auth'}}
ANSWER = {'type': 'assistant', 'content': [{'type': 'text', 'text': 'done'}]}


def transcript(*messages: dict, timed_out: bool = False):
    """Build a transcript from made-up messages."""
    return harness.Transcript(Path('ship.jsonl'), list(messages), timed_out=timed_out)


@pytest.mark.parametrize(
    ('messages', 'timed_out', 'reason'),
    [
        ((USER, USAGE_LIMIT), False, 'over its usage limit (usage_limit_exceeded)'),
        ((USER, AUTH), False, 'login expired (provider.auth)'),
        ((USER,), True, 'still running after 300s, interrupted'),
        ((USER,), False, 'no assistant text'),
    ],
    ids=['usage-limit', 'auth-expired', 'timed-out', 'no-text'],
)
def test_failure_names_its_reason(messages, timed_out, reason):
    """Each way a run fails to complete has its own reason."""
    run = transcript(*messages, timed_out=timed_out)
    assert not run.completed()
    assert reason in run.failure_reason(300)


def test_usage_limit_outranks_a_timeout():
    """A refused login explains a run that then sat until the deadline."""
    run = transcript(USER, USAGE_LIMIT, timed_out=True)
    assert 'usage limit' in run.failure_reason(300)


def test_a_completed_run_is_not_usage_limited():
    """An ordinary answer carries no usage-limit or login signal."""
    run = transcript(USER, ANSWER)
    assert run.completed()
    assert not run.usage_limited()
    assert not run.auth_expired()


FAILED = {
    'type': 'assistant',
    'content': [],
    'error': {'type': 'provider.unknown', 'message': 'stream closed mid-response'},
}
SUBAGENT_AUTH = {
    'type': 'assistant',
    'content': [
        {'type': 'tool', 'name': 'subagent', 'state': {'output': {'error': 'provider.auth'}}},
        {'type': 'text', 'text': 'done'},
    ],
}


@pytest.mark.parametrize(
    ('failure', 'reason'),
    [
        (USAGE_LIMIT, 'over its usage limit'),
        (AUTH, 'login expired (provider.auth)'),
        (FAILED, 'provider.unknown: stream closed mid-response'),
    ],
    ids=['usage-limit', 'auth-expired', 'other-error'],
)
def test_an_error_after_text_is_not_completion(failure, reason):
    """Earlier assistant text does not complete a session whose later message failed."""
    run = transcript(USER, ANSWER, failure)
    assert not run.completed()
    assert reason in run.failure_reason(300)


def test_a_login_failure_is_reported_even_when_the_session_completed():
    """A nested auth failure fails the run though the orchestrator answered cleanly."""
    run = transcript(USER, SUBAGENT_AUTH)
    assert run.completed()
    assert 'provider.auth' in run.failure_reason(300)


def test_a_clean_run_has_no_failure_reason():
    """A completed run in time, with no login signal, has nothing to explain."""
    assert transcript(USER, ANSWER).failure_reason(300) is None
