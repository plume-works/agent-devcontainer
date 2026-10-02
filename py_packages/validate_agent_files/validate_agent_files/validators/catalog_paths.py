#!/usr/bin/env python3

"""
Guard against literal catalog paths in skill bodies.

Skills ship inside the ``agentdev`` plugin, where the catalog lives in the
plugin cache rather than in a repository's ``.claude/``. A literal
``.claude/skills/<name>/...`` reference therefore resolves nowhere at runtime
and must be written as a path relative to the skill directory (self-reference)
or as a namespaced skill invocation (cross-reference).
"""

from __future__ import annotations

import re
from typing import List

from ..types import ValidationIssue, ValidationLevel

# ``~/.claude/...`` is the personal catalog, which resolves for a plugin user
# exactly as it always did, so only repository-relative paths are flagged.
LITERAL_CATALOG_PATH = re.compile(r'(?<!~)(?<!~/)\.claude/(?:skills|agents)/')

REMEDIATION = (
    'write a path inside this skill relative to the skill directory, or invoke '
    'a sibling skill by its namespaced name (for example /agentdev:update-branch)'
)


def validate_catalog_paths(content: str, line_offset: int = 0) -> List[ValidationIssue]:
    """Report every literal catalog path found in ``content``."""
    issues: List[ValidationIssue] = []

    for index, line in enumerate(content.splitlines(), start=1):
        match = LITERAL_CATALOG_PATH.search(line)
        if match is None:
            continue
        issues.append(
            ValidationIssue(
                level=ValidationLevel.ERROR,
                message=(
                    f'Literal catalog path {match.group(0)} does not resolve inside a '
                    f'plugin: {REMEDIATION}'
                ),
                line_number=line_offset + index,
                section='catalog-paths',
            )
        )

    return issues


__all__ = ['validate_catalog_paths']
