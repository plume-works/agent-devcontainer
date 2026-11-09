"""The create phase registers the worktree hooks in the user's Claude settings."""

import json
import os
from pathlib import Path

from agentdev_runtime import lifecycle, worktree
from agentdev_runtime.settings import DEPLOY, DEVCONTAINER, Settings
import pytest

UNRELATED = {
    'model': 'opus',
    'hooks': {
        'WorktreeCreate': [{'hooks': [{'type': 'command', 'command': 'mine create'}]}],
        'Stop': [{'hooks': [{'type': 'command', 'command': 'notify'}]}],
    },
}


@pytest.fixture
def config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / 'claude'
    monkeypatch.setenv('CLAUDE_CONFIG_DIR', str(directory))
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    monkeypatch.setenv('GIT_CONFIG_GLOBAL', str(tmp_path / 'gitconfig'))
    return directory / 'settings.json'


def commands(settings_file: Path, event: str) -> list[str]:
    groups = json.loads(settings_file.read_text())['hooks'][event]
    return [hook['command'] for group in groups for hook in group['hooks']]


def test_registering_twice_adds_each_hook_once_and_keeps_the_rest(config: Path) -> None:
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps(UNRELATED))
    worktree.register()
    worktree.register()
    data = json.loads(config.read_text())
    assert data['model'] == 'opus'
    assert commands(config, 'Stop') == ['notify']
    assert commands(config, 'WorktreeCreate') == [
        'mine create',
        'agentdev-runtime worktree create',
    ]
    assert commands(config, 'WorktreeRemove') == ['agentdev-runtime worktree remove']


@pytest.mark.parametrize(('mode', 'registered'), [(DEVCONTAINER, True), (DEPLOY, False)])
def test_the_create_phase_registers_the_hooks_outside_deploy_mode(
    config: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, registered: bool
) -> None:
    folder = tmp_path / 'checkout'
    folder.mkdir()
    monkeypatch.setattr(lifecycle, 'claim_mounts', lambda owner: None)
    monkeypatch.setattr(lifecycle.git, 'safe_directory', lambda settings: None)
    monkeypatch.setattr(lifecycle.agent_state, 'create', lambda settings: None)
    monkeypatch.setattr(lifecycle.checkout.Workspace, 'project', lambda self: None)
    settings = Settings(
        {
            **os.environ,
            'AGENTDEV_RUNTIME_MODE': mode,
            'DEV_WORKSPACE_FOLDER': str(folder),
            'AGENTDEV_HOOKS_ROOT': str(tmp_path / 'no-hooks'),
            'AGENTDEV_LIFECYCLE_DIR': str(tmp_path / 'lifecycle'),
            'AGENTDEV_CATALOG_DIR': '',
        }
    )
    lifecycle.created(settings)
    assert config.exists() == registered
