"""Tests for scripts/ci-cooldown.py with an injected clock and sleep against a stub API."""

from __future__ import annotations

from datetime import datetime, timedelta, UTC
import importlib.util
from pathlib import Path
import sys

from github_api_stub import ActionsApi, run, RUN_ID, serve
import pytest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))


def _load_script():
    """Load the hyphen-named script as a module."""
    spec = importlib.util.spec_from_file_location('ci_cooldown', SCRIPTS / 'ci-cooldown.py')
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cooldown = _load_script()
NOW = datetime(2026, 11, 4, 12, 0, tzinfo=UTC)


def at(seconds_ago: int) -> str:
    """Return the API timestamp of a run created seconds_ago before NOW."""
    return (NOW - timedelta(seconds=seconds_ago)).strftime('%Y-%m-%dT%H:%M:%SZ')


def own(seconds_ago: int = 0) -> dict:
    """Return this run, still in progress."""
    return run(int(RUN_ID), at(seconds_ago), conclusion=None)


def waited(api: ActionsApi, **variables: str) -> list[float]:
    """Run the script against api and return what it slept for."""
    slept: list[float] = []
    with serve(api):
        status = cooldown.main(
            env={**api.env(), **variables}, now=NOW.timestamp, sleep=slept.append
        )
    assert status == 0
    return slept


def test_no_earlier_run_waits_the_cooldown() -> None:
    """A run with no earlier push run waits the full default cooldown."""
    assert waited(ActionsApi(runs=[own()])) == [600]


def test_anchor_past_the_cap_starts_at_once() -> None:
    """A burst whose oldest cancelled run started beyond the cap builds without waiting."""
    api = ActionsApi(
        runs=[
            run(1, at(4000), conclusion='success'),
            run(2, at(2000), conclusion='cancelled'),
            run(3, at(1000), conclusion='cancelled'),
            own(),
        ]
    )
    assert waited(api) == [0]


def test_anchor_inside_the_cooldown_waits_the_cooldown() -> None:
    """A burst that began within the cooldown leaves the cap far off: the full cooldown."""
    api = ActionsApi(runs=[run(1, at(100), conclusion='cancelled'), own()])
    assert waited(api) == [600]


def test_walk_stops_at_the_first_run_not_cancelled() -> None:
    """The cap counts from the oldest cancelled run newer than the last one not cancelled."""
    api = ActionsApi(
        runs=[
            run(1, at(5000), conclusion='cancelled'),
            run(2, at(3000), conclusion='success'),
            run(3, at(1500), conclusion='cancelled'),
            run(4, at(400), conclusion='cancelled'),
            own(),
        ]
    )
    assert waited(api) == [300]


def test_newer_runs_are_not_walked() -> None:
    """A run queued after this one does not end the walk."""
    api = ActionsApi(
        runs=[run(1, at(1500), conclusion='cancelled'), own(60), run(901, at(0), conclusion=None)]
    )
    assert waited(api) == [300]


def test_failed_lookup_warns_and_waits_the_cooldown(capsys: pytest.CaptureFixture[str]) -> None:
    """A run history that cannot be read costs the full cooldown, with a warning."""
    assert waited(ActionsApi(fail=True), MAIN_COOLDOWN_SECONDS='120') == [120]
    assert '::warning::' in capsys.readouterr().out


def test_cooldown_of_zero_starts_at_once() -> None:
    """MAIN_COOLDOWN_SECONDS=0 turns the wait off."""
    assert waited(ActionsApi(runs=[own()]), MAIN_COOLDOWN_SECONDS='0') == [0]


def test_empty_variables_take_the_defaults() -> None:
    """An unset repository variable reaches the script empty and takes the default."""
    api = ActionsApi(runs=[run(1, at(1500), conclusion='cancelled'), own()])
    assert waited(api, MAIN_COOLDOWN_SECONDS='', MAIN_COOLDOWN_MAX_SECONDS='') == [300]


@pytest.mark.parametrize('name', ['MAIN_COOLDOWN_SECONDS', 'MAIN_COOLDOWN_MAX_SECONDS'])
@pytest.mark.parametrize('value', ['-1', 'ten'])
def test_invalid_variable_fails_naming_it(
    name: str, value: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """A negative or non-integer variable fails before waiting, naming the variable."""
    slept: list[float] = []
    api = ActionsApi(runs=[own()])
    with serve(api):
        status = cooldown.main(
            env={**api.env(), name: value}, now=NOW.timestamp, sleep=slept.append
        )
    assert status != 0
    assert slept == []
    assert name in capsys.readouterr().err
