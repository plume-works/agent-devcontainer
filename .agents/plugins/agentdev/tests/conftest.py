#!/usr/bin/env python3

"""
Shared fixtures for the plugin's own script tests.

These tests exercise the scripts this plugin ships — the helpers in ``bin/`` and
the ``scripts/`` bundled with individual skills. They resolve everything from the
plugin root so the suite runs unchanged from a consumer's plugin cache, where the
repository that develops the plugin is not present.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest


@pytest.fixture
def plugin_root() -> Path:
    """Resolve the plugin root that ships the scripts under test."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture
def plugin_tmp_path(plugin_root: Path):
    """Create an isolated temporary directory under /tmp."""
    temp_path = Path('/tmp/agentdev-tests') / f'pytest-{uuid4().hex}'
    temp_path.mkdir(parents=True)
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path)


@pytest.fixture
def installed_iwe_bootstrap(plugin_root: Path, plugin_tmp_path: Path) -> Path:
    """Copy the bootstrap skill and shared `bin/` into an isolated plugin layout."""
    installed = plugin_tmp_path / 'installed-plugin'
    shutil.copytree(plugin_root / 'bin', installed / 'bin')
    shutil.copytree(
        plugin_root / 'skills' / 'iwe-bootstrap',
        installed / 'skills' / 'iwe-bootstrap',
        symlinks=True,
    )
    return installed / 'skills' / 'iwe-bootstrap'


@pytest.fixture
def unrelated_repository(plugin_tmp_path: Path) -> Path:
    """Create a git repository that shares nothing with the publisher checkout."""
    repository = plugin_tmp_path / 'unrelated-repository'
    repository.mkdir()
    subprocess.run(
        ['git', 'init', '--quiet', '--initial-branch=main'],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    (repository / 'README.md').write_text('# Unrelated project\n', encoding='utf-8')
    return repository
