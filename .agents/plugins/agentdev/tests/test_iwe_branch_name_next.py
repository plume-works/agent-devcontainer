#!/usr/bin/env python3

"""Behavior tests for iwe-branch-name.py next against a local remote and a gh stub."""

from __future__ import annotations

from pathlib import Path

from git_fixtures import git, outcome, stub_gh
from iwe_branch_fixtures import (
    plan_document,
    PLAN_KEY,
    PLAN_SLUG,
    run_script,
    tools_without_gh,
    Workspace,
)
import pytest


def pr_heads(directory: Path, *heads: str) -> Path:
    """Install a gh stub whose pull-request query answers with `heads`."""
    lines = ''.join(f'{head}\n' for head in heads)
    return stub_gh(directory, f"printf '%s' '{lines}'")


def test_next_starts_at_iteration_one(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """With no branch or pull request of the phase, the first iteration is 1."""
    workspace = Workspace(plugin_tmp_path)
    gh = pr_heads(plugin_tmp_path / 'gh')

    completed, values = run_script(
        plugin_root, workspace.work, 'next', PLAN_KEY, '--phase', 'impl', path_prefix=gh
    )

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert (values['NEXT'], values['NEXT_KIND'], values['ITERATION']) == (
        f'impl/{PLAN_SLUG}/iteration-1',
        'impl',
        '1',
    )
    recorded = (gh / 'gh-args').read_text().splitlines()
    assert recorded[:5] == ['pr', 'list', '--state', 'all', '--search']
    assert recorded[5] == f'head:impl/{PLAN_SLUG}/'


def test_next_follows_every_used_iteration(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """The highest of a local, a remote-only, and a PR-only iteration plus one."""
    workspace = Workspace(plugin_tmp_path)
    git(workspace.work, 'branch', f'impl/{PLAN_SLUG}/iteration-1')
    workspace.push_branch(f'impl/{PLAN_SLUG}/iteration-2')
    gh = pr_heads(plugin_tmp_path / 'gh', f'impl/{PLAN_SLUG}/iteration-4')

    _, values = run_script(
        plugin_root, workspace.work, 'next', PLAN_SLUG, '--phase', 'impl', path_prefix=gh
    )

    assert values['NEXT'] == f'impl/{PLAN_SLUG}/iteration-5'


@pytest.mark.parametrize('source', ['local', 'remote', 'pr'])
def test_next_counts_each_source(plugin_root: Path, plugin_tmp_path: Path, source: str) -> None:
    """A merged iteration whose branch was deleted still counts, as do local and remote ones."""
    workspace = Workspace(plugin_tmp_path)
    used = f'impl/{PLAN_SLUG}/iteration-3'
    heads: tuple[str, ...] = ()
    if source == 'local':
        git(workspace.work, 'branch', used)
    elif source == 'remote':
        workspace.push_branch(used)
    else:
        heads = (used,)
    gh = pr_heads(plugin_tmp_path / 'gh', *heads)

    _, values = run_script(
        plugin_root, workspace.work, 'next', PLAN_SLUG, '--phase', 'impl', path_prefix=gh
    )

    assert values['NEXT'] == f'impl/{PLAN_SLUG}/iteration-4'


def test_next_ignores_names_off_the_shape_and_the_other_phase(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Only exact <phase>/<slug>/iteration-<N> names of the asked phase and slug count."""
    workspace = Workspace(plugin_tmp_path)
    git(workspace.work, 'branch', f'ship/{PLAN_SLUG}/iteration-7')
    git(workspace.work, 'branch', PLAN_SLUG)
    git(workspace.work, 'branch', f'impl/{PLAN_SLUG}-v2/iteration-9')
    gh = pr_heads(
        plugin_tmp_path / 'gh',
        f'impl/{PLAN_SLUG}/iteration-8-retry',
        f'impl/{PLAN_SLUG}/iteration-0',
        f'impl-{PLAN_SLUG}-iter2',
    )

    _, values = run_script(
        plugin_root, workspace.work, 'next', PLAN_SLUG, '--phase', 'impl', path_prefix=gh
    )

    assert values['NEXT'] == f'impl/{PLAN_SLUG}/iteration-1'


def test_next_with_phase_does_not_need_the_plan(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A plan written only locally is missing on the remote, yet --phase still names it."""
    workspace = Workspace(plugin_tmp_path, plans={})
    gh = pr_heads(plugin_tmp_path / 'gh')

    completed, values = run_script(
        plugin_root, workspace.work, 'next', PLAN_KEY, '--phase', 'impl', path_prefix=gh
    )

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert values['NEXT'] == f'impl/{PLAN_SLUG}/iteration-1'
    assert 'PLAN_STATE' not in values


@pytest.mark.parametrize(
    ('plans', 'state', 'next_name', 'kind'),
    [
        ({PLAN_KEY: plan_document(stage='done', ticks=(True,))}, 'done', 'main', 'default'),
        ({PLAN_KEY: plan_document(stage='cancelled')}, 'cancelled', 'main', 'default'),
        ({}, 'missing', 'main', 'default'),
        (
            {PLAN_KEY: plan_document(ticks=(True, True))},
            'complete',
            f'ship/{PLAN_SLUG}/iteration-2',
            'ship',
        ),
        (
            {PLAN_KEY: plan_document(ticks=(True, False))},
            'incomplete',
            f'impl/{PLAN_SLUG}/iteration-1',
            'impl',
        ),
    ],
)
def test_next_follows_the_plan_state(
    plugin_root: Path,
    plugin_tmp_path: Path,
    plans: dict[str, str],
    state: str,
    next_name: str,
    kind: str,
) -> None:
    """Without --phase, each plan state maps to its NEXT_KIND."""
    workspace = Workspace(plugin_tmp_path, plans)
    gh = pr_heads(plugin_tmp_path / 'gh', f'ship/{PLAN_SLUG}/iteration-1')

    completed, values = run_script(plugin_root, workspace.work, 'next', PLAN_SLUG, path_prefix=gh)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert (values['PLAN_STATE'], values['NEXT'], values['NEXT_KIND']) == (
        state,
        next_name,
        kind,
    )
    assert ('ITERATION' in values) == (kind != 'default')


def test_next_without_gh_gives_no_name(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A missing gh cannot rule out a merged iteration, so no name is reported."""
    workspace = Workspace(plugin_tmp_path)
    tools = tools_without_gh(plugin_tmp_path / 'tools')

    completed, values = run_script(
        plugin_root, workspace.work, 'next', PLAN_SLUG, '--phase', 'impl', path=tools
    )

    assert outcome(completed) == (6, 'RESULT=GH_UNAVAILABLE')
    assert 'NEXT' not in values


def test_next_with_unauthenticated_gh_gives_no_name(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A gh that cannot list pull requests is GH_UNAVAILABLE, not a lower bound."""
    workspace = Workspace(plugin_tmp_path)
    gh = stub_gh(
        plugin_tmp_path / 'gh',
        "echo 'To get started with GitHub CLI, please run:  gh auth login' >&2\nexit 4",
    )

    completed, values = run_script(
        plugin_root, workspace.work, 'next', PLAN_SLUG, '--phase', 'impl', path_prefix=gh
    )

    assert outcome(completed) == (6, 'RESULT=GH_UNAVAILABLE')
    assert 'NEXT' not in values


def test_next_reports_an_unlistable_remote(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A remote whose branches cannot be listed is FETCH_FAILED."""
    workspace = Workspace(plugin_tmp_path)
    git(workspace.work, 'remote', 'set-url', 'origin', str(plugin_tmp_path / 'gone.git'))
    gh = pr_heads(plugin_tmp_path / 'gh')

    completed, _ = run_script(
        plugin_root, workspace.work, 'next', PLAN_SLUG, '--phase', 'impl', path_prefix=gh
    )

    assert outcome(completed) == (5, 'RESULT=FETCH_FAILED')


def test_next_rejects_an_unknown_phase(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """--phase takes only impl or ship."""
    workspace = Workspace(plugin_tmp_path)

    completed, _ = run_script(plugin_root, workspace.work, 'next', PLAN_SLUG, '--phase', 'review')

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
