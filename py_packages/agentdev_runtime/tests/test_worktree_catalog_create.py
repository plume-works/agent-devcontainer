"""`worktree create` gives a catalog checkout's worktree its own `wt-<name>` catalog."""

from collections.abc import Callable
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


def hook(cwd: Path, name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, '-m', 'agentdev_runtime', 'worktree', 'create'],
        input=json.dumps({'session_id': 's', 'cwd': str(cwd), 'name': name}),
        capture_output=True,
        text=True,
        env=os.environ,
        check=False,
    )


def calls(log: Path) -> list[dict]:
    return [json.loads(line) for line in log.read_text().splitlines()]


def local_settings(path: Path) -> dict:
    return json.loads((path / '.claude' / 'settings.local.json').read_text())


def test_a_plain_repository_gets_permissions_and_no_marketplace(
    tmp_path: Path, claude_stub: Path, make_repository: Callable[..., Path]
) -> None:
    repo = make_repository(tmp_path / 'repo', with_catalog=False)
    result = hook(repo, 'plain')
    assert result.returncode == 0, result.stderr
    path = Path(result.stdout.strip())
    assert local_settings(path) == {'permissions': {'allow': ['Bash(ls:*)', 'Read']}}
    assert calls(claude_stub) == []
    assert not (path / '.claude' / 'marketplace.local.json').exists()


def test_permissions_merge_without_duplicates(
    tmp_path: Path, claude_stub: Path, make_repository: Callable[..., Path]
) -> None:
    repo = make_repository(tmp_path / 'repo', with_catalog=False)
    path = Path(hook(repo, 'twice').stdout.strip())
    settings = path / '.claude' / 'settings.local.json'
    settings.write_text(json.dumps({'permissions': {'allow': ['Read', 'Write']}}))
    assert hook(repo, 'twice').returncode == 0
    assert local_settings(path)['permissions']['allow'] == ['Read', 'Write', 'Bash(ls:*)']


def test_a_catalog_repository_installs_its_own_catalog(
    tmp_path: Path, claude_stub: Path, make_repository: Callable[..., Path]
) -> None:
    repo = make_repository(tmp_path / 'repo', with_catalog=True)
    result = hook(repo, 'task')
    assert result.returncode == 0, result.stderr
    path = repo / '.claude' / 'worktrees' / 'task'
    assert result.stdout == f'{path}\n'
    local = path / '.claude' / 'marketplace.local.json'
    assert json.loads(local.read_text())['name'] == 'wt-task'
    assert json.loads(local.read_text())['plugins'][0]['source'] == './.agents/plugins/agentdev'
    assert calls(claude_stub) == [
        {'argv': ['plugin', 'marketplace', 'add', str(local)], 'cwd': str(path)},
        {
            'argv': ['plugin', 'install', 'agentdev@wt-task', '--scope', 'local'],
            'cwd': str(path),
        },
        {'argv': ['plugin', 'install', 'extra@wt-task', '--scope', 'local'], 'cwd': str(path)},
    ]
    assert local_settings(path) == {
        'permissions': {'allow': ['Bash(ls:*)', 'Read']},
        'enabledPlugins': {'agentdev@shared': False, 'extra@shared': False},
    }


def test_a_failing_install_removes_the_worktree_and_registration(
    tmp_path: Path,
    claude_stub: Path,
    make_repository: Callable[..., Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = make_repository(tmp_path / 'repo', with_catalog=True)
    monkeypatch.setenv('CLAUDE_STUB_FAIL', 'install extra@wt-doomed')
    Path(os.environ['CLAUDE_STUB_MARKETPLACES']).write_text(json.dumps([{'name': 'wt-doomed'}]))
    result = hook(repo, 'doomed')
    assert result.returncode != 0
    assert result.stdout == ''
    assert 'install extra@wt-doomed' in result.stderr
    assert not (repo / '.claude' / 'worktrees' / 'doomed').exists()
    branches = subprocess.run(
        ['git', '-C', str(repo), 'branch', '--list', 'worktree-doomed'],
        capture_output=True,
        text=True,
        check=True,
    )
    assert branches.stdout == ''
    assert calls(claude_stub)[-1]['argv'] == ['plugin', 'marketplace', 'remove', 'wt-doomed']
