#!/usr/bin/env python3

"""Tests for the shared Python skill-script helpers in bin/skill_common.py."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from git_fixtures import git
import pytest

PROBE = """\
import sys
sys.path.insert(0, sys.argv[1])
import skill_common as common
request = sys.argv[2]
try:
    if request == 'root':
        print(common.require_git_repo())
    elif request == 'main':
        print(common.main_checkout_dir())
    elif request == 'branch':
        print(common.current_branch())
    elif request == 'header':
        print(common.help_header('Describe it.', sys.argv[3]), end='')
except common.Stop as stop:
    sys.exit(stop.code)
"""


def probe(plugin_root: Path, cwd: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run one helper through a standard-library-only interpreter in `cwd`."""
    return subprocess.run(
        [sys.executable, '-S', '-c', PROBE, str(plugin_root / 'bin'), *arguments],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, 'GIT_CEILING_DIRECTORIES': str(Path('/tmp/agentdev-tests'))},
    )


@pytest.fixture
def repository(unrelated_repository: Path) -> Path:
    """Commit once on main in an unrelated repository."""
    git(unrelated_repository, 'add', 'README.md')
    git(unrelated_repository, 'commit', '--quiet', '-m', 'Initial commit')
    return unrelated_repository


def test_require_git_repo_returns_the_top_level(plugin_root: Path, repository: Path) -> None:
    """Inside a repository the helper must return its top level, from any subdirectory."""
    nested = repository / 'nested'
    nested.mkdir()

    completed = probe(plugin_root, nested, 'root')

    assert completed.returncode == 0, completed.stderr
    assert Path(completed.stdout.strip()) == repository.resolve()


def test_require_git_repo_stops_outside_a_repository(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Outside a repository the helper must stop with a preflight error and say why."""
    outside = plugin_tmp_path / 'outside'
    outside.mkdir()

    completed = probe(plugin_root, outside, 'root')

    assert completed.returncode == 2
    assert completed.stderr == 'ERROR: This script must be run inside a Git repository.\n'


def test_main_checkout_dir_is_shared_by_linked_worktrees(
    plugin_root: Path, repository: Path, plugin_tmp_path: Path
) -> None:
    """A linked worktree must report the main checkout, not its own directory."""
    linked = plugin_tmp_path / 'linked'
    git(repository, 'worktree', 'add', '--quiet', '-b', 'feature', str(linked))

    completed = probe(plugin_root, linked, 'main')

    assert Path(completed.stdout.strip()) == repository.resolve()


def test_current_branch_names_the_checked_out_branch(plugin_root: Path, repository: Path) -> None:
    """The helper must print the branch HEAD points at."""
    assert probe(plugin_root, repository, 'branch').stdout == 'main\n'


def test_help_header_names_the_skill_root(plugin_root: Path, repository: Path) -> None:
    """The header must hold the description and the skill directory of the script."""
    script = plugin_root / 'skills' / 'fixture' / 'agent-code' / 'fixture.py'

    completed = probe(plugin_root, repository, 'header', str(script))

    assert completed.stdout == (
        f'Describe it.\n\nSkill root: {plugin_root.resolve() / "skills" / "fixture"}\n'
    )
