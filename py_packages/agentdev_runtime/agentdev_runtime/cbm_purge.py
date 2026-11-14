"""
Clear what ``codebase-memory-mcp install`` left in persisted agent configuration.

Its hooks and MCP entries outlive the binary in the home and ``~/.claude`` volumes, where they
would fail on every tool call. Every step is idempotent. See ADR-0047.
"""

from __future__ import annotations

from collections.abc import Callable
import json
import os
from pathlib import Path
import re
import shutil
import sys
from typing import Any

from agentdev_runtime import claude_state, opencode_config, settings as env

BINARY = 'codebase-memory-mcp'
HOOK_COMMAND = re.compile(rf'{BINARY}|/hooks/cbm-')
MANAGED_BLOCK = re.compile(
    rf'^[^\n]*{BINARY}:start.*?^[^\n]*{BINARY}:end[^\n]*\n?', re.DOTALL | re.MULTILINE
)
AGENTS = ('codebase-memory.md', 'codebase-memory-scout.md', 'codebase-memory-auditor.md')


def strip_hooks(settings: dict[str, Any]) -> bool:
    """Drop CBM's hooks, and any matcher group or event they leave empty."""
    events = settings.get('hooks')
    if not isinstance(events, dict):
        return False
    changed = False
    for event, groups in list(events.items()):
        kept_groups = []
        for group in groups:
            hooks = group.get('hooks', [])
            kept = [hook for hook in hooks if not HOOK_COMMAND.search(hook.get('command', ''))]
            changed = changed or len(kept) != len(hooks)
            if kept or not hooks:
                kept_groups.append({**group, 'hooks': kept})
        if kept_groups:
            events[event] = kept_groups
        else:
            del events[event]
    if not events:
        del settings['hooks']
    return changed


def strip_mcp(state: dict[str, Any], key: str) -> bool:
    """Drop CBM's server from the ``key`` table, and the table when that empties it."""
    servers = state.get(key)
    if not isinstance(servers, dict) or BINARY not in servers:
        return False
    del servers[BINARY]
    if not servers:
        del state[key]
    return True


def edit_json(path: Path, strip: Callable[[dict[str, Any]], bool]) -> None:
    """Rewrite a JSON object only when ``strip`` would change it."""
    if path.is_file() and strip(json.loads(path.read_text())):
        claude_state.update_json(path, strip)
        print(f'Removed codebase-memory-mcp entries from {path}.')


def write_keeping_mode(path: Path, content: str) -> None:
    """Rewrite the file ``path`` resolves to, keeping that file's permissions."""
    target = Path(os.path.realpath(path))
    mode = target.stat().st_mode & 0o7777
    opencode_config.write_atomically(target, content)
    target.chmod(mode)


def purge_opencode_config(directory: Path) -> None:
    path = opencode_config.config_path(directory)
    config = opencode_config.load_config(path)
    if strip_mcp(config, 'mcp'):
        content = json.dumps(config, indent=2, ensure_ascii=False) + '\n'
        write_keeping_mode(path, content)
        print(f'Removed codebase-memory-mcp entries from {path}.')


def purge_managed_block(path: Path) -> None:
    """
    Remove CBM's marked block, and the file when nothing of the user's remains.

    A symlinked file is edited at its target, and emptied rather than removed, so the link stays.
    """
    if not path.is_file():
        return
    target = Path(os.path.realpath(path))
    text = target.read_text()
    remaining = MANAGED_BLOCK.sub('', text)
    if remaining == text:
        return
    if remaining.strip() or path.is_symlink():
        write_keeping_mode(path, remaining)
    else:
        path.unlink()
    print(f'Removed the codebase-memory-mcp block from {path}.')


def purge_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()
    else:
        return
    print(f'Removed {path}.')


def purge(settings: env.Settings) -> None:
    """Run every step; a config this cannot read must not stop the container from starting."""
    claude = settings.path('AGENTDEV_CLAUDE_DIR')
    opencode = opencode_config.config_directory()
    home = Path(settings.home)
    steps: list[Callable[[], None]] = [
        lambda: edit_json(claude / 'settings.json', strip_hooks),
        lambda: edit_json(
            settings.path('AGENTDEV_CLAUDE_JSON'), lambda state: strip_mcp(state, 'mcpServers')
        ),
        lambda: purge_opencode_config(opencode),
        lambda: purge_managed_block(opencode / 'AGENTS.md'),
        lambda: purge_managed_block(opencode / 'plugins/cbm-augment.ts'),
    ]
    paths = [
        *(root / 'agents' / name for root in (claude, opencode) for name in AGENTS),
        *(root / 'skills/codebase-memory' for root in (claude, opencode)),
        *sorted((claude / 'hooks').glob('cbm-*')),
        home / '.local/bin' / BINARY,
        home / '.cache' / BINARY,
    ]
    steps += [lambda path=path: purge_path(path) for path in paths]
    for step in steps:
        try:
            step()
        except (OSError, ValueError, AttributeError, TypeError) as error:
            print(f'WARNING: codebase-memory-mcp cleanup step failed: {error}', file=sys.stderr)
