"""
Claude Code's ``WorktreeCreate`` hook: a worktree with its own uv environment.

Hook contract: architecture/worktree-hooks. Spec: agentdev-runtime-images.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys

from agentdev_runtime import project, settings as env

PREFIX = 'agentdev-runtime worktree'


def fail(message: str) -> int:
    print(f'{PREFIX}: {message}', file=sys.stderr)
    return 1


def git(*args: str) -> int:
    """Run git with its output on stderr, which Claude Code does not read as the path."""
    return subprocess.run(['git', *args], stdout=2, check=False).returncode


def create(text: str) -> int:
    """Create ``.claude/worktrees/<name>`` on ``worktree-<name>``, link its ``.venv``, print it."""
    try:
        request = json.loads(text)
        cwd, name = str(request['cwd']), str(request['name'])
    except (ValueError, KeyError, TypeError) as error:
        return fail(f'unreadable hook input: {error}')
    top = subprocess.run(
        ['git', '-C', cwd, 'rev-parse', '--show-toplevel'],
        capture_output=True,
        text=True,
        check=False,
    )
    if top.returncode != 0:
        return fail(f'{cwd} is not in a git repository: {top.stderr.strip()}')
    repository = top.stdout.strip()
    safe = re.sub(r'[^A-Za-z0-9._-]', '-', name)
    if not safe.strip('.'):
        return fail(f'worktree name {name!r} has no usable characters')
    path = Path(repository, '.claude', 'worktrees', safe)
    branch = f'worktree-{safe}'
    if git('-C', repository, 'worktree', 'add', '-b', branch, str(path), 'HEAD') != 0:
        return fail(f'git worktree add {path} failed')
    try:
        project.link_venv(env.Settings(), path)
    except OSError as error:
        git('-C', repository, 'worktree', 'remove', '--force', str(path))
        git('-C', repository, 'branch', '-D', branch)
        return fail(f'linking the uv environment of {path} failed: {error}')
    print(path)
    return 0


def main(argv: list[str]) -> int:
    if argv == ['create']:
        return create(sys.stdin.read())
    print(f'usage: {PREFIX} create', file=sys.stderr)
    return 2
