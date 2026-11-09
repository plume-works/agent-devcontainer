"""`project sync` in a Dev Container links the checkout's `.venv` before `uv sync`."""

import os
from pathlib import Path
import subprocess

from agentdev_runtime import project
from agentdev_runtime.settings import DEVCONTAINER, Settings
import pytest


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Make a Git checkout, on a PATH whose `uv` records how it was called."""
    workspace = tmp_path / 'checkout'
    workspace.mkdir()
    subprocess.run(['git', 'init', '-q', str(workspace)], check=True)
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    uv = bin_dir / 'uv'
    uv.write_text(f'#!/bin/sh\necho "$(readlink .venv) $*" >> "{tmp_path}/uv.log"\n')
    uv.chmod(0o755)
    monkeypatch.setenv('PATH', f'{bin_dir}:{os.environ["PATH"]}')
    return workspace


def settings_for(checkout: Path) -> Settings:
    root = checkout.parent / 'uv' / 'venvs'
    root.parent.mkdir(parents=True, exist_ok=True)
    return Settings(
        {
            **os.environ,
            'AGENTDEV_RUNTIME_MODE': DEVCONTAINER,
            'AGENTDEV_VENV_ROOT': str(root),
            'DEV_WORKSPACE_FOLDER': str(checkout),
        }
    )


def uv_calls(checkout: Path) -> list[str]:
    return (checkout.parent / 'uv.log').read_text().splitlines()


def test_sync_runs_in_the_linked_environment(checkout: Path) -> None:
    assert project.sync(settings_for(checkout)) == 0
    target = checkout.parent / 'uv' / 'venvs' / 'checkout'
    assert uv_calls(checkout) == [f'{target} sync --all-groups --all-extras']


def test_a_real_uv_environment_is_replaced_by_the_link(checkout: Path) -> None:
    (checkout / '.venv' / 'bin').mkdir(parents=True)
    (checkout / '.venv' / 'pyvenv.cfg').write_text('home = /usr/bin\n')
    assert project.sync(settings_for(checkout)) == 0
    assert (checkout / '.venv').is_symlink()


def test_another_real_venv_is_left_with_a_warning(
    checkout: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (checkout / '.venv').mkdir()
    (checkout / '.venv' / 'notes.txt').write_text('mine\n')
    assert project.sync(settings_for(checkout)) == 0
    assert (checkout / '.venv' / 'notes.txt').read_text() == 'mine\n'
    assert 'not a link' in capsys.readouterr().err
