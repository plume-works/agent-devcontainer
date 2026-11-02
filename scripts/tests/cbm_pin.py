"""Stage the codebase-memory-mcp binary the image pins, for tests that run the real thing."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from scratch import TMP_ROOT
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
DEV_TOOLS = REPO_ROOT / 'ansible/roles/dev_tools/defaults/main.yml'


def pinned_version() -> str:
    """Return the CBM version the image ships, without its leading ``v``."""
    tools = yaml.safe_load(DEV_TOOLS.read_text())['dev_tools_pinned_tools']
    return next(t['version'] for t in tools if t['name'] == 'codebase-memory-mcp').lstrip('v')


def binary_version(path: Path) -> str:
    """Return the version a CBM binary reports."""
    output = subprocess.run([path, '--version'], capture_output=True, text=True, check=True)
    return output.stdout.split()[-1]


def stage_pinned_cbm() -> Path:
    """
    Stage the pinned CBM binary under /tmp, copying the image's when it matches the pin.

    The isolated account cannot traverse the invoking user's home, where the image installs it.
    xdist workers share the path, so a binary is staged aside and renamed into place: writing over
    one another worker is executing fails with ETXTBSY.
    """
    version = pinned_version()
    destination = TMP_ROOT / f'cbm-pin-{version}'
    binary = destination / 'codebase-memory-mcp'
    if binary.exists() and binary_version(binary) == version:
        return binary
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination) as staging:
        staged = Path(staging) / binary.name
        installed = shutil.which('codebase-memory-mcp')
        if installed and binary_version(Path(installed)) == version:
            shutil.copy2(installed, staged)
        else:
            subprocess.run(
                [
                    sys.executable,
                    REPO_ROOT / 'scripts/fetch-pinned-tool.py',
                    'codebase-memory-mcp',
                    staging,
                    '--repo-root',
                    REPO_ROOT,
                ],
                check=True,
            )
        os.replace(staged, binary)
    return binary
