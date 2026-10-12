#!/usr/bin/env python3

"""Behavior tests for the update-branch skill script."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

from git_fixtures import FIXTURE_ENV, git, outcome


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


class UpstreamFixture:
    """A bare remote, a working clone on a pushed feature branch, and a publisher clone."""

    def __init__(self, root: Path, branch: str = 'fixture-feature') -> None:
        self.root = root
        self.branch = branch
        seed = root / 'seed'
        seed.mkdir()
        git(seed, 'init', '--initial-branch=main')
        commit_file(seed, 'fixture.txt', 'one\ntwo\nthree\n')
        self.remote = root / 'remote.git'
        git(root, 'clone', '--bare', str(seed), str(self.remote))
        self.work = root / 'work'
        git(root, 'clone', str(self.remote), str(self.work))
        git(self.work, 'switch', '--no-track', '-c', branch, 'origin/main')
        git(self.work, 'push', '--set-upstream', 'origin', branch)
        self.publisher = root / 'publisher'
        git(root, 'clone', str(self.remote), str(self.publisher))

    def publish(self, branch: str, name: str, content: str) -> str:
        """Commit `name` on `branch` of the remote behind the working clone's back."""
        git(self.publisher, 'fetch', 'origin')
        git(self.publisher, 'switch', '-C', branch, f'origin/{branch}')
        commit_file(self.publisher, name, content)
        git(self.publisher, 'push', 'origin', branch)
        return git(self.publisher, 'rev-parse', 'HEAD')


def commit_file(repository: Path, name: str, content: str) -> None:
    """Write `name` in `repository` and commit it."""
    (repository / name).write_text(content)
    git(repository, 'add', name)
    git(repository, 'commit', '-m', f'write {name}')


def run_update(
    plugin_root: Path, cwd: Path, *args: str
) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    """Run update-branch.sh and parse the first value of each key=value stdout line."""
    script = plugin_root / 'skills/update-branch/agent-code/update-branch.sh'
    completed = subprocess.run(
        [str(script), *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, **FIXTURE_ENV},
    )
    keys: dict[str, str] = {}
    for line in completed.stdout.splitlines():
        key, separator, value = line.partition('=')
        if separator and key.isupper():
            keys.setdefault(key, value)
    return completed, keys


def is_ancestor(repository: Path, ancestor: str, descendant: str = 'HEAD') -> bool:
    """Return whether `ancestor` is reachable from `descendant`."""
    completed = subprocess.run(
        ['git', 'merge-base', '--is-ancestor', ancestor, descendant],
        cwd=repository,
        check=False,
    )
    return completed.returncode == 0


def test_branch_behind_its_upstream_is_fast_forwarded_before_the_base_merge(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A branch only behind its upstream fast-forwards, then merges the base on top."""
    # Arrange
    fixture = UpstreamFixture(plugin_tmp_path)
    upstream_sha = fixture.publish(fixture.branch, 'remote-only.txt', 'remote\n')
    fixture.publish('main', 'base.txt', 'base\n')

    # Act
    completed, keys = run_update(plugin_root, fixture.work)

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert keys['UPSTREAM_ACTION'] == 'fast-forward'
    assert git(fixture.work, 'rev-parse', 'HEAD^1') == upstream_sha
    assert is_ancestor(fixture.work, 'origin/main')


def test_upstream_that_already_contains_the_base_needs_no_merge_commit(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A fast-forward onto an upstream holding the base reports already up to date."""
    # Arrange
    fixture = UpstreamFixture(plugin_tmp_path)
    fixture.publish('main', 'base.txt', 'base\n')
    git(fixture.publisher, 'switch', '-C', fixture.branch, f'origin/{fixture.branch}')
    git(fixture.publisher, 'merge', '--no-ff', '-m', 'merge main', 'origin/main')
    git(fixture.publisher, 'push', 'origin', fixture.branch)
    upstream_sha = git(fixture.publisher, 'rev-parse', 'HEAD')

    # Act
    completed, keys = run_update(plugin_root, fixture.work)

    # Assert
    assert outcome(completed) == (3, 'RESULT=ALREADY_UP_TO_DATE')
    assert keys['UPSTREAM_ACTION'] == 'fast-forward'
    assert git(fixture.work, 'rev-parse', 'HEAD') == upstream_sha


def test_diverged_upstream_is_merged_before_the_base(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """Local and remote commits are merged, then the base is merged."""
    # Arrange
    fixture = UpstreamFixture(plugin_tmp_path)
    commit_file(fixture.work, 'local.txt', 'local\n')
    fixture.publish(fixture.branch, 'remote-only.txt', 'remote\n')
    fixture.publish('main', 'base.txt', 'base\n')

    # Act
    completed, keys = run_update(plugin_root, fixture.work)

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert keys['UPSTREAM_ACTION'] == 'merge'
    assert git(fixture.work, 'log', '--merges', '--format=%s', '-n', '2').splitlines() == [
        f'Merge origin/main into {fixture.branch}',
        f'Merge origin/{fixture.branch} into {fixture.branch}',
    ]
    assert is_ancestor(fixture.work, f'origin/{fixture.branch}')


def test_conflicting_upstream_merge_stops_and_a_rerun_merges_the_base(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """An upstream conflict stops before the base; the rerun after resolution continues."""
    # Arrange
    fixture = UpstreamFixture(plugin_tmp_path)
    commit_file(fixture.work, 'fixture.txt', 'one\nlocal\nthree\n')
    fixture.publish(fixture.branch, 'fixture.txt', 'one\nremote\nthree\n')
    fixture.publish('main', 'base.txt', 'base\n')

    # Act
    conflicted, conflicted_keys = run_update(plugin_root, fixture.work)
    (fixture.work / 'fixture.txt').write_text('one\nresolved\nthree\n')
    git(fixture.work, 'add', 'fixture.txt')
    git(fixture.work, 'commit', '--no-edit')
    rerun, rerun_keys = run_update(plugin_root, fixture.work)

    # Assert
    assert outcome(conflicted) == (4, 'RESULT=MERGE_CONFLICTS')
    assert conflicted_keys['SOURCE'] == f'origin/{fixture.branch}'
    assert not is_ancestor(fixture.work, 'origin/main', 'HEAD^1')
    assert outcome(rerun) == (0, 'RESULT=SUCCESS')
    assert rerun_keys['UPSTREAM_ACTION'] == 'none'
    assert is_ancestor(fixture.work, 'origin/main')


def test_conflicting_base_merge_names_the_base_as_source(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A conflict in the base merge reports the base ref as SOURCE."""
    # Arrange
    fixture = UpstreamFixture(plugin_tmp_path)
    commit_file(fixture.work, 'fixture.txt', 'one\nlocal\nthree\n')
    git(fixture.work, 'push')
    fixture.publish('main', 'fixture.txt', 'one\nbase\nthree\n')

    # Act
    completed, keys = run_update(plugin_root, fixture.work)

    # Assert
    assert outcome(completed) == (4, 'RESULT=MERGE_CONFLICTS')
    assert keys['UPSTREAM_ACTION'] == 'none'
    assert keys['SOURCE'] == 'origin/main'


def test_gone_upstream_is_skipped_with_a_warning(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A deleted remote branch warns and the base is still merged."""
    # Arrange
    fixture = UpstreamFixture(plugin_tmp_path)
    git(fixture.publisher, 'push', 'origin', '--delete', fixture.branch)
    fixture.publish('main', 'base.txt', 'base\n')

    # Act
    completed, keys = run_update(plugin_root, fixture.work)

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert keys['UPSTREAM_ACTION'] == 'gone'
    assert 'no longer exists' in completed.stderr
    assert is_ancestor(fixture.work, 'origin/main')


def test_upstream_that_is_the_base_ref_is_merged_once(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A branch tracking the base skips the upstream sync and merges the base once."""
    # Arrange
    fixture = UpstreamFixture(plugin_tmp_path)
    git(fixture.work, 'switch', '--track', '-c', 'fixture-tracks-base', 'origin/main')
    commit_file(fixture.work, 'local.txt', 'local\n')
    before = git(fixture.work, 'rev-parse', 'HEAD')
    fixture.publish('main', 'base.txt', 'base\n')

    # Act
    completed, keys = run_update(plugin_root, fixture.work)

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert keys['UPSTREAM_ACTION'] == 'base'
    assert git(fixture.work, 'rev-list', '--merges', '--count', f'{before}..HEAD') == '1'


def test_upstream_on_a_second_remote_is_fetched_and_brought_in(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """An upstream on another remote is fetched before it is synced."""
    # Arrange
    fixture = UpstreamFixture(plugin_tmp_path)
    fork = plugin_tmp_path / 'fork.git'
    git(plugin_tmp_path, 'clone', '--bare', str(fixture.remote), str(fork))
    git(fixture.work, 'remote', 'add', 'fixture-fork', str(fork))
    git(fixture.work, 'push', '--set-upstream', 'fixture-fork', fixture.branch)
    fork_publisher = plugin_tmp_path / 'fork-publisher'
    git(plugin_tmp_path, 'clone', '--branch', fixture.branch, str(fork), str(fork_publisher))
    commit_file(fork_publisher, 'fork-only.txt', 'fork\n')
    git(fork_publisher, 'push', 'origin', fixture.branch)
    fork_sha = git(fork_publisher, 'rev-parse', 'HEAD')
    fixture.publish('main', 'base.txt', 'base\n')

    # Act
    completed, keys = run_update(plugin_root, fixture.work)

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert (keys['UPSTREAM'], keys['UPSTREAM_ACTION']) == (
        f'fixture-fork/{fixture.branch}',
        'fast-forward',
    )
    assert is_ancestor(fixture.work, fork_sha)
    assert is_ancestor(fixture.work, 'origin/main')


def test_unreachable_upstream_remote_reports_fetch_failure(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A second upstream remote that cannot be fetched stops with FETCH_FAILED."""
    # Arrange
    fixture = UpstreamFixture(plugin_tmp_path)
    git(fixture.work, 'remote', 'add', 'fixture-fork', str(plugin_tmp_path / 'missing.git'))
    git(fixture.work, 'config', f'branch.{fixture.branch}.remote', 'fixture-fork')

    # Act
    completed, _ = run_update(plugin_root, fixture.work)

    # Assert
    assert outcome(completed) == (6, 'RESULT=FETCH_FAILED')
