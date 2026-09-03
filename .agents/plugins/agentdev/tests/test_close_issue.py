#!/usr/bin/env python3

"""Behavior tests for the iwe-plan close-issue script."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

from test_update_branch import initialize_repository

SCRIPT_PATH = 'skills/iwe-plan/scripts/close-issue.sh'
PLAN_PATH = 'docs/knowledge/data/plans/20260903-fixture.md'


def install_gh_stub(path: Path, state: str) -> tuple[Path, Path]:
    """Create a stub `gh` reporting `state` for the issue and logging `issue close` calls."""
    stub_directory = path / 'stub-bin'
    stub_directory.mkdir(parents=True, exist_ok=True)
    for command in ('bash', 'git', 'dirname', 'sed', 'grep'):
        executable = shutil.which(command)
        assert executable is not None
        (stub_directory / command).symlink_to(executable)
    close_log = path / 'close.log'
    stub = stub_directory / 'gh'
    stub.write_text(
        f'#!{sys.executable}\n'
        'import sys\n'
        'arguments = sys.argv[1:]\n'
        'if arguments[:2] == ["auth", "status"]:\n'
        '    sys.exit(0)\n'
        'if arguments[:2] == ["repo", "view"]:\n'
        '    print("octo/repo")\n'
        '    sys.exit(0)\n'
        'if arguments[:2] == ["issue", "view"]:\n'
        '    print("ISSUE_URL=https://github.com/octo/repo/issues/42")\n'
        f'    print("ISSUE_STATE={state}")\n'
        '    sys.exit(0)\n'
        'if arguments[:2] == ["issue", "close"]:\n'
        f'    open({str(close_log)!r}, "a").write(" ".join(arguments) + "\\n")\n'
        '    sys.exit(0)\n'
        'sys.exit(1)\n'
    )
    stub.chmod(0o755)
    return stub_directory, close_log


def prepare_repository(path: Path) -> Path:
    """Create a fixture repository that already holds the plan document."""
    repository = path / 'repo'
    initialize_repository(repository)
    plan = repository / PLAN_PATH
    plan.parent.mkdir(parents=True)
    plan.write_text('# Fixture plan\n')
    return repository


def run_script(
    plugin_root: Path,
    repository: Path,
    stub_directory: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    """Run the close script inside `repository` with `PATH` limited to the stubs."""
    environment = dict(os.environ)
    environment['PATH'] = str(stub_directory)
    return subprocess.run(
        [str(plugin_root / SCRIPT_PATH), *arguments],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def test_open_issue_is_closed_with_plan_comment(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """An open issue must be closed once, with a comment naming the plan path."""
    # Arrange
    repository = prepare_repository(plugin_tmp_path)
    stub_directory, close_log = install_gh_stub(plugin_tmp_path, 'OPEN')

    # Act
    completed = run_script(
        plugin_root, repository, stub_directory, '--issue', '#42', '--plan', PLAN_PATH
    )

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (0, 'RESULT=SUCCESS')
    assert 'ISSUE_STATE=CLOSED' in completed.stdout.splitlines()
    close_calls = close_log.read_text().splitlines()
    assert len(close_calls) == 1
    assert close_calls[0].startswith('issue close 42 --repo octo/repo --comment ')
    assert PLAN_PATH in close_calls[0]
    assert 'fixture-feature' in close_calls[0]


def test_closed_issue_is_left_alone(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """An already closed issue must report ALREADY_CLOSED without a close call."""
    # Arrange
    repository = prepare_repository(plugin_tmp_path)
    stub_directory, close_log = install_gh_stub(plugin_tmp_path, 'CLOSED')

    # Act
    completed = run_script(
        plugin_root, repository, stub_directory, '--issue', '42', '--plan', PLAN_PATH
    )

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        5,
        'RESULT=ALREADY_CLOSED',
    )
    assert not close_log.exists()


def test_missing_plan_file_is_a_preflight_error(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A plan path that does not exist must stop before any gh call."""
    # Arrange
    repository = prepare_repository(plugin_tmp_path)
    stub_directory, close_log = install_gh_stub(plugin_tmp_path, 'OPEN')

    # Act
    completed = run_script(
        plugin_root, repository, stub_directory, '--issue', '42', '--plan', 'missing.md'
    )

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        2,
        'RESULT=PREFLIGHT_ERROR',
    )
    assert not close_log.exists()
