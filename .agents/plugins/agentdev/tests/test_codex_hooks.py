#!/usr/bin/env python3

"""Codex hook-manifest tests for the agentdev plugin."""

from __future__ import annotations

import json
from pathlib import Path


def load_json(path: Path) -> dict:
    """Load a JSON object from `path`."""
    return json.loads(path.read_text())


def test_codex_manifest_resolves_explicit_hook_file(plugin_root: Path) -> None:
    """Codex uses a runtime-specific hook file instead of default discovery."""
    manifest = load_json(plugin_root / '.codex-plugin/plugin.json')

    hook_path = manifest['extensions']['com.openai']['hooks']
    assert hook_path == './hooks/codex-hooks.json'

    resolved = (plugin_root / hook_path).resolve()
    assert resolved.is_relative_to(plugin_root.resolve())
    assert resolved.is_file()


def test_codex_hooks_do_not_run_claude_session_start(plugin_root: Path) -> None:
    """Codex should not invoke the Claude-web devcontainer startup hook."""
    codex_hooks = load_json(plugin_root / 'hooks/codex-hooks.json')
    claude_hooks = load_json(plugin_root / 'hooks/hooks.json')

    assert codex_hooks == {'hooks': {}}
    assert claude_hooks['hooks']['SessionStart'][0]['hooks'][0]['command'] == (
        '${CLAUDE_PLUGIN_ROOT}/hooks/session-start.sh'
    )
