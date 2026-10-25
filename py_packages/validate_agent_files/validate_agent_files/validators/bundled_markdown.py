#!/usr/bin/env python3

"""
Validation for the markdown a plugin ships besides its catalog entry files.

Skills deliberately move detail into ``references/``, and a plugin carries its
own ``README.md``. Those files ship to the plugin cache exactly as ``SKILL.md``
does, so a reference that leaves the plugin root is just as wrong in them — but
catalog discovery only finds ``SKILL.md``, ``*.agent.md``, and ``*.prompt.md``,
so nothing was checking them.

These files have no frontmatter contract to enforce; they are validated for
their references alone. A skill's ``assets/`` tree is skipped: it holds files the
skill copies out as output, whose references resolve where they land.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import List

from ..types import ValidationIssue, ValidationLevel, ValidationResult
from .cross_reference import CrossReferenceValidator

EXCLUDED_DIRS = {'test', 'tests', '.pytest_cache', '__pycache__', '.git', 'node_modules'}

# Output templates beside a SKILL.md, per the Agent Skills directory layout.
SKILL_ASSETS_DIR = 'assets'

# Suffixes owned by a catalog validator, which already checks their references.
CATALOG_ENTRY_SUFFIXES = ('.agent.md', '.prompt.md')


def find_bundled_markdown(plugin_root: Path) -> List[Path]:
    """Return the markdown inside ``plugin_root`` that no catalog validator covers."""
    bundled: List[Path] = []

    for directory, subdirectories, filenames in os.walk(plugin_root):
        skipped = set(EXCLUDED_DIRS)
        if 'SKILL.md' in filenames:
            skipped.add(SKILL_ASSETS_DIR)
        subdirectories[:] = [name for name in subdirectories if name not in skipped]
        for filename in filenames:
            if not filename.endswith('.md'):
                continue
            if filename == 'SKILL.md' or filename.endswith(CATALOG_ENTRY_SUFFIXES):
                continue
            bundled.append(Path(directory) / filename)

    return sorted(bundled)


def validate_bundled_markdown(plugin_root: Path) -> List[ValidationResult]:
    """Validate the references of every non-catalog markdown file in a plugin."""
    results: List[ValidationResult] = []

    for markdown_path in find_bundled_markdown(plugin_root):
        result = ValidationResult(skill_path=str(markdown_path), issues=[])
        try:
            content = markdown_path.read_text(encoding='utf-8')
        except (OSError, UnicodeDecodeError) as exc:
            result.issues.append(
                ValidationIssue(
                    level=ValidationLevel.ERROR,
                    message=f'Failed to read file: {exc}',
                    section='parsing',
                )
            )
            results.append(result)
            continue

        validator = CrossReferenceValidator(
            base_path=str(markdown_path.parent),
            plugin_root=str(plugin_root),
        )
        result.issues.extend(
            validator.validate(skill_path=str(markdown_path), metadata={}, content=content)
        )
        results.append(result)

    return results


__all__ = ['find_bundled_markdown', 'validate_bundled_markdown']
