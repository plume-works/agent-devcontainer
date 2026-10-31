"""Hook registration warns about each system hook whose executable is not on PATH."""

import os
from pathlib import Path
import subprocess

from agentdev_runtime import project
from agentdev_runtime.settings import DEPLOY, DEVCONTAINER, Settings
import pytest

CONFIG = """repos:
  - repo: local
    hooks:
      - id: gitleaks
        name: Detect hardcoded secrets
        entry: gitleaks git --pre-commit --staged
        language: system
      - id: python-hook
        name: Not a system hook
        entry: absent-python-tool
        language: python
"""


@pytest.fixture
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Make a Git checkout with a pre-commit config, on a PATH with only a fake pre-commit."""
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    subprocess.run(['git', 'init', '-q', str(workspace)], check=True)
    (workspace / '.pre-commit-config.yaml').write_text(CONFIG)
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    fake = bin_dir / 'pre-commit'
    fake.write_text('#!/bin/sh\nexit 0\n')
    fake.chmod(0o755)
    git_dir = Path(subprocess.run(['which', 'git'], capture_output=True, text=True).stdout).parent
    monkeypatch.setenv('PATH', f'{bin_dir}:{git_dir}')
    monkeypatch.setenv('HOME', str(tmp_path))
    return workspace


def settings_for(workspace: Path, mode: str) -> Settings:
    return Settings(
        {**os.environ, 'AGENTDEV_RUNTIME_MODE': mode, 'DEV_WORKSPACE_FOLDER': str(workspace)}
    )


@pytest.mark.parametrize('mode', [DEVCONTAINER, DEPLOY])
def test_a_missing_system_hook_executable_warns_and_keeps_the_status(
    checkout: Path, mode: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert project.hooks(settings_for(checkout, mode)) == 0
    err = capsys.readouterr().err
    assert 'hook gitleaks runs gitleaks, which is not on PATH' in err
    assert 'absent-python-tool' not in err


@pytest.mark.parametrize('mode', [DEVCONTAINER, DEPLOY])
def test_a_present_executable_draws_no_warning(
    checkout: Path, mode: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    gitleaks = tmp_path / 'bin/gitleaks'
    gitleaks.write_text('#!/bin/sh\nexit 0\n')
    gitleaks.chmod(0o755)
    assert project.hooks(settings_for(checkout, mode)) == 0
    assert 'not on PATH' not in capsys.readouterr().err


def test_deploy_keeps_failing_on_a_custom_hook_without_warning(
    checkout: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (checkout / '.git/hooks/pre-push').write_text('#!/bin/sh\necho mine\n')
    assert project.hooks(settings_for(checkout, DEPLOY)) == 1
    assert 'not on PATH' not in capsys.readouterr().err


def test_an_unreadable_config_lists_nothing(tmp_path: Path) -> None:
    config = tmp_path / '.pre-commit-config.yaml'
    config.write_text('repos: [unclosed')
    assert project.missing_executables(config) == []
