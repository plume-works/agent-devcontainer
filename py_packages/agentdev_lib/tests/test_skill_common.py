#!/usr/bin/env python3

"""Tests for the shared Python skill-script helpers in agentdev_lib.skill_common."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from agentdev_lib.skill_common import bash_quote
from lib_fixtures import git, SCRATCH_ROOT
import pytest

PROBE = """\
import sys
from agentdev_lib import skill_common as common
request = sys.argv[1]
try:
    if request == 'root':
        print(common.require_git_repo())
    elif request == 'main':
        print(common.main_checkout_dir())
    elif request == 'branch':
        print(common.current_branch())
    elif request == 'header':
        print(common.help_header('Describe it.', sys.argv[2]), end='')
except common.Stop as stop:
    sys.exit(stop.code)
"""


def probe(cwd: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run one helper through a fresh interpreter in `cwd`."""
    return subprocess.run(
        [sys.executable, '-c', PROBE, *arguments],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, 'GIT_CEILING_DIRECTORIES': str(SCRATCH_ROOT)},
    )


@pytest.fixture
def repository(unrelated_repository: Path) -> Path:
    """Commit once on main in an unrelated repository."""
    git(unrelated_repository, 'add', 'README.md')
    git(unrelated_repository, 'commit', '--quiet', '-m', 'Initial commit')
    return unrelated_repository


def test_require_git_repo_returns_the_top_level(repository: Path) -> None:
    """Inside a repository the helper must return its top level, from any subdirectory."""
    nested = repository / 'nested'
    nested.mkdir()

    completed = probe(nested, 'root')

    assert completed.returncode == 0, completed.stderr
    assert Path(completed.stdout.strip()) == repository.resolve()


def test_require_git_repo_stops_outside_a_repository(scratch: Path) -> None:
    """Outside a repository the helper must stop with a preflight error and say why."""
    outside = scratch / 'outside'
    outside.mkdir()

    completed = probe(outside, 'root')

    assert completed.returncode == 2
    assert completed.stderr == 'ERROR: This script must be run inside a Git repository.\n'


def test_main_checkout_dir_is_shared_by_linked_worktrees(repository: Path, scratch: Path) -> None:
    """A linked worktree must report the main checkout, not its own directory."""
    linked = scratch / 'linked'
    git(repository, 'worktree', 'add', '--quiet', '-b', 'feature', str(linked))

    completed = probe(linked, 'main')

    assert Path(completed.stdout.strip()) == repository.resolve()


def test_current_branch_names_the_checked_out_branch(repository: Path) -> None:
    """The helper must print the branch HEAD points at."""
    assert probe(repository, 'branch').stdout == 'main\n'


def test_help_header_names_the_skill_root(scratch: Path, repository: Path) -> None:
    """The header must hold the description and the skill directory of the script."""
    script = scratch / 'plugin' / 'skills' / 'fixture' / 'agent-code' / 'fixture.py'

    completed = probe(repository, 'header', str(script))

    assert completed.stdout == (
        f'Describe it.\n\nSkill root: {scratch.resolve() / "plugin" / "skills" / "fixture"}\n'
    )


@pytest.mark.parametrize(
    'word',
    ['plain-path/x.y_z', 'a b', "it's", '$HOME', '', '~x', 'x~y', 'a=~b', 'x:~y', '#c', 'd#e',
     'tab\there', 'new\nline', 'ünï', 'a,b', '{x}', 'esc\x1b', '\x01'],
)  # fmt: skip
def test_bash_quote_matches_printf_q(word: str) -> None:
    """bash_quote reproduces bash's printf %q byte for byte."""
    expected = subprocess.run(
        ['bash', '-c', 'printf %q "$1"', '_', word], capture_output=True, text=True, check=True
    ).stdout

    assert bash_quote(word) == expected
