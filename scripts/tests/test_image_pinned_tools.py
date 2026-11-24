"""Pinned hook binaries in the image report the versions pinned-tools.yml pins."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
PINNED_TOOLS = REPO_ROOT / 'docker/devcontainer/pinned-tools.yml'
VERSION_COMMANDS = {'gitleaks': ['version'], 'actionlint': ['--version']}


def pinned(name: str) -> str:
    tools = yaml.safe_load(PINNED_TOOLS.read_text())['tools']
    return next(t['version'] for t in tools if t['name'] == name).removeprefix('v')


@pytest.mark.parametrize('name', sorted(VERSION_COMMANDS))
def test_an_installed_hook_binary_matches_its_pin(name: str):
    binary = shutil.which(name)
    if binary is None:
        pytest.skip(f'{name} is not installed; the image smoke test requires it')
    shown = subprocess.run(
        [binary, *VERSION_COMMANDS[name]], capture_output=True, text=True, check=True
    ).stdout
    assert shown.splitlines()[0].split()[-1].removeprefix('v') == pinned(name)
