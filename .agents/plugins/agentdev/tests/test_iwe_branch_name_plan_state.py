#!/usr/bin/env python3

"""Behavior tests for iwe-branch-name.py plan-state against a local bare remote."""

from __future__ import annotations

from pathlib import Path

from git_fixtures import git, outcome
from iwe_branch_fixtures import (
    commit_file,
    LIBRARY,
    plan_document,
    PLAN_KEY,
    PLAN_SLUG,
    run_script,
    Workspace,
)
import pytest


@pytest.mark.parametrize(
    ('document', 'state'),
    [
        (plan_document(stage='cancelled'), 'cancelled'),
        (plan_document(stage='done', ticks=(True, True)), 'done'),
        (plan_document(ticks=(True, True)), 'complete'),
        (plan_document(ticks=(True, False)), 'incomplete'),
        (plan_document(ticks=(True, True), heading='Tasks'), 'complete'),
        (plan_document(ticks=(True, False), heading='Tasks'), 'incomplete'),
        (plan_document(ticks=()), 'incomplete'),
        (plan_document(ticks=(True,), heading='Steps'), 'incomplete'),
    ],
)
def test_plan_state_classifies_the_plan(
    plugin_root: Path, plugin_tmp_path: Path, document: str, state: str
) -> None:
    """Stage wins; without one, every task checkbox ticked is complete."""
    workspace = Workspace(plugin_tmp_path, {PLAN_KEY: document})

    completed, values = run_script(plugin_root, workspace.work, 'plan-state', PLAN_SLUG)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert values == {
        'DEFAULT_BRANCH': 'main',
        'PLAN_KEY': PLAN_KEY,
        'PLAN_STATE': state,
        'RESULT': 'SUCCESS',
    }


def test_plan_state_reports_a_missing_plan(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A slug no plan carries is missing, with no key."""
    workspace = Workspace(plugin_tmp_path)

    completed, values = run_script(plugin_root, workspace.work, 'plan-state', 'no-such-plan')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert values['PLAN_STATE'] == 'missing'
    assert 'PLAN_KEY' not in values


def test_plan_state_ignores_the_working_tree(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A plan finished only locally, in the tree or in an unpushed commit, stays incomplete."""
    workspace = Workspace(plugin_tmp_path)
    finished = plan_document(ticks=(True, True))
    commit_file(workspace.work, f'{LIBRARY}/{PLAN_KEY}.md', finished)
    (workspace.work / LIBRARY / 'data/plans/20250103-other.md').write_text(finished)

    completed, values = run_script(plugin_root, workspace.work, 'plan-state', PLAN_SLUG)
    _, other = run_script(plugin_root, workspace.work, 'plan-state', 'other')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert values['PLAN_STATE'] == 'incomplete'
    assert other['PLAN_STATE'] == 'missing'


def test_plan_state_fetches_the_remote(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A plan finished on the remote since the last fetch reads as complete."""
    workspace = Workspace(plugin_tmp_path)
    workspace.publish(PLAN_KEY, plan_document(ticks=(True, True)))

    _, values = run_script(plugin_root, workspace.work, 'plan-state', PLAN_SLUG)

    assert values['PLAN_STATE'] == 'complete'


@pytest.mark.parametrize('target', [PLAN_KEY, f'{PLAN_KEY}.md', '20250102-focus-timer', PLAN_SLUG])
def test_plan_state_resolves_a_key_or_a_slug(
    plugin_root: Path, plugin_tmp_path: Path, target: str
) -> None:
    """The plan key, its file name, its dated name, and its bare slug name one plan."""
    workspace = Workspace(plugin_tmp_path)

    completed, values = run_script(plugin_root, workspace.work, 'plan-state', target)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert values['PLAN_KEY'] == PLAN_KEY


def test_plan_state_refuses_a_shared_slug(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A slug two dated plans share is ambiguous; either full key still resolves."""
    later = 'data/plans/20250220-focus-timer'
    workspace = Workspace(plugin_tmp_path, {PLAN_KEY: plan_document(), later: plan_document()})

    completed, values = run_script(plugin_root, workspace.work, 'plan-state', PLAN_SLUG)
    _, by_key = run_script(plugin_root, workspace.work, 'plan-state', later)

    assert outcome(completed) == (4, 'RESULT=AMBIGUOUS_PLAN')
    assert 'PLAN_STATE' not in values
    assert by_key['PLAN_KEY'] == later


def test_plan_state_reports_an_unreachable_remote(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A remote that cannot be fetched is FETCH_FAILED, not a stale answer."""
    workspace = Workspace(plugin_tmp_path)
    git(workspace.work, 'remote', 'set-url', 'origin', str(plugin_tmp_path / 'gone.git'))

    completed, values = run_script(plugin_root, workspace.work, 'plan-state', PLAN_SLUG)

    assert outcome(completed) == (5, 'RESULT=FETCH_FAILED')
    assert 'PLAN_STATE' not in values


def test_plan_state_needs_an_iwe_workspace(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A repository without .iwe/config.toml is a preflight error."""
    workspace = Workspace(plugin_tmp_path)
    git(workspace.work, 'rm', '--quiet', '.iwe/config.toml')

    completed, _ = run_script(plugin_root, workspace.work, 'plan-state', PLAN_SLUG)

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
