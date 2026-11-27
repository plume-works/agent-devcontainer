#!/usr/bin/env python3
"""Renovate's one post-upgrade task: see ADR-0050."""

from __future__ import annotations

import os
import subprocess
import sys

# Declares the iwe that the hooks and .iwe/ migrations run: see ADR-0111.
TOOLCHAIN = 'mise.toml'


def run(*command: str, check: bool = True) -> int:
    return subprocess.run(command, check=check).returncode


def changed_files() -> list[str]:
    """Return Renovate's uncommitted edits in its clone: the bump against HEAD."""
    tracked = subprocess.run(
        ['git', 'diff', '--name-only', '--diff-filter=d', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    untracked = subprocess.run(
        ['git', 'ls-files', '--others', '--exclude-standard'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    return [*tracked, *untracked]


def main() -> int:
    root = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'], check=True, capture_output=True, text=True
    ).stdout.strip()
    os.chdir(root)
    changed = changed_files()
    if not changed:
        return 0
    # The image carries the old iwe; the bumped one migrates .iwe/ and runs the hooks' `iwe`.
    locked: tuple[str, ...] = ()
    if TOOLCHAIN in changed:
        os.environ['MISE_TRUSTED_CONFIG_PATHS'] = root
        locked = ('mise', 'exec', '--locked', '--')
        run(*locked, 'iwe', 'normalize')
    # pre-commit through uv, not the image's copy: see ADR-0050.
    # Post-upgrade runs on the base branch; the guard is for commits.
    skip = os.environ.get('SKIP')
    os.environ['SKIP'] = f'{skip},no-commit-to-branch' if skip else 'no-commit-to-branch'
    pre_commit = (*locked, 'uv', 'run', '--frozen', 'pre-commit', 'run', '--files')
    if run(*pre_commit, *changed_files(), check=False):
        run(*pre_commit, *changed_files())
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
