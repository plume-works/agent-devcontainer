"""
Claude Code's ``WorktreeCreate`` and ``WorktreeRemove`` hooks.

Each worktree they make gets its own uv environment and, in a catalog checkout, its own catalog.

Hook contract: architecture/worktree-hooks. Spec: agentdev-runtime-images, catalog-lifecycle.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from agentdev_runtime import (
    agent_state,
    catalog,
    claude_state,
    project,
    remote_control,
    settings as env,
)

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


def claude(cwd: Path | str, *args: str) -> None:
    """Run a ``claude`` command with its output on stderr; a failure raises ``CatalogError``."""
    result = subprocess.run(['claude', *args], cwd=cwd, stdout=2, check=False)
    if result.returncode != 0:
        raise catalog.CatalogError(f'claude {" ".join(args)} exited {result.returncode}')


def marketplace(path: Path) -> str:
    return f'wt-{path.name}'


def marketplace_file(path: Path) -> Path:
    return path / '.claude' / 'marketplace.local.json'


def registered_file(path: Path) -> str | None:
    """Return the file ``wt-<name>`` is registered from, or ``None`` when it is not registered."""
    name = marketplace(path)
    for entry in catalog.listing('claude', 'plugin', 'marketplace', 'list', '--json'):
        if isinstance(entry, dict) and entry.get('name') == name:
            return entry.get('path')
    return None


def main_checkout(repository: str) -> Path:
    common = subprocess.run(
        ['git', '-C', repository, 'rev-parse', '--path-format=absolute', '--git-common-dir'],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(common.stdout.strip()).parent


def copy_permissions(main: Path, path: Path) -> None:
    """Merge the main checkout's local ``permissions.allow`` into the worktree's."""
    source = main / '.claude' / 'settings.local.json'
    try:
        allowed = json.loads(source.read_text()).get('permissions', {}).get('allow', [])
    except FileNotFoundError:
        return
    if not allowed:
        return

    def merge(data: dict) -> None:
        rules = data.setdefault('permissions', {}).setdefault('allow', [])
        rules.extend(rule for rule in allowed if rule not in rules)

    claude_state.update_json(path / '.claude' / 'settings.local.json', merge)


def install_catalog(main: Path, path: Path) -> None:
    """Install the worktree's own catalog as ``wt-<name>`` and turn the shared one off there."""
    manifest = catalog.read_manifest(path / catalog.CLAUDE_MANIFEST)
    shared, name = manifest['name'], marketplace(path)
    plugins = [plugin['name'] for plugin in manifest.get('plugins') or []]
    local = marketplace_file(path)
    owner = registered_file(path)
    if owner not in (None, str(local)):
        raise catalog.CatalogError(f'{name} is already registered from {owner}')
    local.parent.mkdir(parents=True, exist_ok=True)
    local.write_text(json.dumps({**manifest, 'name': name}, indent=2) + '\n')
    ours = [f'{plugin}@{name}' for plugin in plugins]

    def unclaim(data: dict) -> None:
        for key in ours:
            data.get('enabledPlugins', {}).pop(key, None)

    # Run in a worktree, a local-scope install enables the plugin in the main checkout's
    # local settings, which every worktree reads: architecture/per-worktree-catalog.
    try:
        claude(path, 'plugin', 'marketplace', 'add', str(local))
        for key in ours:
            claude(path, 'plugin', 'install', key, '--scope', 'local')
    finally:
        if (main / '.claude' / 'settings.local.json').is_file():
            claude_state.update_json(main / '.claude' / 'settings.local.json', unclaim)

    def enable(data: dict) -> None:
        enabled = data.setdefault('enabledPlugins', {})
        enabled.update({f'{plugin}@{shared}': False for plugin in plugins})
        enabled.update(dict.fromkeys(ours, True))

    claude_state.update_json(path / '.claude' / 'settings.local.json', enable)


def uninstall_catalog(path: Path) -> None:
    """Remove this worktree's ``wt-<name>`` marketplace, which also uninstalls its plugins."""
    if registered_file(path) == str(marketplace_file(path)):
        claude('/', 'plugin', 'marketplace', 'remove', marketplace(path))


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

    def undo() -> None:
        if not reused:
            git('-C', repository, 'worktree', 'remove', '--force', str(path))
        if new_branch:
            git('-C', repository, 'branch', '-D', branch)

    settings = env.Settings()
    try:
        project.link_venv(settings, path)
    except OSError as error:
        undo()
        return fail(f'linking the uv environment of {path} failed: {error}')
    try:
        main = main_checkout(repository)
        copy_permissions(main, path)
        if catalog.complete(path):
            with agent_state.config_lock(settings):
                install_catalog(main, path)
    except (
        OSError,
        ValueError,
        subprocess.CalledProcessError,
        catalog.CatalogError,
        agent_state.StateError,
    ) as error:
        try:
            uninstall_catalog(path)
        except catalog.CatalogError as cleanup:
            print(f'{PREFIX}: {cleanup}', file=sys.stderr)
        undo()
        return fail(f'setting up {path} failed: {error}')
    print(path)
    return 0


def remove(text: str) -> int:
    """Drop the worktree's catalog and uv environment, then the worktree; its branch stays."""
    try:
        path = Path(str(json.loads(text)['worktree_path']))
    except (ValueError, KeyError, TypeError) as error:
        return fail(f'unreadable hook input: {error}')
    settings = env.Settings()
    try:
        with agent_state.config_lock(settings):
            uninstall_catalog(path)
    except (catalog.CatalogError, agent_state.StateError) as error:
        return fail(f'removing the catalog of {path} failed: {error}')
    if not path.exists():
        return 0
    root = Path(os.path.abspath(settings.get('AGENTDEV_VENV_ROOT')))
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
