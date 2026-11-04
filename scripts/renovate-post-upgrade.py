#!/usr/bin/env python3
"""Renovate's one post-upgrade task: see architecture/renovate-post-upgrade."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

# renovate: datasource=npm depName=@devcontainers/cli
DEVCONTAINER_CLI_VERSION = '0.90.0'
DEVCONTAINER_JSON = '.devcontainer/devcontainer.json'
DEV_TOOLS = 'ansible/roles/dev_tools/defaults/main.yml'


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
    run('uv', 'run', '--frozen', 'scripts/refresh-pin-checksums.py', *changed)
    if DEVCONTAINER_JSON in changed:
        run(
            'bunx',
            '--package',
            f'@devcontainers/cli@{DEVCONTAINER_CLI_VERSION}',
            'devcontainer',
            'upgrade',
            '--workspace-folder',
            '.',
        )
    iwe_dir = None
    try:
        # The image carries the old iwe; the pinned one migrates .iwe/ and serves the hooks below.
        if DEV_TOOLS in changed:
            Path('.tmp').mkdir(exist_ok=True)
            iwe_dir = './' + os.path.relpath(tempfile.mkdtemp(prefix='renovate-iwe.', dir='.tmp'))
            subprocess.run(
                ['uv', 'run', '--frozen', 'scripts/fetch-pinned-tool.py', 'iwe', iwe_dir],
                check=True,
                stdout=subprocess.DEVNULL,
            )
            os.environ['PATH'] = f'{os.path.realpath(iwe_dir)}:{os.environ["PATH"]}'
            run('iwe', 'normalize')
        # pre-commit through uv, not the image's apt copy: see architecture/renovate-post-upgrade.
        # Post-upgrade runs on the base branch; the guard is for commits: see spec/git-new-branch.
        skip = os.environ.get('SKIP')
        os.environ['SKIP'] = f'{skip},no-commit-to-branch' if skip else 'no-commit-to-branch'
        if run(
            'uv', 'run', '--frozen', 'pre-commit', 'run', '--files', *changed_files(), check=False
        ):
            run('uv', 'run', '--frozen', 'pre-commit', 'run', '--files', *changed_files())
    finally:
        if iwe_dir is not None:
            shutil.rmtree(iwe_dir, ignore_errors=True)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
