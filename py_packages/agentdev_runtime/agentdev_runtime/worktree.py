"""
Claude Code's ``WorktreeCreate`` and ``WorktreeRemove`` hooks: a worktree with its own uv environment.

Hook contract: architecture/worktree-hooks. Spec: agentdev-runtime-images.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from agentdev_runtime import claude_state, project, remote_control, settings as env

PREFIX = 'agentdev-runtime worktree'
HOOKS = {
    'WorktreeCreate': 'agentdev-runtime worktree create',
    'WorktreeRemove': 'agentdev-runtime worktree remove',
}


def fail(message: str) -> int:
    print(f'{PREFIX}: {message}', file=sys.stderr)
    return 1


def git(*args: str) -> int:
    """Run git with its output on stderr, which Claude Code does not read as the path."""
    return subprocess.run(['git', *args], stdout=2, check=False).returncode


def worktrees(repository: str) -> set[Path]:
    listed = subprocess.run(
        ['git', '-C', repository, 'worktree', 'list', '--porcelain'],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        Path(line.removeprefix('worktree '))
        for line in listed.stdout.splitlines()
        if line.startswith('worktree ')
    }


def create(text: str) -> int:
    """Make or reuse ``.claude/worktrees/<name>`` on ``worktree-<name>``, link its ``.venv``."""
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
    reused = path in worktrees(repository)
    new_branch = (
        not reused
        and git('-C', repository, 'rev-parse', '--verify', '-q', f'refs/heads/{branch}') != 0
    )
    if not reused:
        add = ['-b', branch, str(path), 'HEAD'] if new_branch else [str(path), branch]
        if git('-C', repository, 'worktree', 'add', *add) != 0:
            if new_branch:
                git('-C', repository, 'branch', '-D', branch)
            return fail(f'git worktree add {path} failed')
    try:
        project.link_venv(env.Settings(), path)
    except OSError as error:
        if not reused:
            git('-C', repository, 'worktree', 'remove', '--force', str(path))
        if new_branch:
            git('-C', repository, 'branch', '-D', branch)
        return fail(f'linking the uv environment of {path} failed: {error}')
    print(path)
    return 0


def remove(text: str) -> int:
    """Delete the worktree's uv environment, then the worktree; its branch stays."""
    try:
        path = Path(str(json.loads(text)['worktree_path']))
    except (ValueError, KeyError, TypeError) as error:
        return fail(f'unreadable hook input: {error}')
    if not path.exists():
        return 0
    root = Path(os.path.abspath(env.Settings().get('AGENTDEV_VENV_ROOT')))
    target = project.linked(path)
    if target and project.within(root, target) and target != root and target.is_dir():
        shutil.rmtree(target)
        (root / f'{target.name}.checkout').unlink(missing_ok=True)
    if git('-C', str(path), 'worktree', 'remove', '--force', str(path)) != 0:
        return fail(f'git worktree remove {path} failed')
    return 0


def register() -> None:
    """Add both hooks to the user's Claude settings, keeping every other hook and key."""

    def add(data: dict) -> None:
        events = data.setdefault('hooks', {})
        for event, command in HOOKS.items():
            groups = events.setdefault(event, [])
            hooks = [hook for group in groups for hook in group.get('hooks', [])]
            if not any(hook.get('command') == command for hook in hooks):
                groups.append({'hooks': [{'type': 'command', 'command': command}]})

    claude_state.update_json(remote_control.config_dir() / 'settings.json', add)


def main(argv: list[str]) -> int:
    if argv == ['create']:
        return create(sys.stdin.read())
    if argv == ['remove']:
        return remove(sys.stdin.read())
    print(f'usage: {PREFIX} create|remove', file=sys.stderr)
    return 2
