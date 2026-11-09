#!/usr/bin/env python3

"""Behavior tests for bin/plan_predecessors.py against a local bare remote."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

from git_fixtures import FIXTURE_ENV
from iwe_branch_fixtures import plan_document, Workspace
import pytest

PLAN = 'data/plans/20250105-session-log'
FIRST = 'data/plans/20250102-focus-timer'
SECOND = 'data/plans/20250103-break-reminder'


@pytest.fixture
def predecessors(plugin_root: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load the script as a module, with the fixture identity in the environment."""
    for key, value in FIXTURE_ENV.items():
        monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location(
        'plan_predecessors', plugin_root / 'bin/plan_predecessors.py'
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, 'plan_predecessors', module)
    spec.loader.exec_module(module)
    return module


def dependent_plan(*dependencies: str) -> str:
    """Return a made-up plan whose ``## Depends on`` links each dependency key."""
    links = ''.join(
        f'[A plan that\nwraps]({key.removeprefix("data/plans/")}.md) — supplies a part.\n\n'
        for key in dependencies
    )
    section = f'## Depends on\n\n{links}' if dependencies else ''
    return f'{plan_document()}{section}## Out of scope\n\n- [Other](../spec/other.md)\n'


def run(
    module: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    workspace: Workspace,
    pulls: list[tuple[int, str, str]],
) -> tuple[int, list[str], str]:
    """Run the script for PLAN with `pulls` as (number, head, base); return code, PRs, stderr."""
    monkeypatch.setattr(
        module,
        'open_pull_requests',
        lambda _remote_url: [module.PullRequest(*pull) for pull in pulls],
    )
    monkeypatch.chdir(workspace.work)
    monkeypatch.setattr(sys, 'argv', ['plan_predecessors.py', PLAN])
    code = module.main()
    captured = capsys.readouterr()
    found = [
        line.removeprefix('PREDECESSOR=')
        for line in captured.out.splitlines()
        if line.startswith('PREDECESSOR=')
    ]
    return code, found, captured.err


def test_a_plan_without_dependencies_has_no_predecessor(
    predecessors: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    plugin_tmp_path: Path,
) -> None:
    workspace = Workspace(plugin_tmp_path, {PLAN: dependent_plan()})

    assert run(predecessors, monkeypatch, capsys, workspace, []) == (0, [], '')


def test_a_dependency_done_at_the_remote_default_branch_is_skipped(
    predecessors: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    plugin_tmp_path: Path,
) -> None:
    workspace = Workspace(plugin_tmp_path, {FIRST: plan_document(), PLAN: dependent_plan(FIRST)})
    workspace.publish(FIRST, plan_document(stage='done', ticks=(True, True)))
    pulls = [(10, 'iwe/focus-timer/iter-1-impl', 'main')]

    assert run(predecessors, monkeypatch, capsys, workspace, pulls) == (0, [], '')


def test_an_open_dependency_yields_the_top_of_its_chain(
    predecessors: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    plugin_tmp_path: Path,
) -> None:
    workspace = Workspace(plugin_tmp_path, {FIRST: plan_document(), PLAN: dependent_plan(FIRST)})
    pulls = [
        (10, 'iwe/focus-timer/iter-1-impl', 'main'),
        (11, 'iwe/focus-timer/iter-2-impl', 'iwe/focus-timer/iter-1-impl'),
        (12, 'iwe/unrelated/iter-1-impl', 'main'),
    ]

    assert run(predecessors, monkeypatch, capsys, workspace, pulls) == (0, ['11'], '')


def test_two_dependencies_in_one_chain_yield_the_upper_one(
    predecessors: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    plugin_tmp_path: Path,
) -> None:
    plans = {FIRST: plan_document(), SECOND: plan_document(), PLAN: dependent_plan(FIRST, SECOND)}
    workspace = Workspace(plugin_tmp_path, plans)
    pulls = [
        (10, 'iwe/focus-timer/iter-1-impl', 'main'),
        (20, 'iwe/break-reminder/iter-1-impl', 'iwe/focus-timer/iter-1-impl'),
    ]

    assert run(predecessors, monkeypatch, capsys, workspace, pulls) == (0, ['20'], '')


def test_two_dependencies_in_different_chains_yield_both(
    predecessors: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    plugin_tmp_path: Path,
) -> None:
    plans = {FIRST: plan_document(), SECOND: plan_document(), PLAN: dependent_plan(FIRST, SECOND)}
    workspace = Workspace(plugin_tmp_path, plans)
    pulls = [
        (20, 'iwe/break-reminder/iter-1-impl', 'main'),
        (10, 'iwe/focus-timer/iter-1-impl', 'main'),
    ]

    assert run(predecessors, monkeypatch, capsys, workspace, pulls) == (0, ['10', '20'], '')


def test_the_plans_own_open_iteration_is_a_predecessor(
    predecessors: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    plugin_tmp_path: Path,
) -> None:
    workspace = Workspace(plugin_tmp_path, {PLAN: dependent_plan()})
    pulls = [(30, 'iwe/session-log/iter-1-impl', 'main')]

    assert run(predecessors, monkeypatch, capsys, workspace, pulls) == (0, ['30'], '')


def test_an_unshipped_dependency_without_a_pull_request_stops(
    predecessors: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    plugin_tmp_path: Path,
) -> None:
    workspace = Workspace(plugin_tmp_path, {FIRST: plan_document(), PLAN: dependent_plan(FIRST)})
    pulls = [(30, 'iwe/session-log/iter-1-impl', 'main')]

    code, found, error = run(predecessors, monkeypatch, capsys, workspace, pulls)

    assert (code, found) == (predecessors.NO_PULL_REQUEST, [])
    assert FIRST in error


def test_a_section_that_starts_with_none_names_no_dependency(
    predecessors: ModuleType,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    plugin_tmp_path: Path,
) -> None:
    related = FIRST.removeprefix('data/plans/')
    document = (
        plan_document() + f'## Depends on\n\nNone. [A related plan]({related}.md) follows.\n'
    )
    workspace = Workspace(plugin_tmp_path, {FIRST: plan_document(), PLAN: document})

    assert run(predecessors, monkeypatch, capsys, workspace, []) == (0, [], '')
