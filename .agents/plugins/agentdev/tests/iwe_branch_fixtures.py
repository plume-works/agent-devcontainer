#!/usr/bin/env python3

"""Shared mock world for the iwe-branch-name script tests: a remote, clones, and plans."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

from git_fixtures import FIXTURE_ENV, git

SCRIPT = 'skills/iwe-branch-name/agent-code/iwe-branch-name.py'
LIBRARY = 'notes'
PLAN_KEY = 'data/plans/20250102-focus-timer'
PLAN_SLUG = 'focus-timer'


def plan_document(stage: str = '', ticks: tuple[bool, ...] = (True, False)) -> str:
    """Return a made-up plan whose task checkboxes are ticked as `ticks` says."""
    stage_line = f'stage: {stage}\n' if stage else ''
    boxes = ''.join(f'- [{"x" if ticked else " "}] Task {n}\n' for n, ticked in enumerate(ticks))
    return (
        f'---\ntype: plan\n{stage_line}created: 2025-01-02\n---\n\n# Focus timer\n\n'
        f'## Implementation Steps\n\n### Task 1\n\n{boxes}\n'
        '## Verification\n\n- [ ] not a task checkbox\n'
    )


def commit_file(repository: Path, relative: str, content: str) -> None:
    """Write `relative` in `repository` and commit it."""
    target = repository / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    git(repository, 'add', relative)
    git(repository, 'commit', '-m', f'write {relative}')


class Workspace:
    """A bare remote, a publisher clone that advances it, and a working clone."""

    def __init__(self, root: Path, plans: dict[str, str] | None = None) -> None:
        self.root = root
        seed = root / 'seed'
        seed.mkdir()
        git(seed, 'init', '--initial-branch=main')
        commit_file(seed, '.iwe/config.toml', f'version = 4\n\n[workspace]\npath = "{LIBRARY}"\n')
        for key, document in (plans if plans is not None else {PLAN_KEY: plan_document()}).items():
            commit_file(seed, f'{LIBRARY}/{key}.md', document)
        self.remote = root / 'remote.git'
        git(root, 'clone', '--bare', str(seed), str(self.remote))
        self.work = root / 'work'
        git(root, 'clone', str(self.remote), str(self.work))
        self.publisher = root / 'publisher'
        git(root, 'clone', str(self.remote), str(self.publisher))

    def publish(self, key: str, document: str) -> None:
        """Commit a plan on the remote default branch behind the working clone's back."""
        commit_file(self.publisher, f'{LIBRARY}/{key}.md', document)
        git(self.publisher, 'push', 'origin', 'main')

    def push_branch(self, branch: str) -> None:
        """Create `branch` on the remote only."""
        git(self.publisher, 'push', 'origin', f'HEAD:refs/heads/{branch}')


def run_script(
    plugin_root: Path, cwd: Path, *args: str, path_prefix: Path | None = None
) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    """Run iwe-branch-name.py and parse its key=value stdout."""
    env = {**os.environ, **FIXTURE_ENV}
    if path_prefix is not None:
        env['PATH'] = f'{path_prefix}{os.pathsep}{env["PATH"]}'
    completed = subprocess.run(
        [str(plugin_root / SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    values = dict(line.split('=', 1) for line in completed.stdout.splitlines() if '=' in line)
    return completed, values
