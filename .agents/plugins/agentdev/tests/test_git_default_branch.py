#!/usr/bin/env python3

"""Tests for the default-branch helper in bin/git_default_branch.py."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from git_fixtures import git, stub_gh
import pytest

SCRIPT_PATH = 'bin/git_default_branch.py'


def run_helper(
    plugin_root: Path, cwd: Path, *arguments: str, path: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the helper's command line with only the standard library."""
    environment = dict(os.environ)
    if path is not None:
        environment['PATH'] = path
    return subprocess.run(
        [sys.executable, '-S', str(plugin_root / SCRIPT_PATH), *arguments],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


@pytest.fixture
def clone(unrelated_repository: Path, plugin_tmp_path: Path) -> Path:
    """Clone a repository whose default branch is trunk."""
    git(unrelated_repository, 'checkout', '--quiet', '-b', 'trunk')
    git(unrelated_repository, 'add', 'README.md')
    git(unrelated_repository, 'commit', '--quiet', '-m', 'Initial commit')
    destination = plugin_tmp_path / 'clone'
    git(plugin_tmp_path, 'clone', '--quiet', str(unrelated_repository), str(destination))
    return destination


@pytest.mark.parametrize(('branch', 'expected'), [('main', 0), ('master', 0), ('trunk', 1)])
def test_is_default_recognizes_main_and_master(
    plugin_root: Path, plugin_tmp_path: Path, branch: str, expected: int
) -> None:
    """Only main and master count as conventional default-branch names."""
    assert run_helper(plugin_root, plugin_tmp_path, 'is-default', branch).returncode == expected


def test_remote_reads_the_remote_head(
    plugin_root: Path, clone: Path, plugin_tmp_path: Path
) -> None:
    """refs/remotes/<remote>/HEAD must answer without asking GitHub."""
    git_dir = Path(subprocess.check_output(['which', 'git'], text=True).strip()).parent
    empty = plugin_tmp_path / 'no-gh'
    empty.mkdir()
    (empty / 'git').symlink_to(git_dir / 'git')

    completed = run_helper(plugin_root, clone, 'remote', 'origin', path=str(empty))

    assert (completed.returncode, completed.stdout) == (0, 'trunk\n')


def test_remote_falls_back_to_github(
    plugin_root: Path, clone: Path, plugin_tmp_path: Path
) -> None:
    """Without a remote HEAD, gh's answer for the remote URL must be used."""
    git(clone, 'remote', 'set-head', 'origin', '--delete')
    stubs = stub_gh(plugin_tmp_path / 'stubs', 'echo develop')
    git_dir = Path(subprocess.check_output(['which', 'git'], text=True).strip()).parent

    completed = run_helper(plugin_root, clone, 'remote', 'origin', path=f'{stubs}:{git_dir}')

    assert (completed.returncode, completed.stdout) == (0, 'develop\n')
    assert (stubs / 'gh-args').read_text().splitlines()[:2] == ['repo', 'view']


def test_remote_fails_when_nothing_knows(
    plugin_root: Path, clone: Path, plugin_tmp_path: Path
) -> None:
    """Without a remote HEAD and with gh failing, the helper must exit 1 printing nothing."""
    git(clone, 'remote', 'set-head', 'origin', '--delete')
    stubs = stub_gh(plugin_tmp_path / 'stubs', 'exit 1')
    git_dir = Path(subprocess.check_output(['which', 'git'], text=True).strip()).parent

    completed = run_helper(plugin_root, clone, 'remote', 'origin', path=f'{stubs}:{git_dir}')

    assert (completed.returncode, completed.stdout) == (1, '')


def test_bad_usage_exits_two(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """An unknown request must print usage on stderr and exit 2."""
    completed = run_helper(plugin_root, plugin_tmp_path, 'bogus')

    assert completed.returncode == 2
    assert completed.stdout == ''
    assert 'Usage:' in completed.stderr
