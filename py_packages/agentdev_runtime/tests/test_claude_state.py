"""Claude's first-run prompts pre-answered for the workspace."""

import json
from pathlib import Path

from agentdev_runtime import claude_state
from agentdev_runtime.settings import Settings
import pytest


def settings(tmp_path: Path, **extra: str) -> Settings:
    return Settings(
        {
            'AGENTDEV_CLAUDE_STATE_PATH': str(tmp_path / '.claude.json'),
            'DEV_WORKSPACE_FOLDER': str(tmp_path / 'workspace'),
            **extra,
        }
    )


def test_state_and_project_settings_are_approved(tmp_path: Path) -> None:
    claude_state.preapprove(settings(tmp_path))
    state = json.loads((tmp_path / '.claude.json').read_text())
    assert state['hasCompletedOnboarding'] and state['remoteDialogSeen']
    assert state['projects'][str(tmp_path / 'workspace')]['hasTrustDialogAccepted']
    local = json.loads((tmp_path / 'workspace/.claude/settings.local.json').read_text())
    assert local == {'enableAllProjectMcpServers': True}


def test_a_symlinked_state_file_stays_a_symlink(tmp_path: Path) -> None:
    volume = tmp_path / 'volume.json'
    volume.write_text('{"keep": 1}')
    (tmp_path / '.claude.json').symlink_to(volume)
    claude_state.preapprove(settings(tmp_path))
    assert (tmp_path / '.claude.json').is_symlink()
    assert json.loads(volume.read_text())['keep'] == 1


def test_the_skip_variable_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    claude_state.preapprove(settings(tmp_path, AGENTDEV_SKIP_CLAUDE_PREAPPROVE='1'))
    assert not (tmp_path / '.claude.json').exists()
    assert 'skipping' in capsys.readouterr().out
