#!/usr/bin/env python3

"""Runtime-specific hook-manifest tests for the agentdev plugin."""

from __future__ import annotations

import json
from pathlib import Path


def load_json(path: Path) -> dict:
    """Load a JSON object from `path`."""
    return json.loads(path.read_text())


CODEX_MANIFEST_KEYS = {
    'apps',
    'author',
    'description',
    'homepage',
    'id',
    'interface',
    'keywords',
    'license',
    'mcpServers',
    'name',
    'repository',
    'skills',
    'version',
}


def test_codex_manifest_fields_match_current_ingestion_contract(plugin_root: Path) -> None:
    """Codex manifest fields stay within the current ingestion contract."""
    manifest = load_json(plugin_root / '.codex-plugin/plugin.json')

    assert set(manifest) <= CODEX_MANIFEST_KEYS


def test_codex_has_no_default_hook_manifest(plugin_root: Path) -> None:
    """Codex should not discover the Claude-web devcontainer startup hook."""
    manifest = load_json(plugin_root / '.codex-plugin/plugin.json')

    assert 'extensions' not in manifest
    assert 'hooks' not in manifest
    assert not (plugin_root / 'hooks/hooks.json').exists()


def test_claude_manifest_resolves_claude_hook_file(plugin_root: Path) -> None:
    """Claude keeps the SessionStart command in a Claude-specific hook file."""
    manifest = load_json(plugin_root / '.claude-plugin/plugin.json')

    hook_path = manifest['hooks']
    assert hook_path == './hooks/claude-hooks.json'

    resolved = (plugin_root / hook_path).resolve()
    assert resolved.is_relative_to(plugin_root.resolve())
    assert resolved.is_file()

    claude_hooks = load_json(resolved)
    assert claude_hooks['hooks']['SessionStart'][0]['hooks'][0]['command'] == (
        '${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh'
    )
