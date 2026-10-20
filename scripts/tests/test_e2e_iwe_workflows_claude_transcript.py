"""A Claude run completes only on a successful result event, and a failed one names why."""

import importlib.util
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).parents[2]
SUITE = REPO_ROOT / 'scripts/e2e/iwe-workflows'
sys.path.insert(0, str(SUITE))
_spec = importlib.util.spec_from_file_location(
    'e2e_iwe_workflows_harness_claude', SUITE / 'harness_claude.py'
)
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)
sys.path.remove(str(SUITE))

INIT = {'type': 'system', 'subtype': 'init'}
SUCCESS = {'type': 'result', 'subtype': 'success', 'is_error': False, 'result': 'Shipped.'}
API_ERROR = {
    'type': 'result',
    'subtype': 'success',
    'is_error': True,
    'result': 'API Error: 401 authentication_error',
}
MAX_TURNS = {
    'type': 'result',
    'subtype': 'error_max_turns',
    'is_error': True,
    'errors': ['Reached maximum number of turns (8)'],
}


def transcript(*events: dict, timed_out: bool = False, returncode: int | None = 0):
    """Build a transcript from made-up stream-json events."""
    return harness.ClaudeTranscript(Path('ship.jsonl'), list(events), timed_out, returncode)


def test_a_successful_result_completes():
    """A success result with no error is a completed run."""
    assert transcript(INIT, SUCCESS).completed()


@pytest.mark.parametrize(
    ('events', 'timed_out', 'returncode', 'reason'),
    [
        ((INIT, API_ERROR), False, 1, 'API Error: 401 authentication_error'),
        ((INIT, MAX_TURNS), False, 1, 'error_max_turns: Reached maximum number of turns (8)'),
        ((INIT,), True, -9, 'still running after 420s, killed'),
        ((INIT,), False, 1, 'no result event (claude exited 1)'),
    ],
    ids=['is-error', 'error-subtype', 'timed-out', 'no-result'],
)
def test_failure_names_its_reason(events, timed_out, returncode, reason):
    """An error result is not completion, and its own text explains the failure."""
    run = transcript(*events, timed_out=timed_out, returncode=returncode)
    assert not run.completed()
    assert reason in run.failure_reason(420)
