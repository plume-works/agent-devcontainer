#!/usr/bin/env python3

"""Behavior tests for the update-branch skill script."""

from __future__ import annotations

from pathlib import Path
import subprocess


def initialize_repository(path: Path, branch: str = 'fixture-feature') -> None:
    """Create a repository with one commit on the selected branch."""
    path.mkdir()
    subprocess.run(
        ['git', 'init', f'--initial-branch={branch}'],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    (path / 'fixture.txt').write_text('fixture data\n')
    subprocess.run(
        ['git', 'add', 'fixture.txt'],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            'git',
            '-c',
            'user.name=Fixture Author',
            '-c',
            'user.email=fixture@example.invalid',
            'commit',
            '-m',
            'fixture commit',
        ],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )


def test_update_branch_reports_declared_result_when_fetch_fails(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A missing selected remote must produce the stable fetch-failure result."""
    # Arrange
    script = plugin_root / 'skills/update-branch/agent-code/update-branch.sh'
    mock_repository = plugin_tmp_path / 'fixture-repository'
    initialize_repository(mock_repository)

    # Act
    completed = subprocess.run(
        [str(script), '--remote', 'missing-fixture-remote'],
        cwd=mock_repository,
        check=False,
        capture_output=True,
        text=True,
    )

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        6,
        'RESULT=FETCH_FAILED',
    )


def test_update_branch_reports_preflight_error_when_base_branch_is_missing(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A fetched remote without the selected base branch must fail preflight."""
    # Arrange
    script = plugin_root / 'skills/update-branch/agent-code/update-branch.sh'
    mock_repository = plugin_tmp_path / 'fixture-repository'
    remote_repository = plugin_tmp_path / 'fixture-remote'
    initialize_repository(mock_repository)
    initialize_repository(remote_repository, branch='fixture-trunk')
    subprocess.run(
        ['git', 'remote', 'add', 'fixture-remote', str(remote_repository)],
        cwd=mock_repository,
        check=True,
        capture_output=True,
        text=True,
    )

    # Act
    completed = subprocess.run(
        [str(script), '--remote', 'fixture-remote', '--base', 'missing-base'],
        cwd=mock_repository,
        check=False,
        capture_output=True,
        text=True,
    )

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        2,
        'RESULT=PREFLIGHT_ERROR',
    )
    assert "Base branch 'fixture-remote/missing-base' was not found" in completed.stderr
