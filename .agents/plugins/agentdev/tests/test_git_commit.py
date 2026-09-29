#!/usr/bin/env python3

"""Behavior tests for the git-commit skill's guarded commit script."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

FIXTURE_ENV = {
    'GIT_AUTHOR_NAME': 'Fixture Author',
    'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
    'GIT_COMMITTER_NAME': 'Fixture Author',
    'GIT_COMMITTER_EMAIL': 'fixture@example.invalid',
}


def git(cwd: Path, *args: str) -> str:
    """Run a fixture git command and return its stripped stdout."""
    completed = subprocess.run(
        ['git', *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **FIXTURE_ENV},
    )
    return completed.stdout.strip()


def initialize_repository(path: Path, branch: str) -> Path:
    """Create a repository with one commit on `branch` and a staged change."""
    path.mkdir()
    git(path, 'init', f'--initial-branch={branch}')
    (path / 'fixture.txt').write_text('fixture\n')
    git(path, 'add', 'fixture.txt')
    git(path, 'commit', '-m', 'fixture commit')
    (path / 'fixture.txt').write_text('changed\n')
    git(path, 'add', 'fixture.txt')
    return path


def run_commit(
    plugin_root: Path,
    cwd: Path,
    *args: str,
    path_prefix: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run git-commit.sh with `args`, optionally with `path_prefix` first on PATH."""
    env = {**os.environ, **FIXTURE_ENV}
    if path_prefix is not None:
        env['PATH'] = f'{path_prefix}{os.pathsep}{env["PATH"]}'
    return subprocess.run(
        [str(plugin_root / 'skills/git-commit/scripts/git-commit.sh'), *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )


def stub_gh(directory: Path, script_body: str) -> Path:
    """Install a fake `gh` running `script_body` and return its directory."""
    directory.mkdir()
    gh = directory / 'gh'
    gh.write_text(f'#!/bin/sh\n{script_body}\n')
    gh.chmod(0o755)
    return directory


def outcome(completed: subprocess.CompletedProcess[str]) -> tuple[int, str]:
    """Return the (exit code, last stdout line) contract pair."""
    return completed.returncode, completed.stdout.splitlines()[-1]


def commit_count(repository: Path) -> int:
    """Count the commits reachable from HEAD."""
    return int(git(repository, 'rev-list', '--count', 'HEAD'))


def test_commit_on_main_is_refused(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """The main branch is protected, and git commit never runs."""
    # Arrange
    repository = initialize_repository(plugin_tmp_path / 'repo', 'main')

    # Act
    completed = run_commit(plugin_root, repository, '--', '-m', 'fixture change')

    # Assert
    assert outcome(completed) == (3, 'RESULT=PROTECTED_BRANCH')
    assert 'GIT_EXIT_CODE' not in completed.stdout
    assert '/agentdev:git-new-branch' in completed.stderr
    assert commit_count(repository) == 1


def test_commit_on_master_is_refused(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """The master branch is protected as well."""
    # Arrange
    repository = initialize_repository(plugin_tmp_path / 'repo', 'master')

    # Act
    completed = run_commit(plugin_root, repository, '--', '-m', 'fixture change')

    # Assert
    assert outcome(completed) == (3, 'RESULT=PROTECTED_BRANCH')
    assert commit_count(repository) == 1


def test_commit_on_the_remote_head_branch_is_refused(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A default branch with another name is protected through refs/remotes/origin/HEAD."""
    # Arrange
    seed = initialize_repository(plugin_tmp_path / 'seed', 'fixture-trunk')
    git(seed, 'commit', '-m', 'seed change')
    remote = plugin_tmp_path / 'remote.git'
    git(plugin_tmp_path, 'clone', '--bare', str(seed), str(remote))
    repository = plugin_tmp_path / 'work'
    git(plugin_tmp_path, 'clone', str(remote), str(repository))
    (repository / 'fixture.txt').write_text('work change\n')
    git(repository, 'add', 'fixture.txt')

    # Act
    completed = run_commit(plugin_root, repository, '--', '-m', 'fixture change')

    # Assert
    assert outcome(completed) == (3, 'RESULT=PROTECTED_BRANCH')
    assert commit_count(repository) == 2


def test_commit_on_a_feature_branch_succeeds(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A feature branch commits normally and reports git's own status."""
    # Arrange
    repository = initialize_repository(plugin_tmp_path / 'repo', 'main')
    git(repository, 'switch', '-c', 'fixture-topic')

    # Act
    completed = run_commit(plugin_root, repository, '--', '-m', 'fixture change')

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert 'GIT_EXIT_CODE=0' in completed.stdout.splitlines()
    assert git(repository, 'log', '-1', '--format=%s') == 'fixture change'


def test_failing_commit_reports_commit_failed(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """With nothing staged, git commit fails and its status is carried as a payload key."""
    # Arrange
    repository = initialize_repository(plugin_tmp_path / 'repo', 'main')
    git(repository, 'switch', '-c', 'fixture-topic')
    git(repository, 'commit', '-m', 'take the staged change')

    # Act
    completed = run_commit(plugin_root, repository, '--', '-m', 'empty change')

    # Assert
    assert outcome(completed) == (4, 'RESULT=COMMIT_FAILED')
    assert 'GIT_EXIT_CODE=1' in completed.stdout.splitlines()


def test_detached_head_is_a_preflight_error(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A detached HEAD has no branch to commit on."""
    # Arrange
    repository = initialize_repository(plugin_tmp_path / 'repo', 'main')
    git(repository, 'switch', '--detach')

    # Act
    completed = run_commit(plugin_root, repository, '--', '-m', 'fixture change')

    # Assert
    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert commit_count(repository) == 1


def test_unknown_default_branch_of_a_configured_remote_is_refused(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A remote whose default branch nobody can name blocks the commit instead of guessing."""
    # Arrange
    repository = initialize_repository(plugin_tmp_path / 'repo', 'main')
    git(repository, 'switch', '-c', 'fixture-topic')
    git(repository, 'remote', 'add', 'origin', str(plugin_tmp_path / 'remote.git'))
    stub_dir = stub_gh(plugin_tmp_path / 'stub-bin', 'exit 1')

    # Act
    completed = run_commit(
        plugin_root, repository, '--', '-m', 'fixture change', path_prefix=stub_dir
    )

    # Assert
    assert outcome(completed) == (5, 'RESULT=DEFAULT_UNKNOWN')
    assert 'GIT_EXIT_CODE' not in completed.stdout
    assert 'git remote set-head origin --auto' in completed.stderr
    assert commit_count(repository) == 1


def test_missing_remote_protects_only_main_and_master(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """Without the remote configured at all, a feature branch commits even when gh knows nothing."""
    # Arrange
    repository = initialize_repository(plugin_tmp_path / 'repo', 'main')
    git(repository, 'switch', '-c', 'fixture-topic')
    stub_dir = stub_gh(plugin_tmp_path / 'stub-bin', 'exit 1')

    # Act
    completed = run_commit(
        plugin_root, repository, '--', '-m', 'fixture change', path_prefix=stub_dir
    )

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert commit_count(repository) == 2
