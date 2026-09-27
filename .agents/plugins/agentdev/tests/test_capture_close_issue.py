#!/usr/bin/env python3

"""Behavior tests for the iwe-capture close-issue script."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

from test_update_branch import initialize_repository

SCRIPT_PATH = 'skills/iwe-capture/scripts/close-issue.sh'
DOC_PATH = 'docs/knowledge/data/bugs/fixture-bug.md'


def install_gh_stub(path: Path, view: str, authenticated: bool = True) -> tuple[Path, Path]:
    """Create a stub `gh` reporting `view` (a state, or `MISSING`) and logging closes."""
    stub_directory = path / 'stub-bin'
    stub_directory.mkdir(parents=True, exist_ok=True)
    for command in ('bash', 'cat', 'git', 'dirname', 'sed', 'grep'):
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
        f'    sys.exit({0 if authenticated else 1})\n'
        'if arguments[:2] == ["repo", "view"]:\n'
        '    print("octo/repo")\n'
        '    sys.exit(0)\n'
        'if arguments[:2] == ["issue", "view"]:\n'
        f'    if {view!r} == "MISSING":\n'
        '        print("GraphQL: Could not resolve to an issue", file=sys.stderr)\n'
        '        sys.exit(1)\n'
        '    print("ISSUE_URL=https://github.com/octo/repo/issues/42")\n'
        f'    print("ISSUE_STATE={view}")\n'
        '    sys.exit(0)\n'
        'if arguments[:2] == ["issue", "close"]:\n'
        f'    open({str(close_log)!r}, "a").write(" ".join(arguments) + "\\n")\n'
        '    sys.exit(0)\n'
        'sys.exit(1)\n'
    )
    stub.chmod(0o755)
    return stub_directory, close_log


def prepare_repository(path: Path) -> Path:
    """Create a fixture repository that already holds the captured document."""
    repository = path / 'repo'
    initialize_repository(repository)
    document = repository / DOC_PATH
    document.parent.mkdir(parents=True)
    document.write_text('# Bug: fixture\n')
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


def last_result(completed: subprocess.CompletedProcess[str]) -> tuple[int, str]:
    """Return the exit code and the final stdout line, where RESULT is printed."""
    return completed.returncode, completed.stdout.splitlines()[-1]


def test_open_issue_is_closed_with_document_comment(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """An open issue must be closed once, with a comment naming the captured document."""
    # Arrange
    repository = prepare_repository(plugin_tmp_path)
    stub_directory, close_log = install_gh_stub(plugin_tmp_path, 'OPEN')

    # Act
    completed = run_script(
        plugin_root, repository, stub_directory, '--issue', '#42', '--doc', DOC_PATH
    )

    # Assert
    assert last_result(completed) == (0, 'RESULT=SUCCESS')
    assert 'ISSUE_STATE=CLOSED' in completed.stdout.splitlines()
    close_calls = close_log.read_text().splitlines()
    assert len(close_calls) == 1
    assert close_calls[0].startswith('issue close 42 --repo octo/repo --comment ')
    assert DOC_PATH in close_calls[0]
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
        plugin_root, repository, stub_directory, '--issue', '42', '--doc', DOC_PATH
    )

    # Assert
    assert last_result(completed) == (5, 'RESULT=ALREADY_CLOSED')
    assert not close_log.exists()


def test_missing_issue_is_not_found(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """An issue number the repository does not have must report ISSUE_NOT_FOUND."""
    # Arrange
    repository = prepare_repository(plugin_tmp_path)
    stub_directory, close_log = install_gh_stub(plugin_tmp_path, 'MISSING')

    # Act
    completed = run_script(
        plugin_root, repository, stub_directory, '--issue', 'octo/repo#42', '--doc', DOC_PATH
    )

    # Assert
    assert last_result(completed) == (4, 'RESULT=ISSUE_NOT_FOUND')
    assert not close_log.exists()


def test_unauthenticated_gh_is_unavailable(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """An unauthenticated gh must report GH_UNAVAILABLE before any issue call."""
    # Arrange
    repository = prepare_repository(plugin_tmp_path)
    stub_directory, close_log = install_gh_stub(plugin_tmp_path, 'OPEN', authenticated=False)

    # Act
    completed = run_script(
        plugin_root, repository, stub_directory, '--issue', '42', '--doc', DOC_PATH
    )

    # Assert
    assert last_result(completed) == (3, 'RESULT=GH_UNAVAILABLE')
    assert not close_log.exists()


def test_missing_document_is_a_preflight_error(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A document path that does not exist must stop before any gh call."""
    # Arrange
    repository = prepare_repository(plugin_tmp_path)
    stub_directory, close_log = install_gh_stub(plugin_tmp_path, 'OPEN')

    # Act
    completed = run_script(
        plugin_root, repository, stub_directory, '--issue', '42', '--doc', 'missing.md'
    )

    # Assert
    assert last_result(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert not close_log.exists()


def test_help_lists_the_arguments_and_succeeds(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """`--help` must describe --issue and --doc and exit SUCCESS."""
    # Arrange
    repository = prepare_repository(plugin_tmp_path)
    stub_directory, _ = install_gh_stub(plugin_tmp_path, 'OPEN')

    # Act
    completed = run_script(plugin_root, repository, stub_directory, '--help')

    # Assert
    assert last_result(completed) == (0, 'RESULT=SUCCESS')
    assert '--issue <issue>' in completed.stdout
    assert '--doc <path>' in completed.stdout
