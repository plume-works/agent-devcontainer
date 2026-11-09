"""`worktree create`, Claude Code's WorktreeCreate hook, makes a worktree with its own `.venv`."""

import json
import os
from pathlib import Path
import subprocess
import sys

from agentdev_runtime import project, worktree
from agentdev_runtime.settings import DEVCONTAINER
import pytest

GIT_ID = ['-c', 'user.name=t', '-c', 'user.email=t@example.invalid']


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Make a repository with one commit, a venv root, and no inherited hooks."""
    repo = tmp_path / 'repo'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    subprocess.run(['git', *GIT_ID, '-C', str(repo), 'commit', '-q', '--allow-empty', '-m', 'i'])
    (repo / 'sub').mkdir()
    (tmp_path / 'uv').mkdir()
    monkeypatch.setenv('AGENTDEV_RUNTIME_MODE', DEVCONTAINER)
    monkeypatch.setenv('AGENTDEV_VENV_ROOT', str(tmp_path / 'uv' / 'venvs'))
    return repo


def run(cwd: Path, name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, '-m', 'agentdev_runtime', 'worktree', 'create'],
        input=json.dumps({'session_id': 's', 'cwd': str(cwd), 'name': name}),
        capture_output=True,
        text=True,
        env=os.environ,
        check=False,
    )


def branches(repo: Path) -> list[str]:
    listed = subprocess.run(
        ['git', '-C', str(repo), 'branch', '--format=%(refname:short)'],
        capture_output=True,
        text=True,
        check=True,
    )
    return listed.stdout.split()


def test_a_worktree_is_created_with_its_venv_linked(repository: Path) -> None:
    result = run(repository / 'sub', 'bridge-cse_1')
    assert result.returncode == 0, result.stderr
    path = repository / '.claude' / 'worktrees' / 'bridge-cse_1'
    assert result.stdout == f'{path}\n'
    assert 'worktree-bridge-cse_1' in branches(repository)
    venvs = repository.parent / 'uv' / 'venvs'
    assert Path(os.readlink(path / '.venv')) == venvs / 'bridge-cse_1'


def test_a_name_is_reduced_to_safe_characters(repository: Path) -> None:
    result = run(repository, 'my task/ü 1')
    assert result.returncode == 0, result.stderr
    assert result.stdout == f'{repository}/.claude/worktrees/my-task---1\n'
    assert 'worktree-my-task---1' in branches(repository)


def test_a_failing_worktree_add_fails_the_hook(repository: Path) -> None:
    subprocess.run(['git', '-C', str(repository), 'branch', 'worktree-taken'], check=True)
    result = run(repository, 'taken')
    assert result.returncode != 0
    assert result.stdout == ''
    assert 'git worktree add' in result.stderr
    assert not (repository / '.claude' / 'worktrees' / 'taken').exists()


def test_a_failing_link_removes_the_worktree_and_its_branch(
    repository: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    def broken(settings, path):
        raise PermissionError('read-only volume')

    monkeypatch.setattr(project, 'link_venv', broken)
    request = json.dumps({'cwd': str(repository), 'name': 'doomed'})
    assert worktree.create(request) == 1
    assert not (repository / '.claude' / 'worktrees' / 'doomed').exists()
    assert 'worktree-doomed' not in branches(repository)
    assert 'read-only volume' in capsys.readouterr().err


def test_unreadable_input_fails_the_hook(capsys: pytest.CaptureFixture[str]) -> None:
    assert worktree.create('{"name": "x"}') == 1
    assert 'unreadable hook input' in capsys.readouterr().err
