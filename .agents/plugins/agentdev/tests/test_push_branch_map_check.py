#!/usr/bin/env python3

"""Behavior tests for the codebase-map gate in the pr-open push-branch script."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import subprocess
import sys

from git_fixtures import FIXTURE_ENV, git, outcome

PUSH_SCRIPT = 'skills/pr-open/scripts/push-branch.sh'
MAP_SCRIPT = 'skills/iwe-map/scripts/stale-map-docs.py'
LIBRARY = 'docs/knowledge'
BRANCH = 'fixture-feature'


def _load_map_script():
    """Import the staleness script by path, so the digest has one definition."""
    plugin_root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(plugin_root / 'bin'))
    spec = importlib.util.spec_from_file_location('stale_map_docs', plugin_root / MAP_SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stale_map_docs = _load_map_script()


def commit_file(repository: Path, relative: str, content: str) -> None:
    """Write `relative` and commit it."""
    target = repository / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    git(repository, 'add', relative)
    git(repository, 'commit', '-m', f'write {relative}')


def source_digest(repository: Path, source: str) -> str:
    """Return the map digest of `source`, computed by the staleness script."""
    previous = Path.cwd()
    os.chdir(repository)
    try:
        return stale_map_docs.source_digest_for_paths([source])
    finally:
        os.chdir(previous)


def build_repository(path: Path, with_map: bool = True) -> Path:
    """Create a feature-branch repository with a bare remote and, optionally, a fresh map."""
    remote = path / 'remote.git'
    git(path, 'init', '--bare', str(remote))
    repository = path / 'repo'
    repository.mkdir()
    git(repository, 'init', f'--initial-branch={BRANCH}')
    git(repository, 'remote', 'add', 'origin', str(remote))
    commit_file(repository, 'src/timer/engine.txt', 'tick\n')
    if with_map:
        commit_file(
            repository, '.iwe/config.toml', f'version = 3\n\n[library]\npath = "{LIBRARY}"\n'
        )
        digest = source_digest(repository, 'src/timer')
        commit_file(
            repository,
            f'{LIBRARY}/data/codebase/timer.md',
            f"---\ntype: codebase\nsource: src/timer\nsource_digest: '{digest}'\n---\n\n# Timer\n",
        )
    return repository


def push(plugin_root: Path, repository: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run push-branch.sh inside `repository`."""
    return subprocess.run(
        [str(plugin_root / PUSH_SCRIPT), *arguments],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, **FIXTURE_ENV},
    )


def remote_head(repository: Path) -> str:
    """Return the remote branch SHA, or an empty string when it does not exist."""
    return git(repository, 'ls-remote', 'origin', f'refs/heads/{BRANCH}')


def map_check(completed: subprocess.CompletedProcess[str]) -> list[str]:
    """Return every MAP_CHECK line the script printed."""
    return [line for line in completed.stdout.splitlines() if line.startswith('MAP_CHECK=')]


def test_fresh_map_is_pushed_with_upstream(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A fresh map passes the gate on the first push."""
    # Arrange
    repository = build_repository(plugin_tmp_path)

    # Act
    completed = push(plugin_root, repository)

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert map_check(completed) == ['MAP_CHECK=fresh']
    assert remote_head(repository).startswith(git(repository, 'rev-parse', 'HEAD'))


def test_stale_map_is_not_pushed_to_existing_upstream(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A commit that moves mapped code without a refresh stops at MAP_STALE."""
    # Arrange
    repository = build_repository(plugin_tmp_path)
    assert outcome(push(plugin_root, repository)) == (0, 'RESULT=SUCCESS')
    pushed = remote_head(repository)
    commit_file(repository, 'src/timer/engine.txt', 'tock\n')

    # Act
    completed = push(plugin_root, repository)

    # Assert
    assert outcome(completed) == (6, 'RESULT=MAP_STALE')
    assert map_check(completed) == ['MAP_CHECK=stale']
    assert 'ACTION=push' not in completed.stdout.splitlines()
    assert 'STALE data/codebase/timer' in completed.stderr
    assert remote_head(repository) == pushed


def test_stale_map_is_not_pushed_with_upstream(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """The push-with-upstream path is gated too and creates no remote branch."""
    # Arrange
    repository = build_repository(plugin_tmp_path)
    commit_file(repository, 'src/timer/engine.txt', 'tock\n')

    # Act
    completed = push(plugin_root, repository)

    # Assert
    assert outcome(completed) == (6, 'RESULT=MAP_STALE')
    assert remote_head(repository) == ''


def test_skip_map_check_pushes_a_stale_map(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """The explicit override pushes without running the check."""
    # Arrange
    repository = build_repository(plugin_tmp_path)
    commit_file(repository, 'src/timer/engine.txt', 'tock\n')

    # Act
    completed = push(plugin_root, repository, '--skip-map-check')

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert map_check(completed) == ['MAP_CHECK=overridden']
    assert remote_head(repository).startswith(git(repository, 'rev-parse', 'HEAD'))


def test_repository_without_iwe_config_is_not_gated(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A repository with no IWE workspace pushes as before."""
    # Arrange
    repository = build_repository(plugin_tmp_path, with_map=False)

    # Act
    completed = push(plugin_root, repository)

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert map_check(completed) == ['MAP_CHECK=skipped']


def test_up_to_date_fresh_head_is_checked(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """ACTION=none still reports the verdict for the head already on the remote."""
    # Arrange
    repository = build_repository(plugin_tmp_path)
    assert outcome(push(plugin_root, repository)) == (0, 'RESULT=SUCCESS')

    # Act
    completed = push(plugin_root, repository)

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert 'ACTION=none' in completed.stdout.splitlines()
    assert map_check(completed) == ['MAP_CHECK=fresh']


def test_stale_head_pushed_outside_the_helper_is_caught(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A stale head that reached the remote through a bare push stops at MAP_STALE."""
    # Arrange
    repository = build_repository(plugin_tmp_path)
    assert outcome(push(plugin_root, repository)) == (0, 'RESULT=SUCCESS')
    commit_file(repository, 'src/timer/engine.txt', 'tock\n')
    git(repository, 'push', '--quiet')

    # Act
    completed = push(plugin_root, repository)

    # Assert
    assert outcome(completed) == (6, 'RESULT=MAP_STALE')
    assert map_check(completed) == ['MAP_CHECK=stale']
    assert 'ACTION=none' not in completed.stdout.splitlines()


def test_uncommitted_edit_does_not_change_the_verdict(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """The check reads the commit being pushed, not the working tree."""
    # Arrange
    repository = build_repository(plugin_tmp_path)
    (repository / 'src/timer/engine.txt').write_text('uncommitted\n')

    # Act
    completed = push(plugin_root, repository)

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert map_check(completed) == ['MAP_CHECK=fresh']


def test_check_worktree_is_removed(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """The temporary worktree is gone after both a fresh and a stale verdict."""
    # Arrange
    repository = build_repository(plugin_tmp_path)
    push(plugin_root, repository)
    commit_file(repository, 'src/timer/engine.txt', 'tock\n')

    # Act
    push(plugin_root, repository)

    # Assert
    assert len(git(repository, 'worktree', 'list').splitlines()) == 1
    assert list((repository / '.tmp').iterdir()) == []
