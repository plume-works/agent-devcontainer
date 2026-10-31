"""A phase's image hooks: name order, executables only, containment, and failure."""

from pathlib import Path

from agentdev_runtime import hooks
from agentdev_runtime.settings import Settings
import pytest


def write_hook(directory: Path, name: str, body: str, executable: bool = True) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / name
    path.write_text(f'#!/bin/sh\n{body}\n')
    path.chmod(0o755 if executable else 0o644)


def settings(root: Path, workspace: Path) -> Settings:
    return Settings({'AGENTDEV_HOOKS_ROOT': str(root), 'DEV_WORKSPACE_FOLDER': str(workspace)})


def test_hooks_run_in_byte_order_with_their_phase(tmp_path: Path) -> None:
    log = tmp_path / 'log'
    phase = tmp_path / 'hooks/started.d'
    for name in ('b', 'A', '10'):
        write_hook(phase, name, f'echo "{name} $AGENTDEV_LIFECYCLE_PHASE" >> {log}')
    write_hook(phase, 'README', 'exit 9', executable=False)
    hooks.run(settings(tmp_path / 'hooks', tmp_path / 'ws'), 'started')
    assert log.read_text().splitlines() == ['10 started', 'A started', 'b started']


def test_a_failing_hook_stops_the_phase(tmp_path: Path) -> None:
    write_hook(tmp_path / 'hooks/created.d', '10-broken', 'exit 7')
    with pytest.raises(
        hooks.HookError, match=r'10-broken failed in the created phase \(exit status 7\)'
    ):
        hooks.run(settings(tmp_path / 'hooks', tmp_path / 'ws'), 'created')


def test_a_hook_root_inside_the_workspace_is_refused(tmp_path: Path) -> None:
    workspace = tmp_path / 'ws'
    write_hook(workspace / 'hooks/attached.d', 'x', 'exit 0')
    with pytest.raises(hooks.HookError, match='is inside the workspace'):
        hooks.run(settings(workspace / 'hooks', workspace), 'attached')


def test_a_missing_phase_directory_runs_nothing(tmp_path: Path) -> None:
    hooks.run(settings(tmp_path / 'absent', tmp_path / 'ws'), 'attached')


def test_an_unknown_phase_is_a_usage_error() -> None:
    assert hooks.main(['deployed']) == 2
