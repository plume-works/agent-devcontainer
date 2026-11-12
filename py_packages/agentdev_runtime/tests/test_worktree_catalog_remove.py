"""`worktree remove` drops the `wt-<name>` catalog `worktree create` registered."""

from collections.abc import Callable
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


def hook(action: str, request: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, '-m', 'agentdev_runtime', 'worktree', action],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        env=os.environ,
        check=False,
    )


def calls(log: Path) -> list[list[str]]:
    return [json.loads(line)['argv'] for line in log.read_text().splitlines()]


@pytest.fixture
def created(tmp_path: Path, claude_stub: Path, make_repository: Callable[..., Path]) -> Path:
    """Return a worktree `worktree create` made in a catalog repository, its log cleared."""
    repo = make_repository(tmp_path / 'repo', with_catalog=True)
    result = hook('create', {'cwd': str(repo), 'name': 'task'})
    assert result.returncode == 0, result.stderr
    claude_stub.write_text('')
    return Path(result.stdout.strip())


def registered(name: str, path: Path) -> None:
    entry = {'name': name, 'path': str(path / '.claude' / 'marketplace.local.json')}
    Path(os.environ['CLAUDE_STUB_MARKETPLACES']).write_text(json.dumps([entry]))


def test_removing_a_worktree_removes_its_marketplace_first(
    created: Path, claude_stub: Path
) -> None:
    registered('wt-task', created)
    result = hook('remove', {'worktree_path': str(created)})
    assert result.returncode == 0, result.stderr
    assert calls(claude_stub) == [
        ['plugin', 'marketplace', 'list', '--json'],
        ['plugin', 'marketplace', 'remove', 'wt-task'],
    ]
    assert not created.exists()


def test_a_gone_worktree_still_loses_its_marketplace(created: Path, claude_stub: Path) -> None:
    registered('wt-task', created)
    subprocess.run(['git', '-C', str(created), 'worktree', 'remove', '--force', str(created)])
    result = hook('remove', {'worktree_path': str(created)})
    assert result.returncode == 0, result.stderr
    assert calls(claude_stub)[-1] == ['plugin', 'marketplace', 'remove', 'wt-task']


def test_a_worktree_without_a_marketplace_is_removed(created: Path, claude_stub: Path) -> None:
    result = hook('remove', {'worktree_path': str(created)})
    assert result.returncode == 0, result.stderr
    assert calls(claude_stub) == [['plugin', 'marketplace', 'list', '--json']]
    assert not created.exists()


def test_a_failing_marketplace_removal_keeps_the_worktree(
    created: Path, claude_stub: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registered('wt-task', created)
    monkeypatch.setenv('CLAUDE_STUB_FAIL', 'marketplace remove')
    result = hook('remove', {'worktree_path': str(created)})
    assert result.returncode != 0
    assert 'marketplace remove wt-task' in result.stderr
    assert created.exists()


def test_a_same_named_marketplace_of_another_worktree_is_kept(
    tmp_path: Path, created: Path, claude_stub: Path
) -> None:
    registered('wt-task', tmp_path / 'other' / '.claude' / 'worktrees' / 'task')
    result = hook('remove', {'worktree_path': str(created)})
    assert result.returncode == 0, result.stderr
    assert calls(claude_stub) == [['plugin', 'marketplace', 'list', '--json']]
    assert not created.exists()
