"""Tests for scripts/ci_runs.py against a local stub of the GitHub Actions API."""

from __future__ import annotations

from pathlib import Path
import sys

from github_api_stub import ActionsApi, run, serve, WORKFLOW_ID
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import ci_runs  # noqa: E402


def test_last_success_is_the_newest_successful_push_run() -> None:
    """The head commit of the newest successful run is returned, not a newer cancelled one."""
    api = ActionsApi(
        runs=[
            run(1, '2026-11-04T09:00:00Z', conclusion='success', sha='a' * 40),
            run(2, '2026-11-04T10:00:00Z', conclusion='success', sha='b' * 40),
            run(3, '2026-11-04T11:00:00Z', conclusion='cancelled', sha='c' * 40),
        ]
    )
    with serve(api):
        assert ci_runs.last_success_sha(api.env(), 'main') == 'b' * 40
    assert any(f'workflows/{WORKFLOW_ID}/runs?' in path for path in api.requests)


def test_no_successful_run_returns_none() -> None:
    """A workflow with no successful push run on the branch has no last success."""
    api = ActionsApi(runs=[run(3, '2026-11-04T11:00:00Z', conclusion='cancelled')])
    with serve(api):
        assert ci_runs.last_success_sha(api.env(), 'main') is None


def test_failed_request_raises_the_module_error() -> None:
    """A request the API answers with an error raises CIRunsError naming the cause."""
    api = ActionsApi(fail=True)
    with serve(api), pytest.raises(ci_runs.CIRunsError, match='500'):
        ci_runs.last_success_sha(api.env(), 'main')
