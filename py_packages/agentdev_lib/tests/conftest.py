"""Shared fixtures for the agentdev-lib tests."""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

from lib_fixtures import SCRATCH_ROOT
import pytest


@pytest.fixture
def scratch() -> Path:
    """Create an isolated directory under /tmp, removed on teardown."""
    path = SCRATCH_ROOT / f'pytest-{uuid4().hex}'
    path.mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path)


@pytest.fixture
def unrelated_repository(scratch: Path) -> Path:
    """Create a git repository that shares nothing with the publisher checkout."""
    repository = scratch / 'unrelated-repository'
    repository.mkdir()
    subprocess.run(
        ['git', 'init', '--quiet', '--initial-branch=main'],
        cwd=repository,
        check=True,
        capture_output=True,
    )
    (repository / 'README.md').write_text('# Unrelated project\n', encoding='utf-8')
    return repository
