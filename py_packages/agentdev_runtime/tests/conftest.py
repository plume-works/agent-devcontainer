"""Shared fixtures: a recording ``claude`` stub and a made-up catalog repository."""

from collections.abc import Callable
import json
import os
from pathlib import Path
import subprocess

from agentdev_runtime import catalog
from agentdev_runtime.settings import DEVCONTAINER
import pytest

GIT_ID = ['-c', 'user.name=t', '-c', 'user.email=t@example.invalid']
STUB = """#!/usr/bin/env python3
import json, os, sys
argv = sys.argv[1:]
with open(os.environ['CLAUDE_STUB_LOG'], 'a') as log:
    log.write(json.dumps({'argv': argv, 'cwd': os.getcwd()}) + '\\n')
if argv[:3] == ['plugin', 'marketplace', 'list']:
    print(open(os.environ['CLAUDE_STUB_MARKETPLACES']).read())
fail = os.environ.get('CLAUDE_STUB_FAIL')
sys.exit(1 if fail and fail in ' '.join(argv) else 0)
"""


@pytest.fixture
def claude_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Put a recording ``claude`` on PATH and isolate HOME and the venv root."""
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    (bin_dir / 'claude').write_text(STUB)
    (bin_dir / 'claude').chmod(0o755)
    log = tmp_path / 'claude.log'
    log.touch()
    marketplaces = tmp_path / 'marketplaces.json'
    marketplaces.write_text('[]')
    (tmp_path / 'home').mkdir()
    (tmp_path / 'uv').mkdir()
    monkeypatch.setenv('PATH', f'{bin_dir}{os.pathsep}{os.environ["PATH"]}')
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    monkeypatch.setenv('CLAUDE_STUB_LOG', str(log))
    monkeypatch.setenv('CLAUDE_STUB_MARKETPLACES', str(marketplaces))
    monkeypatch.setenv('AGENTDEV_RUNTIME_MODE', DEVCONTAINER)
    monkeypatch.setenv('AGENTDEV_VENV_ROOT', str(tmp_path / 'uv' / 'venvs'))
    return log


def _make_repository(root: Path, *, with_catalog: bool) -> Path:
    root.mkdir()
    subprocess.run(['git', 'init', '-q', str(root)], check=True)
    if with_catalog:
        manifest = root / catalog.CLAUDE_MANIFEST
        manifest.parent.mkdir(parents=True)
        manifest.write_text(
            json.dumps(
                {
                    'name': 'shared',
                    'plugins': [
                        {'name': 'agentdev', 'source': './.agents/plugins/agentdev'},
                        {'name': 'extra', 'source': './.agents/plugins/extra'},
                    ],
                }
            )
        )
        (root / catalog.OPENCODE_BRIDGE).mkdir(parents=True)
        (root / catalog.OPENCODE_BRIDGE / 'keep').touch()
        subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True)
    subprocess.run(['git', *GIT_ID, '-C', str(root), 'commit', '-q', '--allow-empty', '-m', 'i'])
    local = root / '.claude' / 'settings.local.json'
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(json.dumps({'permissions': {'allow': ['Bash(ls:*)', 'Read']}}))
    return root


@pytest.fixture
def make_repository() -> Callable[..., Path]:
    """Return a builder for a repository, with or without a complete catalog."""
    return _make_repository
