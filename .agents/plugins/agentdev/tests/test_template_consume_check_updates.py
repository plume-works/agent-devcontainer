#!/usr/bin/env python3

"""Behavior tests for the template-consume check-updates script."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess


def _env_without_repo_discovery(ceiling: Path) -> dict[str, str]:
    """Return an env stopping git's upward .git search at ``ceiling``, so cwd reads non-git."""
    env = dict(os.environ)
    env['GIT_CEILING_DIRECTORIES'] = str(ceiling)
    return env


def _run_git(args: list[str], cwd: Path) -> None:
    subprocess.run(
        ['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )


def build_template_repository(root: Path) -> tuple[Path, str, str]:
    """Build a two-commit fixture template repo; return (path, first_sha, second_sha)."""
    template_dir = root / 'fixture-template'
    template_dir.mkdir()
    _run_git(['init', '--initial-branch=main'], template_dir)

    (template_dir / 'file-a.txt').write_text('a\n')
    tracked_dir = template_dir / 'tracked-dir'
    tracked_dir.mkdir()
    (tracked_dir / 'file-b.txt').write_text('b\n')
    _run_git(['add', '-A'], template_dir)
    _run_git(['commit', '-m', 'first'], template_dir)
    first_sha = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=template_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    (tracked_dir / 'file-b.txt').write_text('b changed\n')
    _run_git(['add', '-A'], template_dir)
    _run_git(['commit', '-m', 'second'], template_dir)
    second_sha = subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=template_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    return template_dir, first_sha, second_sha


def build_consumer_repository(
    root: Path,
    consumed_ref: str,
    tracked_paths: list[str],
    source_repo: str = 'fixture/template',
) -> Path:
    """Build a consumer repo carrying a marker file pointed at consumed_ref."""
    consumer_dir = root / 'fixture-consumer'
    consumer_dir.mkdir()
    _run_git(['init', '--initial-branch=main'], consumer_dir)
    marker = {
        'source_repo': source_repo,
        'consumed_ref': consumed_ref,
        'workflow': 'A',
        'tracked_paths': tracked_paths,
        'last_synced_at': '2026-09-03T00:00:00Z',
    }
    (consumer_dir / '.agentdev-template.json').write_text(json.dumps(marker))
    _run_git(['add', '-A'], consumer_dir)
    _run_git(['commit', '-m', 'init'], consumer_dir)
    return consumer_dir


def test_check_updates_reports_changes_found_for_a_changed_tracked_path(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A tracked path modified upstream since consumed_ref must be reported."""
    # Arrange
    script = plugin_root / 'skills/template-consume/scripts/check-updates.sh'
    template_dir, first_sha, second_sha = build_template_repository(plugin_tmp_path)
    consumer_dir = build_consumer_repository(plugin_tmp_path, first_sha, ['tracked-dir'])

    # Act
    completed = subprocess.run(
        [str(script), '--root', str(consumer_dir), '--repo-url', str(template_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    # Assert
    lines = completed.stdout.splitlines()
    assert (completed.returncode, lines[-1]) == (5, 'RESULT=CHANGES_FOUND')
    assert f'CONSUMED_REF={first_sha}' in lines
    assert f'UPSTREAM_REF={second_sha}' in lines
    assert '  tracked-dir' in lines


def test_check_updates_reports_up_to_date_when_consumed_ref_matches_head(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A consumed_ref already at the template's HEAD must report UP_TO_DATE."""
    # Arrange
    script = plugin_root / 'skills/template-consume/scripts/check-updates.sh'
    template_dir, _first_sha, second_sha = build_template_repository(plugin_tmp_path)
    consumer_dir = build_consumer_repository(plugin_tmp_path, second_sha, ['tracked-dir'])

    # Act
    completed = subprocess.run(
        [str(script), '--root', str(consumer_dir), '--repo-url', str(template_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        4,
        'RESULT=UP_TO_DATE',
    )


def test_check_updates_reports_up_to_date_when_no_tracked_path_changed(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """Only file-a.txt is tracked, and it never changes between the two commits."""
    # Arrange
    script = plugin_root / 'skills/template-consume/scripts/check-updates.sh'
    template_dir, first_sha, _second_sha = build_template_repository(plugin_tmp_path)
    consumer_dir = build_consumer_repository(plugin_tmp_path, first_sha, ['file-a.txt'])

    # Act
    completed = subprocess.run(
        [str(script), '--root', str(consumer_dir), '--repo-url', str(template_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        4,
        'RESULT=UP_TO_DATE',
    )


def test_check_updates_reports_no_marker_when_marker_file_is_absent(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A consumer repository with no marker file must fail with NO_MARKER."""
    # Arrange
    script = plugin_root / 'skills/template-consume/scripts/check-updates.sh'
    consumer_dir = plugin_tmp_path / 'fixture-consumer-no-marker'
    consumer_dir.mkdir()
    _run_git(['init', '--initial-branch=main'], consumer_dir)
    (consumer_dir / 'placeholder.txt').write_text('x\n')
    _run_git(['add', '-A'], consumer_dir)
    _run_git(['commit', '-m', 'init'], consumer_dir)

    # Act
    completed = subprocess.run(
        [str(script), '--root', str(consumer_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        3,
        'RESULT=NO_MARKER',
    )


def test_check_updates_reports_invalid_marker_when_consumed_ref_is_missing(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A marker file missing consumed_ref must fail with INVALID_MARKER."""
    # Arrange
    script = plugin_root / 'skills/template-consume/scripts/check-updates.sh'
    consumer_dir = plugin_tmp_path / 'fixture-consumer-bad-marker'
    consumer_dir.mkdir()
    _run_git(['init', '--initial-branch=main'], consumer_dir)
    (consumer_dir / '.agentdev-template.json').write_text(
        json.dumps({'source_repo': 'fixture/template'})
    )
    _run_git(['add', '-A'], consumer_dir)
    _run_git(['commit', '-m', 'init'], consumer_dir)

    # Act
    completed = subprocess.run(
        [str(script), '--root', str(consumer_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        7,
        'RESULT=INVALID_MARKER',
    )


def test_check_updates_honors_root_from_a_non_git_cwd(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """--root must be validated as the repo, not the process CWD."""
    # Arrange
    script = plugin_root / 'skills/template-consume/scripts/check-updates.sh'
    template_dir, first_sha, _second_sha = build_template_repository(plugin_tmp_path)
    consumer_dir = build_consumer_repository(plugin_tmp_path, first_sha, ['tracked-dir'])
    non_git_cwd = plugin_tmp_path / 'not-a-git-repo'
    non_git_cwd.mkdir()

    # Act
    completed = subprocess.run(
        [str(script), '--root', str(consumer_dir), '--repo-url', str(template_dir)],
        cwd=non_git_cwd,
        env=_env_without_repo_discovery(plugin_tmp_path),
        check=False,
        capture_output=True,
        text=True,
    )

    # Assert
    last_line = completed.stdout.splitlines()[-1]
    assert (completed.returncode, last_line) == (5, 'RESULT=CHANGES_FOUND')


def test_check_updates_reports_invalid_marker_when_tracked_paths_is_empty(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A marker with an empty tracked_paths array must fail INVALID_MARKER."""
    # Arrange: a reachable consumed_ref so the gap under test is tracked_paths, not the ref.
    script = plugin_root / 'skills/template-consume/scripts/check-updates.sh'
    template_dir, first_sha, _second_sha = build_template_repository(plugin_tmp_path)
    consumer_dir = plugin_tmp_path / 'fixture-consumer-empty-tracked'
    consumer_dir.mkdir()
    _run_git(['init', '--initial-branch=main'], consumer_dir)
    (consumer_dir / '.agentdev-template.json').write_text(
        json.dumps({'consumed_ref': first_sha, 'tracked_paths': []})
    )
    _run_git(['add', '-A'], consumer_dir)
    _run_git(['commit', '-m', 'init'], consumer_dir)

    # Act
    completed = subprocess.run(
        [str(script), '--root', str(consumer_dir), '--repo-url', str(template_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        7,
        'RESULT=INVALID_MARKER',
    )


def test_check_updates_reports_invalid_marker_when_tracked_paths_is_absent(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A marker with no tracked_paths key must fail INVALID_MARKER."""
    # Arrange: a reachable consumed_ref so the gap under test is tracked_paths, not the ref.
    script = plugin_root / 'skills/template-consume/scripts/check-updates.sh'
    template_dir, first_sha, _second_sha = build_template_repository(plugin_tmp_path)
    consumer_dir = plugin_tmp_path / 'fixture-consumer-no-tracked'
    consumer_dir.mkdir()
    _run_git(['init', '--initial-branch=main'], consumer_dir)
    (consumer_dir / '.agentdev-template.json').write_text(json.dumps({'consumed_ref': first_sha}))
    _run_git(['add', '-A'], consumer_dir)
    _run_git(['commit', '-m', 'init'], consumer_dir)

    # Act
    completed = subprocess.run(
        [str(script), '--root', str(consumer_dir), '--repo-url', str(template_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        7,
        'RESULT=INVALID_MARKER',
    )


def test_check_updates_emits_result_on_unhandled_abort_after_trap(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """An unhandled set -e abort after the trap must still emit RESULT."""
    # Arrange
    script = plugin_root / 'skills/template-consume/scripts/check-updates.sh'
    template_dir, first_sha, _second_sha = build_template_repository(plugin_tmp_path)
    consumer_dir = build_consumer_repository(plugin_tmp_path, first_sha, ['tracked-dir'])
    # A regular file at .tmp makes `mkdir -p "${consumer_root}/.tmp"` abort under set -e.
    (consumer_dir / '.tmp').write_text('not a directory\n')

    # Act
    completed = subprocess.run(
        [str(script), '--root', str(consumer_dir), '--repo-url', str(template_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        1,
        'RESULT=SCRIPT_FAILURE',
    )


def test_check_updates_reports_clone_failed_for_an_unreachable_repo_url(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """An unreachable --repo-url must fail with CLONE_FAILED."""
    # Arrange
    script = plugin_root / 'skills/template-consume/scripts/check-updates.sh'
    consumer_dir = build_consumer_repository(plugin_tmp_path, 'deadbeef', ['tracked-dir'])
    unreachable_url = str(plugin_tmp_path / 'does-not-exist')

    # Act
    completed = subprocess.run(
        [str(script), '--root', str(consumer_dir), '--repo-url', unreachable_url],
        check=False,
        capture_output=True,
        text=True,
    )

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        6,
        'RESULT=CLONE_FAILED',
    )
