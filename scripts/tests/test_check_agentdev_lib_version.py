"""Tests for scripts/check-agentdev-lib-version.py run in a made-up repository."""

from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/check-agentdev-lib-version.py'
IDENTITY = {
    'GIT_AUTHOR_NAME': 'Fixture Author',
    'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
    'GIT_COMMITTER_NAME': 'Fixture Author',
    'GIT_COMMITTER_EMAIL': 'fixture@example.invalid',
}
INHERITED_GIT = ('GIT_DIR', 'GIT_INDEX_FILE', 'GIT_WORK_TREE')


def environment() -> dict[str, str]:
    """Return the environment with the fixture identity and no inherited repository."""
    kept = {key: value for key, value in os.environ.items() if key not in INHERITED_GIT}
    return {**kept, **IDENTITY}


def git(repository: Path, *arguments: str) -> None:
    """Run a fixture git command in `repository`."""
    subprocess.run(
        ['git', *arguments], cwd=repository, env=environment(), check=True, capture_output=True
    )


def write_package(repository: Path, version: str, body: str) -> None:
    """Write the package's pyproject.toml at `version` and its module with `body`."""
    package = repository / 'py_packages/agentdev_lib'
    (package / 'agentdev_lib').mkdir(parents=True, exist_ok=True)
    (package / 'pyproject.toml').write_text(
        f'[project]\nname = "agentdev-lib"\nversion = "{version}"\n'
    )
    (package / 'agentdev_lib/__init__.py').write_text(body)


def commit(repository: Path, message: str) -> None:
    """Commit every change in `repository`."""
    git(repository, 'add', '--all')
    git(repository, 'commit', '--quiet', '-m', message)


@pytest.fixture
def repository() -> Iterator[Path]:
    """Yield a repository whose package 1.0 is tagged agentdev-lib/1.0 and then changed."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'check-agentdev-lib-version-{uuid4().hex}'
    root.mkdir()
    git(root, 'init', '--quiet', '--initial-branch=main')
    write_package(root, '1.0', 'ANSWER = 1\n')
    commit(root, 'Release 1.0')
    git(root, 'tag', 'agentdev-lib/1.0')
    write_package(root, '1.0', 'ANSWER = 2\n')
    commit(root, 'Change the package')
    yield root
    shutil.rmtree(root)


def check(repository: Path) -> subprocess.CompletedProcess[str]:
    """Run the check from the root of `repository`."""
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=repository,
        env=environment(),
        capture_output=True,
        text=True,
        check=False,
    )


def test_change_without_bump_fails(repository: Path) -> None:
    """A change after the tag that keeps the tagged version fails the check."""
    completed = check(repository)

    assert completed.returncode == 1
    assert 'keeps version 1.0' in completed.stderr


def test_change_with_bump_passes(repository: Path) -> None:
    """The same change with a new version passes."""
    write_package(repository, '1.1', 'ANSWER = 2\n')
    commit(repository, 'Raise the version')

    assert check(repository).returncode == 0
