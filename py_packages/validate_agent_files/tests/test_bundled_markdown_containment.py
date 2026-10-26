#!/usr/bin/env python3

"""Tests for containment in markdown a plugin ships beside its catalog entries."""

from __future__ import annotations

import json
from pathlib import Path

from validate_agent_files.main import main
from validate_agent_files.validators.bundled_markdown import (
    find_bundled_markdown,
    SKILL_ASSETS_DIR,
    validate_bundled_markdown,
)

ESCAPING_LINK = 'See [conventions](../../../../../AGENTS.md) for the rules.\n'

SKILL_BODY = """---
name: demo
description: A comprehensive description of what this demo skill does and when to use it.
---

# Overview

Demo skill body.

## When to use this skill

Use when needed.
"""


def _write_plugin(root: Path, *, claude: bool = True, codex: bool = False) -> Path:
    """Create a plugin packaged for the requested ecosystems, with one skill."""
    plugin_root = root / 'plugin'
    manifest = json.dumps({'name': 'demo', 'version': '1.0.0'}) + '\n'
    if claude:
        (plugin_root / '.claude-plugin').mkdir(parents=True)
        (plugin_root / '.claude-plugin' / 'plugin.json').write_text(manifest)
    if codex:
        (plugin_root / '.codex-plugin').mkdir(parents=True)
        (plugin_root / '.codex-plugin' / 'plugin.json').write_text(manifest)

    skill_dir = plugin_root / 'skills' / 'demo'
    skill_dir.mkdir(parents=True)
    (skill_dir / 'SKILL.md').write_text(SKILL_BODY)
    (root / 'AGENTS.md').write_text('# Conventions\n')
    return plugin_root


def test_catalog_entry_files_are_left_to_their_own_validators(tmp_path):
    """SKILL.md and agent files are already covered, so they are not re-scanned."""
    plugin_root = _write_plugin(tmp_path)
    (plugin_root / 'agents').mkdir()
    (plugin_root / 'agents' / 'demo.agent.md').write_text('# Agent\n')

    bundled = {path.name for path in find_bundled_markdown(plugin_root)}

    assert 'SKILL.md' not in bundled
    assert 'demo.agent.md' not in bundled


def test_reference_page_is_discovered(tmp_path):
    """A skill's references/ page ships with the plugin and must be checked."""
    plugin_root = _write_plugin(tmp_path)
    reference = plugin_root / 'skills' / 'demo' / 'references' / 'detail.md'
    reference.parent.mkdir()
    reference.write_text('# Detail\n')

    assert reference in find_bundled_markdown(plugin_root)


def test_escaping_link_in_a_reference_page_is_reported(tmp_path):
    """The gap this closes: an escaping link outside SKILL.md was invisible."""
    plugin_root = _write_plugin(tmp_path)
    reference = plugin_root / 'skills' / 'demo' / 'references' / 'detail.md'
    reference.parent.mkdir()
    reference.write_text(ESCAPING_LINK)

    results = validate_bundled_markdown(plugin_root)
    issues = [issue for result in results for issue in result.issues]

    assert len(issues) == 1
    assert 'outside the plugin root' in issues[0].message


def test_escaping_link_in_a_plugin_readme_is_reported(tmp_path):
    """A plugin README ships to the cache too, so it is held to the same rule."""
    plugin_root = _write_plugin(tmp_path)
    (plugin_root / 'README.md').write_text(ESCAPING_LINK)

    issues = [
        issue for result in validate_bundled_markdown(plugin_root) for issue in result.issues
    ]

    assert len(issues) == 1
    assert 'outside the plugin root' in issues[0].message


def test_intra_plugin_links_in_bundled_markdown_pass(tmp_path):
    """A reference that stays inside the plugin is valid wherever it ships."""
    plugin_root = _write_plugin(tmp_path)
    (plugin_root / 'README.md').write_text('See [demo](skills/demo/SKILL.md).\n')

    issues = [
        issue for result in validate_bundled_markdown(plugin_root) for issue in result.issues
    ]

    assert issues == []


def test_codex_only_plugin_still_enforces_containment(tmp_path, monkeypatch, capsys):
    """A Codex-only package is a plugin, so its skills cannot link outside it."""
    plugin_root = _write_plugin(tmp_path, claude=False, codex=True)
    (plugin_root / 'skills' / 'demo' / 'SKILL.md').write_text(
        SKILL_BODY.replace('Demo skill body.', ESCAPING_LINK)
    )
    monkeypatch.chdir(tmp_path)

    exit_code = main(['.', '--kind', 'skills'])

    assert exit_code == 1
    assert 'resolves outside the plugin root' in capsys.readouterr().out


def test_skill_assets_are_not_scanned(tmp_path):
    """A skill's assets/ ship as output templates whose links resolve once copied out."""
    plugin_root = _write_plugin(tmp_path)
    asset = plugin_root / 'skills' / 'demo' / SKILL_ASSETS_DIR / 'docs' / 'guide.md'
    asset.parent.mkdir(parents=True)
    asset.write_text('[Timer](spec/timer)\n' + ESCAPING_LINK)

    assert asset not in find_bundled_markdown(plugin_root)
    assert validate_bundled_markdown(plugin_root) == []


def test_assets_directory_outside_a_skill_is_still_scanned(tmp_path):
    """Only the directory beside a SKILL.md is an asset tree."""
    plugin_root = _write_plugin(tmp_path)
    stray = plugin_root / SKILL_ASSETS_DIR / 'notes.md'
    stray.parent.mkdir()
    stray.write_text(ESCAPING_LINK)

    assert stray in find_bundled_markdown(plugin_root)
