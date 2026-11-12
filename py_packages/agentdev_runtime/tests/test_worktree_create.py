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
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, claude_stub: Path) -> Path:
    """Make a repository with one commit, a venv root, and no inherited hooks."""
    repo = tmp_path / 'repo'
    repo.mkdir()
    subprocess.run(['git', 'init', '-q', str(repo)], check=True)
    subprocess.run(['git', *GIT_ID, '-C', str(repo), 'commit', '-q', '--allow-empty', '-m', 'i'])
    (repo / 'sub').mkdir()
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


def test_creating_a_name_again_reuses_its_worktree(repository: Path) -> None:
    first = run(repository, 'again')
    marker = repository / '.claude' / 'worktrees' / 'again' / 'work.txt'
    marker.write_text('in progress')
    second = run(repository, 'again')
    assert second.returncode == 0, second.stderr
    assert second.stdout == first.stdout
    assert marker.read_text() == 'in progress'


def test_creating_a_name_again_after_remove_checks_out_its_branch(repository: Path) -> None:
    path = repository / '.claude' / 'worktrees' / 'revived'
    run(repository, 'revived')
    subprocess.run(['git', *GIT_ID, '-C', str(path), 'commit', '-q', '--allow-empty', '-m', 'w'])
    tip = subprocess.run(
        ['git', '-C', str(path), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True
    ).stdout
    removed = subprocess.run(
        [sys.executable, '-m', 'agentdev_runtime', 'worktree', 'remove'],
        input=json.dumps({'worktree_path': str(path)}),
        text=True,
        check=False,
    )
    assert removed.returncode == 0
    result = run(repository, 'revived')
    assert result.returncode == 0, result.stderr
    assert result.stdout == f'{path}\n'
    head = subprocess.run(
        ['git', '-C', str(path), 'rev-parse', 'HEAD'], capture_output=True, text=True, check=True
    ).stdout
    assert head == tip
    assert (path / '.venv').is_symlink()


def test_a_failing_worktree_add_fails_the_hook(repository: Path) -> None:
    blocked = repository / '.claude' / 'worktrees' / 'taken'
    blocked.mkdir(parents=True)
    (blocked / 'stray.txt').write_text('not a worktree')
    result = run(repository, 'taken')
    assert result.returncode != 0
    assert result.stdout == ''
    assert 'git worktree add' in result.stderr
    assert 'worktree-taken' not in branches(repository)


def test_a_failing_link_keeps_a_branch_that_existed_before(
    repository: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    subprocess.run(['git', '-C', str(repository), 'branch', 'worktree-kept'], check=True)

    def broken(settings, path):
        raise PermissionError('read-only volume')

    monkeypatch.setattr(project, 'link_venv', broken)
    assert worktree.create(json.dumps({'cwd': str(repository), 'name': 'kept'})) == 1
    assert not (repository / '.claude' / 'worktrees' / 'kept').exists()
    assert 'worktree-kept' in branches(repository)


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


def rev(repo: Path, ref: str) -> str:
    return subprocess.run(
        ['git', '-C', str(repo), 'rev-parse', ref], capture_output=True, text=True, check=True
    ).stdout.strip()


def test_a_new_worktree_starts_at_the_freshly_fetched_remote_default_branch(
    repository: Path, tmp_path: Path
) -> None:
    origin = tmp_path / 'origin.git'
    subprocess.run(['git', 'clone', '-q', '--bare', str(repository), str(origin)], check=True)
    subprocess.run(['git', '-C', str(repository), 'remote', 'add', 'origin', str(origin)])
    subprocess.run(['git', '-C', str(repository), 'fetch', '-q', 'origin'], check=True)
    subprocess.run(['git', '-C', str(repository), 'remote', 'set-head', 'origin', '--auto'])
    upstream = tmp_path / 'upstream'
    subprocess.run(['git', 'clone', '-q', str(origin), str(upstream)], check=True)
    subprocess.run(
        ['git', *GIT_ID, '-C', str(upstream), 'commit', '-q', '--allow-empty', '-m', 'n']
    )
    subprocess.run(['git', '-C', str(upstream), 'push', '-q', 'origin', 'HEAD'], check=True)
    result = run(repository, 'fresh')
    assert result.returncode == 0, result.stderr
    assert rev(repository, 'worktree-fresh') == rev(upstream, 'HEAD') != rev(repository, 'HEAD')


def test_a_repository_without_a_remote_starts_the_worktree_at_head(repository: Path) -> None:
    result = run(repository, 'local')
    assert result.returncode == 0, result.stderr
    assert rev(repository, 'worktree-local') == rev(repository, 'HEAD')
