#!/usr/bin/env python3

"""
Verify Python style compliance with ruff (the CI gate).

The pre-commit hooks, locally and in CI, apply ruff's formatter and autofixes;
this is the non-mutating check, so it is safe to run anywhere and needs no
Docker. Nothing here installs or upgrades packages.

Usage:
  python_lint_check.py [PATH ...]

With no arguments this checks the whole repository (ruff honors .gitignore and
its own default excludes). Pass explicit paths to scope the check. Exits
non-zero when ruff reports any violation. Standard library only.
"""

from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys


def repository_root() -> Path:
    """Return the working directory's repository top level, or the directory itself."""
    try:
        completed = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'], check=False, capture_output=True, text=True
        )
    except OSError:
        return Path.cwd()
    return Path(completed.stdout.strip()) if completed.returncode == 0 else Path.cwd()


def resolve_ruff(root: Path) -> list[str] | None:
    """Return the ruff command: the uv project's, an in-tree .venv's, then PATH's."""
    # --no-sync keeps this a check: a mid-edit pyproject.toml must not install packages.
    uv_ruff = ['uv', 'run', '--no-sync', '--project', str(root), 'ruff']
    if shutil.which('uv') is not None:
        probe = subprocess.run([*uv_ruff, '--version'], check=False, capture_output=True)
        if probe.returncode == 0:
            return uv_ruff
    venv_ruff = root / '.venv' / 'bin' / 'ruff'
    if venv_ruff.is_file() and venv_ruff.stat().st_mode & 0o111:
        return [str(venv_ruff)]
    if shutil.which('ruff') is not None:
        return ['ruff']
    return None


def main(arguments: list[str]) -> int:
    """Run ruff's format check, then its lint check, on the targets."""
    if arguments in (['-h'], ['--help']):
        print(__doc__.strip())
        return 0
    root = repository_root()
    targets = arguments or [str(root)]
    ruff = resolve_ruff(root)
    if ruff is None:
        print("ruff not found: run 'uv sync', or invoke via 'uv run'.", file=sys.stderr)
        return 1
    formatted = subprocess.run([*ruff, 'format', '--check', '--quiet', *targets], check=False)
    if formatted.returncode != 0:
        return formatted.returncode
    return subprocess.run([*ruff, 'check', '--quiet', *targets], check=False).returncode


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
