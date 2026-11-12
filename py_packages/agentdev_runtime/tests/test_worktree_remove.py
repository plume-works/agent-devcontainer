"""`worktree remove`, Claude Code's WorktreeRemove hook, deletes a worktree and its environment."""

import json
import os
from pathlib import Path
import subprocess
import sys

from agentdev_runtime import worktree
from agentdev_runtime.settings import DEVCONTAINER
import pytest

GIT_ID = ['-c', 'user.name=t', '-c', 'user.email=t@example.invalid']


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, claude_stub: Path) -> Path:
    repo = tmp_path / 'repo'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    subprocess.run(['git', *GIT_ID, '-C', str(repo), 'commit', '-q', '--allow-empty', '-m', 'i'])
    monkeypatch.setenv('AGENTDEV_RUNTIME_MODE', DEVCONTAINER)
    monkeypatch.setenv('AGENTDEV_VENV_ROOT', str(tmp_path / 'uv' / 'venvs'))
    return repo


def hook(action: str, request: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, '-m', 'agentdev_runtime', 'worktree', action],
        input=json.dumps(request),
        capture_output=True,
        text=True,
        env=os.environ,
        check=False,
    )


def test_a_created_worktree_is_removed_with_its_environment(repository: Path) -> None:
    created = hook('create', {'cwd': str(repository), 'name': 'task'})
    assert created.returncode == 0, created.stderr
    path = Path(created.stdout.strip())
    environment = repository.parent / 'uv' / 'venvs' / 'task'
    (environment / 'pyvenv.cfg').write_text('home = /usr/bin\n')
    (path / 'notes.txt').write_text('untracked\n')
    removed = hook('remove', {'cwd': str(repository), 'worktree_path': str(path)})
    assert removed.returncode == 0, removed.stderr
    assert not path.exists()
    assert not environment.exists()
    assert not environment.with_name('task.checkout').exists()
    branches = subprocess.run(
        ['git', '-C', str(repository), 'branch', '--list', 'worktree-task'],
        capture_output=True,
        text=True,
        check=True,
    )
    assert branches.stdout.strip() == 'worktree-task'


def test_a_worktree_without_a_venv_link_is_removed(repository: Path) -> None:
    path = repository.parent / 'plain'
    subprocess.run(['git', '-C', str(repository), 'worktree', 'add', '-q', str(path)], check=True)
    assert worktree.remove(json.dumps({'worktree_path': str(path)})) == 0
    assert not path.exists()


def test_a_gone_worktree_is_not_an_error(tmp_path: Path, claude_stub: Path) -> None:
    assert worktree.remove(json.dumps({'worktree_path': str(tmp_path / 'gone')})) == 0
