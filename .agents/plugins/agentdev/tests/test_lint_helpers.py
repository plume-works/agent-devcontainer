#!/usr/bin/env python3

"""Tests for the ruff check and ShellCheck fix entry points in bin/."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


def run_helper(
    plugin_root: Path, script: str, cwd: Path, *arguments: str, path: str
) -> subprocess.CompletedProcess[str]:
    """Run a bin/ helper with only the standard library and the given PATH."""
    return subprocess.run(
        [sys.executable, '-S', str(plugin_root / 'bin' / script), *arguments],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, 'PATH': path},
    )


def stub(directory: Path, name: str, body: str) -> None:
    """Write an executable shell stub that logs its arguments to <name>.log."""
    directory.mkdir(exist_ok=True)
    tool = directory / name
    tool.write_text(f'#!/bin/sh\necho "$@" >> "{directory}/{name}.log"\n{body}\n')
    tool.chmod(0o755)


def test_lint_check_runs_format_then_lint_on_the_targets(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Without uv or a .venv, ruff from PATH checks formatting and then lints."""
    stubs = plugin_tmp_path / 'stubs'
    stub(stubs, 'ruff', 'exit 0')

    completed = run_helper(
        plugin_root, 'python_lint_check.py', plugin_tmp_path, 'a.py', path=str(stubs)
    )

    assert completed.returncode == 0
    assert (stubs / 'ruff.log').read_text().splitlines() == [
        'format --check --quiet a.py',
        'check --quiet a.py',
    ]


def test_lint_check_stops_at_a_format_failure(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A formatting violation exits with ruff's status without running the lint pass."""
    stubs = plugin_tmp_path / 'stubs'
    stub(stubs, 'ruff', 'exit 1')

    completed = run_helper(
        plugin_root, 'python_lint_check.py', plugin_tmp_path, 'a.py', path=str(stubs)
    )

    assert completed.returncode == 1
    assert len((stubs / 'ruff.log').read_text().splitlines()) == 1


def test_lint_check_without_ruff_fails(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """With no ruff anywhere the check must exit 1 naming the remedy."""
    empty = plugin_tmp_path / 'empty'
    empty.mkdir()

    completed = run_helper(plugin_root, 'python_lint_check.py', plugin_tmp_path, path=str(empty))

    assert completed.returncode == 1
    assert completed.stderr == "ruff not found: run 'uv sync', or invoke via 'uv run'.\n"


@pytest.mark.skipif(shutil.which('shellcheck') is None, reason='needs shellcheck')
def test_shellcheck_fix_applies_fixes_outside_pruned_trees(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Scripts are fixed in place; vendor, .venv*, and .tmp trees are left alone."""
    tree = plugin_tmp_path / 'tree'
    unquoted = '#!/bin/bash\necho $1\n'
    for relative in ('top.sh', 'a/upper.SH', 'a/vendor/v.sh', '.venv-x/v.sh', '.tmp/t.sh'):
        script = tree / relative
        script.parent.mkdir(parents=True, exist_ok=True)
        script.write_text(unquoted)
    subprocess.run(['git', 'init', '--quiet'], cwd=tree, check=True)
    tools = ':'.join(
        str(Path(found).parent) for found in (shutil.which('shellcheck'), shutil.which('git'))
    )

    completed = run_helper(plugin_root, 'shellcheck_fix.py', tree, path=tools)

    assert completed.returncode == 0, completed.stderr
    quoted = '#!/bin/bash\necho "$1"\n'
    assert (tree / 'top.sh').read_text() == quoted
    assert (tree / 'a/upper.SH').read_text() == quoted
    for pruned in ('a/vendor/v.sh', '.venv-x/v.sh', '.tmp/t.sh'):
        assert (tree / pruned).read_text() == unquoted
    assert sorted(path.name for path in (tree / '.tmp').iterdir()) == ['t.sh']
