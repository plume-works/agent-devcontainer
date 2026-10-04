#!/usr/bin/env python3

"""Tests for plugin-layout validation (spec 02: manifests and catalog paths)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from mock_catalog import (
    claude_entry,
    CLAUDE_MANIFEST,
    CODEX_MANIFEST,
    plugin_manifest,
    PLUGIN_NAME,
    write_claude_marketplace,
    write_json,
    write_skill,
)
from validate_agent_files.main import main
from validate_agent_files.validators.catalog_paths import REMEDIATION

# This fixture publishes its plugin from directly under the repository root,
# which is a layout the tool must accept as readily as a nested one.
PLUGIN_SOURCE = './plugin'


def _write_plugin(
    tmp_path: Path,
    *,
    plugin_version: str,
    marketplace_version: str,
    codex_version: Optional[str] = None,
) -> Path:
    """
    Write a plugin packaged for both Claude and Codex.

    ``codex_version`` defaults to ``plugin_version``; pass ``''`` to omit the
    Codex manifest entirely.
    """
    plugin_root = tmp_path / PLUGIN_SOURCE
    write_json(plugin_root / CLAUDE_MANIFEST, plugin_manifest(plugin_version))
    codex_version = plugin_version if codex_version is None else codex_version
    if codex_version:
        write_json(plugin_root / CODEX_MANIFEST, plugin_manifest(codex_version))
    write_claude_marketplace(
        tmp_path,
        claude_entry(
            source=PLUGIN_SOURCE,
            version=marketplace_version,
            description='Catalog.',
        ),
    )
    return plugin_root


def test_agreeing_manifest_versions_pass(tmp_path: Path, capsys) -> None:
    """A plugin whose manifests agree on the version validates cleanly."""
    plugin_root = _write_plugin(tmp_path, plugin_version='1.0.0', marketplace_version='1.0.0')
    write_skill(plugin_root, usage='Use it when testing plugin layout validation.')

    exit_code = main([str(plugin_root), '--kind', 'skills'])
    captured = capsys.readouterr()

    assert exit_code == 0, captured.out
    assert 'does not match' not in captured.out


def test_disagreeing_manifest_versions_fail(tmp_path: Path, capsys) -> None:
    """A marketplace entry that drifts from plugin.json is an error."""
    plugin_root = _write_plugin(tmp_path, plugin_version='1.0.0', marketplace_version='1.1.0')
    write_skill(plugin_root, usage='Use it when testing plugin layout validation.')

    exit_code = main([str(plugin_root), '--kind', 'skills'])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert f"'{PLUGIN_NAME}' version 1.0.0" in captured.out
    assert '1.1.0' in captured.out


def test_disagreeing_codex_manifest_version_fails(tmp_path: Path, capsys) -> None:
    """Claude and Codex package manifests must describe the same release."""
    plugin_root = _write_plugin(
        tmp_path,
        plugin_version='1.0.0',
        marketplace_version='1.0.0',
        codex_version='1.1.0',
    )
    write_skill(plugin_root, usage='Use it when testing plugin layout validation.')

    exit_code = main([str(plugin_root), '--kind', 'skills'])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert '.codex-plugin/plugin.json' in captured.out
    assert "version '1.1.0'" in captured.out
    assert "version '1.0.0'" in captured.out


def test_missing_codex_manifest_is_allowed_by_default(tmp_path: Path, capsys) -> None:
    """
    Not every plugin ships for Codex, so its manifest is optional by default.

    A repository that does require it opts in with ``--require-marketplace codex``;
    see ``test_require_marketplace.py``.
    """
    plugin_root = _write_plugin(
        tmp_path,
        plugin_version='1.0.0',
        marketplace_version='1.0.0',
        codex_version='',
    )
    write_skill(plugin_root, usage='Use it when testing plugin layout validation.')

    exit_code = main([str(plugin_root), '--kind', 'skills'])
    captured = capsys.readouterr()

    assert exit_code == 0, captured.out


def test_unparsable_plugin_manifest_fails(tmp_path: Path, capsys) -> None:
    """A plugin.json that does not parse is an error, not a crash."""
    plugin_root = _write_plugin(tmp_path, plugin_version='1.0.0', marketplace_version='1.0.0')
    (plugin_root / CLAUDE_MANIFEST).write_text('{not json')
    write_skill(plugin_root, usage='Use it when testing plugin layout validation.')

    exit_code = main([str(plugin_root), '--kind', 'skills'])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert 'plugin.json' in captured.out


def test_literal_catalog_path_in_skill_body_fails(tmp_path: Path, capsys) -> None:
    """A reintroduced literal `.claude/skills/` path fails validation (F6 guard)."""
    plugin_root = _write_plugin(tmp_path, plugin_version='1.0.0', marketplace_version='1.0.0')
    write_skill(plugin_root, body='Run `.claude/skills/demo/run.sh` to start.')

    exit_code = main([str(plugin_root), '--kind', 'skills'])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert '.claude/skills/' in captured.out
    assert REMEDIATION in captured.out


def test_skill_relative_path_is_accepted(tmp_path: Path, capsys) -> None:
    """A path relative to the skill directory, the recommended replacement, is not flagged."""
    plugin_root = _write_plugin(tmp_path, plugin_version='1.0.0', marketplace_version='1.0.0')
    write_skill(plugin_root, body='Run `scripts/demo.sh` to start.')

    exit_code = main([str(plugin_root), '--kind', 'skills'])
    captured = capsys.readouterr()

    assert exit_code == 0, captured.out


def test_personal_catalog_path_is_not_flagged(tmp_path: Path, capsys) -> None:
    """`~/.claude/agents/` still resolves for a plugin user, so it is allowed."""
    plugin_root = _write_plugin(tmp_path, plugin_version='1.0.0', marketplace_version='1.0.0')
    write_skill(plugin_root, body='Personal agents live in `~/.claude/agents/`.')

    exit_code = main([str(plugin_root), '--kind', 'skills'])

    captured = capsys.readouterr()
    assert exit_code == 0, captured.out
