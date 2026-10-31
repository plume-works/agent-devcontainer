"""The macOS bootstrap's pins track the image's release pins and the repository's Python floor."""

from __future__ import annotations

from pathlib import Path
import re
import tomllib

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
BOOTSTRAP = REPO_ROOT / '.agents/plugins/agentdev/bin/macos-bootstrap.zsh'
DEV_TOOLS = REPO_ROOT / 'ansible/roles/dev_tools/defaults/main.yml'
PYPROJECT = REPO_ROOT / 'pyproject.toml'


def recorded(name: str) -> str:
    """Return a ``typeset -r NAME=value`` constant the bootstrap records."""
    match = re.search(rf'^typeset -r {name}=(\S+)$', BOOTSTRAP.read_text(), re.MULTILINE)
    assert match, f'{name} is not recorded in {BOOTSTRAP.name}'
    return match.group(1)


def image_pin(tool: str) -> str:
    """Return the version ``dev_tools`` pins for one release tool."""
    tools = yaml.safe_load(DEV_TOOLS.read_text())['dev_tools_pinned_tools']
    return next(entry['version'] for entry in tools if entry['name'] == tool)


def test_iwe_matches_the_image_pin() -> None:
    assert recorded('IWE_VERSION') == image_pin('iwe')


def test_codebase_memory_mcp_matches_the_image_pin() -> None:
    assert recorded('CBM_VERSION') == image_pin('codebase-memory-mcp')


def test_python_is_the_requires_python_floor() -> None:
    requires = tomllib.loads(PYPROJECT.read_text())['project']['requires-python']
    floor = re.fullmatch(r'>=\s*(\d+\.\d+)', requires)
    assert floor, f'unexpected requires-python: {requires}'
    assert recorded('PYTHON_VERSION') == floor.group(1)
