#!/usr/bin/env python3

"""Behavior tests for the iwe-explore fetch-issue script."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

from test_update_branch import initialize_repository

SCRIPT_PATH = 'skills/iwe-explore/scripts/fetch-issue.sh'

ISSUE_VIEW_OUTPUT = """ISSUE_NUMBER=42
ISSUE_URL=https://github.com/octo/repo/issues/42
ISSUE_STATE=OPEN
ISSUE_TITLE=Fixture issue
== ISSUE ==
# Fixture issue

## Body

Fixture body

## Comments

### octocat — 2026-09-01T00:00:00Z

Fixture comment
"""


def install_runtime_commands(path: Path) -> Path:
    """Create a PATH directory holding only the commands the script needs."""
    stub_directory = path / 'stub-bin'
    stub_directory.mkdir(parents=True, exist_ok=True)
    for command in ('bash', 'git', 'dirname', 'mkdir', 'sed', 'grep'):
        executable = shutil.which(command)
        assert executable is not None
        (stub_directory / command).symlink_to(executable)
    return stub_directory


def install_gh_stub(path: Path, mode: str) -> Path:
    """Create a stub `gh` whose `issue view` answer is selected by `mode`."""
    stub_directory = install_runtime_commands(path)
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
        'if arguments[:2] != ["issue", "view"]:\n'
        '    sys.exit(1)\n'
        f'mode = {mode!r}\n'
        'if mode == "not-found":\n'
        '    print("GraphQL: Could not resolve to an issue or pull request with the number of 999.",'
        ' file=sys.stderr)\n'
        '    sys.exit(1)\n'
        'if mode == "fail":\n'
        '    print("simulated network failure", file=sys.stderr)\n'
        '    sys.exit(1)\n'
        f'sys.stdout.write({ISSUE_VIEW_OUTPUT!r})\n'
    )
    stub.chmod(0o755)
    return stub_directory


def run_script(
    plugin_root: Path,
    repository: Path,
    stub_directory: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    """Run the fetch script inside `repository` with `PATH` limited to the stubs."""
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


def test_bare_number_resolves_repo_and_writes_issue_file(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A bare number must resolve the current repo and split keys from the document."""
    # Arrange
    repository = plugin_tmp_path / 'repo'
    initialize_repository(repository)
    stub_directory = install_gh_stub(plugin_tmp_path, 'ok')

    # Act
    completed = run_script(plugin_root, repository, stub_directory, '42')

    # Assert
    lines = completed.stdout.splitlines()
    assert (completed.returncode, lines[-1]) == (0, 'RESULT=SUCCESS')
    assert 'ISSUE_REPO=octo/repo' in lines
    assert 'ISSUE_TITLE=Fixture issue' in lines
    issue_file = Path(
        next(line for line in lines if line.startswith('ISSUE_FILE=')).split('=', 1)[1]
    )
    assert issue_file == repository / '.tmp' / 'issue-octo-repo-42.md'
    assert issue_file.read_text().startswith('# Fixture issue\n')
    assert 'Fixture comment' in issue_file.read_text()
    assert '== ISSUE ==' not in completed.stdout


def test_missing_issue_reports_issue_not_found(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """Gh's could-not-resolve error must become the ISSUE_NOT_FOUND result."""
    # Arrange
    repository = plugin_tmp_path / 'repo'
    initialize_repository(repository)
    stub_directory = install_gh_stub(plugin_tmp_path, 'not-found')

    # Act
    completed = run_script(plugin_root, repository, stub_directory, 'octo/repo#999')

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        4,
        'RESULT=ISSUE_NOT_FOUND',
    )


def test_gh_call_failure_reports_gh_unavailable(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """Any other gh failure must map to the fallback-eligible GH_UNAVAILABLE."""
    # Arrange
    repository = plugin_tmp_path / 'repo'
    initialize_repository(repository)
    stub_directory = install_gh_stub(plugin_tmp_path, 'fail')

    # Act
    completed = run_script(
        plugin_root, repository, stub_directory, 'https://github.com/octo/repo/issues/42'
    )

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        3,
        'RESULT=GH_UNAVAILABLE',
    )


def test_missing_gh_reports_gh_unavailable(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A PATH without gh must also produce GH_UNAVAILABLE."""
    # Arrange
    repository = plugin_tmp_path / 'repo'
    initialize_repository(repository)
    stub_directory = install_runtime_commands(plugin_tmp_path)

    # Act
    completed = run_script(plugin_root, repository, stub_directory, '42')

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        3,
        'RESULT=GH_UNAVAILABLE',
    )


def test_unparseable_reference_is_a_preflight_error(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A reference in none of the accepted forms must stop before any gh call."""
    # Arrange
    repository = plugin_tmp_path / 'repo'
    initialize_repository(repository)
    stub_directory = install_gh_stub(plugin_tmp_path, 'ok')

    # Act
    completed = run_script(plugin_root, repository, stub_directory, 'not-an-issue')

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        2,
        'RESULT=PREFLIGHT_ERROR',
    )
