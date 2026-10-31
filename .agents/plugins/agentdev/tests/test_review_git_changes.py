#!/usr/bin/env python3

"""Behavior tests for the pr-gen-description review-git-changes script."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

from git_fixtures import FIXTURE_ENV, git, outcome
import pytest
from test_update_branch import initialize_repository

SCRIPT_PATH = 'skills/pr-gen-description/agent-code/review-git-changes.py'


def run_script(plugin_root: Path, cwd: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the report script in `cwd`."""
    return subprocess.run(
        [str(plugin_root / SCRIPT_PATH), *arguments],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, **FIXTURE_ENV},
    )


@pytest.fixture
def repository(plugin_tmp_path: Path) -> Path:
    """Create a repository whose fixture-feature is one commit past a local base branch."""
    path = plugin_tmp_path / 'repository'
    initialize_repository(path)
    git(path, 'branch', 'fixture-base')
    (path / 'change.txt').write_text('branch change\n')
    git(path, 'add', 'change.txt')
    git(path, 'commit', '--quiet', '-m', 'Branch change')
    return path


def sections(completed: subprocess.CompletedProcess[str]) -> list[str]:
    """Return the section headers of the report."""
    return [line for line in completed.stdout.splitlines() if line.startswith('== ')]


def test_report_covers_the_range_from_the_merge_base(plugin_root: Path, repository: Path) -> None:
    """The default range runs from the merge base with --base-ref to HEAD."""
    merge_base = git(repository, 'merge-base', 'fixture-base', 'HEAD')

    completed = run_script(plugin_root, repository, '--base-ref', 'fixture-base')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    commit_range = f'{merge_base}..HEAD'
    assert sections(completed) == [
        '== Branch ==',
        '== Status ==',
        f'== Diff Stat ({commit_range}) ==',
        '== Working Tree Diff ==',
        f'== Commit Range Diff ({commit_range}) ==',
        f'== Commit Log ({commit_range}) ==',
    ]
    assert completed.stdout.splitlines()[1] == 'fixture-feature'
    assert '+branch change' in completed.stdout
    assert 'Branch change' in completed.stdout


def test_stat_only_skips_the_patches(plugin_root: Path, repository: Path) -> None:
    """--stat-only keeps the summary sections and drops both diffs."""
    completed = run_script(plugin_root, repository, '--range', 'fixture-base..HEAD', '--stat-only')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert sections(completed) == [
        '== Branch ==',
        '== Status ==',
        '== Diff Stat (fixture-base..HEAD) ==',
        '== Commit Log (fixture-base..HEAD) ==',
    ]
    assert '+branch change' not in completed.stdout


def test_working_tree_changes_alone_are_something_to_describe(
    plugin_root: Path, repository: Path
) -> None:
    """An empty range with an uncommitted change still succeeds."""
    (repository / 'fixture.txt').write_text('edited\n')

    completed = run_script(plugin_root, repository, '--range', 'HEAD..HEAD')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert '+edited' in completed.stdout


def test_nothing_to_describe_still_prints_the_report(plugin_root: Path, repository: Path) -> None:
    """A clean tree and an empty range report NO_CHANGES after the sections."""
    completed = run_script(plugin_root, repository, '--range', 'HEAD..HEAD', '--stat-only')

    assert outcome(completed) == (3, 'RESULT=NO_CHANGES')
    assert len(sections(completed)) == 4
    assert 'NOTE: No working tree changes and no commits detected in HEAD..HEAD.' in (
        completed.stderr
    )


@pytest.mark.parametrize(
    ('arguments', 'message'),
    [
        ([], 'Base ref not found: origin/main'),
        (
            ['--range', 'fixture-absent..HEAD'],
            'Commit range does not resolve: fixture-absent..HEAD',
        ),
        (['--base-ref'], 'Missing value for --base-ref'),
        (['--bogus'], 'Unknown argument: --bogus'),
    ],
)
def test_preflight_errors(
    plugin_root: Path, repository: Path, arguments: list[str], message: str
) -> None:
    """An unknown base ref or range and usage errors stop before any section prints."""
    completed = run_script(plugin_root, repository, *arguments)

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert f'ERROR: {message}' in completed.stderr
    assert sections(completed) == []


def test_unrelated_histories_have_no_merge_base(plugin_root: Path, repository: Path) -> None:
    """A base ref sharing no history with HEAD is a preflight error."""
    git(repository, 'checkout', '--quiet', '--orphan', 'fixture-other')
    (repository / 'other.txt').write_text('unrelated\n')
    git(repository, 'add', 'other.txt')
    git(repository, 'commit', '--quiet', '-m', 'Unrelated root')
    git(repository, 'checkout', '--quiet', '--force', 'fixture-feature')

    completed = run_script(plugin_root, repository, '--base-ref', 'fixture-other')

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert 'Could not determine merge base between fixture-other and HEAD.' in completed.stderr


def test_empty_repository_has_nothing_to_report(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A repository with no commits is a preflight error."""
    empty = plugin_tmp_path / 'empty'
    empty.mkdir()
    git(empty, 'init', '--quiet')

    completed = run_script(plugin_root, empty)

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert 'Repository does not contain any commits yet.' in completed.stderr
