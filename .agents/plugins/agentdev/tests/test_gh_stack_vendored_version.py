#!/usr/bin/env python3

"""Keep the vendored gh-stack skill on the gh-stack release the image installs."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROLE_DEFAULTS = Path('ansible/roles/github_cli/defaults/main.yml')
VERSION_KEY = 'github_cli_gh_stack_version'


def _frontmatter(skill_file: Path) -> dict:
    """Parse the YAML frontmatter of a SKILL.md file."""
    _, block, _ = skill_file.read_text(encoding='utf-8').split('---\n', 2)
    return yaml.safe_load(block)


def test_vendored_skill_matches_pinned_extension(plugin_root: Path) -> None:
    """Fail when a gh-stack bump leaves the vendored skill on another release."""
    # Arrange
    defaults = plugin_root.parents[2] / ROLE_DEFAULTS
    if not defaults.is_file():
        pytest.skip('the image role that pins gh-stack ships only with the template repository')
    pinned = yaml.safe_load(defaults.read_text(encoding='utf-8'))[VERSION_KEY]

    # Act
    vendored = _frontmatter(plugin_root / 'skills/gh-stack/SKILL.md')['metadata']['version']

    # Assert
    assert vendored == pinned.removeprefix('v')
