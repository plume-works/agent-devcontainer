"""The standalone runtime registers the worktree hooks when it selects the checkout's catalog."""

from collections.abc import Callable
import json
from pathlib import Path

from agentdev_runtime import worktree
from agentdev_runtime.settings import Settings
from agentdev_runtime.workspace import Workspace
import pytest


@pytest.fixture
def config(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, claude_stub: Path) -> Path:
    """Point every client config at the test's own folders; return the Claude settings file."""
    staged = tmp_path / 'staged'
    staged.mkdir()
    monkeypatch.setenv('CLAUDE_CONFIG_DIR', str(tmp_path / 'claude'))
    monkeypatch.setenv('OPENCODE_CONFIG_DIR', str(tmp_path / 'opencode'))
    monkeypatch.setenv('AGENTDEV_STATE_DIR', str(tmp_path / 'state'))
    monkeypatch.setenv('AGENTDEV_CATALOG_DIR', str(staged))
    return tmp_path / 'claude' / 'settings.json'


def run_catalog(folder: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('DEV_WORKSPACE_FOLDER', str(folder))
    Workspace(Settings()).catalog()


def test_a_complete_checkout_catalog_registers_the_hooks(
    tmp_path: Path,
    config: Path,
    make_repository: Callable[..., Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_catalog(make_repository(tmp_path / 'repo', with_catalog=True), monkeypatch)
    hooks = json.loads(config.read_text())['hooks']
    assert {event: hooks[event][0]['hooks'][0]['command'] for event in hooks} == worktree.HOOKS


def test_the_staged_catalog_registers_no_hooks(
    tmp_path: Path,
    config: Path,
    make_repository: Callable[..., Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    run_catalog(make_repository(tmp_path / 'repo', with_catalog=False), monkeypatch)
    assert not config.exists() or 'hooks' not in json.loads(config.read_text())
