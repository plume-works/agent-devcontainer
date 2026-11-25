"""Tests for scripts/sync-agentdev-lib-pins.py run in made-up repository trees."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/sync-agentdev-lib-pins.py'


def plugin_pyproject(pin: str) -> str:
    """Return a plugin pyproject.toml that pins agentdev-lib at `pin`."""
    return (
        '[project]\nname = "fixture-plugin"\nversion = "0.0.0"\n'
        f'dependencies = ["agentdev-lib=={pin}"]\n\n[tool.uv]\npackage = false\n'
    )


@pytest.fixture
def tree() -> Iterator[Path]:
    """Yield a tree whose package is at version 2.3, with two plugins."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'sync-agentdev-lib-pins-{uuid4().hex}'
    package = root / 'py_packages/agentdev_lib'
    package.mkdir(parents=True)
    (package / 'pyproject.toml').write_text('[project]\nname = "agentdev-lib"\nversion = "2.3"\n')
    for plugin in ('first', 'second'):
        (root / '.agents/plugins' / plugin).mkdir(parents=True)
    yield root
    shutil.rmtree(root)


def run(tree: Path) -> subprocess.CompletedProcess[str]:
    """Run the hook from the root of `tree`."""
    return subprocess.run(
        [sys.executable, str(SCRIPT)], cwd=tree, capture_output=True, text=True, check=False
    )


def test_stale_pin_is_rewritten(tree: Path) -> None:
    """A pin that differs from the package version takes that version, and the hook fails."""
    stale = tree / '.agents/plugins/first/pyproject.toml'
    current = tree / '.agents/plugins/second/pyproject.toml'
    stale.write_text(plugin_pyproject('2.2'))
    current.write_text(plugin_pyproject('2.3'))

    completed = run(tree)

    assert completed.returncode == 1
    assert stale.read_text() == plugin_pyproject('2.3')
    assert current.read_text() == plugin_pyproject('2.3')
    assert completed.stdout == (
        '.agents/plugins/first/pyproject.toml: agentdev-lib==2.2 -> ==2.3\n'
    )


def test_matching_pins_are_left_alone(tree: Path) -> None:
    """When every pin matches, the hook changes no file and passes."""
    pyprojects = [tree / f'.agents/plugins/{name}/pyproject.toml' for name in ('first', 'second')]
    for pyproject in pyprojects:
        pyproject.write_text(plugin_pyproject('2.3'))
    before = {path: path.stat().st_mtime_ns for path in pyprojects}

    completed = run(tree)

    assert completed.returncode == 0
    assert completed.stdout == ''
    assert {path: path.stat().st_mtime_ns for path in pyprojects} == before
