"""Hook binaries on PATH report the versions mise.dev.toml declares."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import tomllib

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOLCHAIN = REPO_ROOT / 'mise.dev.toml'
VERSION_COMMANDS = {
    'gitleaks': ('gitleaks', ['version']),
    'actionlint': ('github:kjanat/actionlint', ['--version']),
}


def pinned(tool: str) -> str:
    return tomllib.loads(TOOLCHAIN.read_text())['tools'][tool].removeprefix('v')


@pytest.mark.parametrize('name', sorted(VERSION_COMMANDS))
def test_an_installed_hook_binary_matches_its_pin(name: str):
    binary = shutil.which(name)
    if binary is None:
        pytest.skip(f'{name} is not installed; the image smoke test requires it')
    tool, args = VERSION_COMMANDS[name]
    shown = subprocess.run([binary, *args], capture_output=True, text=True, check=True).stdout
    assert shown.splitlines()[0].split()[-1].removeprefix('v') == pinned(tool)
