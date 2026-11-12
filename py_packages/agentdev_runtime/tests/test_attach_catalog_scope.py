"""The attach phase installs a complete checkout catalog at user scope."""

from collections.abc import Callable
import json
from pathlib import Path

from agentdev_runtime import lifecycle
from agentdev_runtime.settings import Settings
import pytest


def test_attach_installs_the_checkout_catalog_at_user_scope(
    tmp_path: Path,
    claude_stub: Path,
    make_repository: Callable[..., Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = make_repository(tmp_path / 'repo', with_catalog=True)
    monkeypatch.setenv('DEV_WORKSPACE_FOLDER', str(repo))
    monkeypatch.setenv('GIT_CONFIG_GLOBAL', str(tmp_path / 'gitconfig'))
    monkeypatch.setenv('OPENCODE_CONFIG_DIR', str(tmp_path / 'opencode'))
    monkeypatch.setenv('AGENTDEV_HOOKS_ROOT', str(tmp_path / 'hooks'))
    lifecycle.attached(Settings())
    argvs = [json.loads(line)['argv'] for line in claude_stub.read_text().splitlines()]
    installs = [
        argv
        for argv in argvs
        if argv[:3] == ['plugin', 'marketplace', 'add'] or argv[:2] == ['plugin', 'install']
    ]
    assert installs == [
        ['plugin', 'marketplace', 'add', str(repo), '--scope', 'user'],
        ['plugin', 'install', 'agentdev@shared', '--scope', 'user'],
        ['plugin', 'install', 'extra@shared', '--scope', 'user'],
    ]
    assert 'enabledPlugins' not in json.loads(
        (repo / '.claude' / 'settings.local.json').read_text()
    )
