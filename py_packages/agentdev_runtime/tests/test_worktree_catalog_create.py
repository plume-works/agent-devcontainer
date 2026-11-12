"""`worktree create` gives a catalog checkout's worktree its own `wt-<name>` catalog."""

import json
import os
from pathlib import Path
import subprocess
import sys

from agentdev_runtime import catalog
from agentdev_runtime.settings import DEVCONTAINER
import pytest

GIT_ID = ['-c', 'user.name=t', '-c', 'user.email=t@example.invalid']
STUB = """#!/usr/bin/env python3
import json, os, sys
argv = sys.argv[1:]
with open(os.environ['CLAUDE_STUB_LOG'], 'a') as log:
    log.write(json.dumps({'argv': argv, 'cwd': os.getcwd()}) + '\\n')
if argv[:3] == ['plugin', 'marketplace', 'list']:
    print(open(os.environ['CLAUDE_STUB_MARKETPLACES']).read())
fail = os.environ.get('CLAUDE_STUB_FAIL')
sys.exit(1 if fail and fail in ' '.join(argv) else 0)
"""


@pytest.fixture
def stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Put a recording ``claude`` on PATH and isolate HOME and the venv root."""
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    (bin_dir / 'claude').write_text(STUB)
    (bin_dir / 'claude').chmod(0o755)
    log = tmp_path / 'claude.log'
    log.touch()
    marketplaces = tmp_path / 'marketplaces.json'
    marketplaces.write_text('[]')
    (tmp_path / 'home').mkdir()
    (tmp_path / 'uv').mkdir()
    monkeypatch.setenv('PATH', f'{bin_dir}{os.pathsep}{os.environ["PATH"]}')
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    monkeypatch.setenv('CLAUDE_STUB_LOG', str(log))
    monkeypatch.setenv('CLAUDE_STUB_MARKETPLACES', str(marketplaces))
    monkeypatch.setenv('AGENTDEV_RUNTIME_MODE', DEVCONTAINER)
    monkeypatch.setenv('AGENTDEV_VENV_ROOT', str(tmp_path / 'uv' / 'venvs'))
    return log


def make_repository(root: Path, *, with_catalog: bool) -> Path:
    root.mkdir()
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    if with_catalog:
        manifest = root / catalog.CLAUDE_MANIFEST
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            json.dumps(
                {
                    'name': 'shared',
                    'plugins': [
                        {'name': 'agentdev', 'source': './.agents/plugins/agentdev'},
                        {'name': 'extra', 'source': './.agents/plugins/extra'},
                    ],
                }
            )
        )
        (root / catalog.OPENCODE_BRIDGE).mkdir(parents=True)
        (root / catalog.OPENCODE_BRIDGE / 'keep').touch()
        subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True)
    subprocess.run(['git', *GIT_ID, '-C', str(root), 'commit', '-q', '--allow-empty', '-m', 'i'])
    local = root / '.claude' / 'settings.local.json'
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(json.dumps({'permissions': {'allow': ['Bash(ls:*)', 'Read']}}))
    return root


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
    tmp_path: Path, stub: Path
) -> None:
    repo = make_repository(tmp_path / 'repo', with_catalog=False)
    result = hook(repo, 'plain')
    assert result.returncode == 0, result.stderr
    path = Path(result.stdout.strip())
    assert local_settings(path) == {'permissions': {'allow': ['Bash(ls:*)', 'Read']}}
    assert calls(stub) == []
    assert not (path / '.claude' / 'marketplace.local.json').exists()


def test_permissions_merge_without_duplicates(tmp_path: Path, stub: Path) -> None:
    repo = make_repository(tmp_path / 'repo', with_catalog=False)
    path = Path(hook(repo, 'twice').stdout.strip())
    settings = path / '.claude' / 'settings.local.json'
    settings.write_text(json.dumps({'permissions': {'allow': ['Read', 'Write']}}))
    assert hook(repo, 'twice').returncode == 0
    assert local_settings(path)['permissions']['allow'] == ['Read', 'Write', 'Bash(ls:*)']


def test_a_catalog_repository_installs_its_own_catalog(tmp_path: Path, stub: Path) -> None:
    repo = make_repository(tmp_path / 'repo', with_catalog=True)
    result = hook(repo, 'task')
    assert result.returncode == 0, result.stderr
    path = repo / '.claude' / 'worktrees' / 'task'
    assert result.stdout == f'{path}\n'
    local = path / '.claude' / 'marketplace.local.json'
    assert json.loads(local.read_text())['name'] == 'wt-task'
    assert json.loads(local.read_text())['plugins'][0]['source'] == './.agents/plugins/agentdev'
    assert calls(stub) == [
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
    tmp_path: Path, stub: Path, monkeypatch: pytest.MonkeyPatch
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
    assert calls(stub)[-1]['argv'] == ['plugin', 'marketplace', 'remove', 'wt-doomed']
