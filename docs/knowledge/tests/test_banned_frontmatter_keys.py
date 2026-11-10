"""
Checks that no graph document sets a frontmatter key the graph bans.

The banned keys are the graph's departures from OKF; see openspec/specs/iwe-workflow-skills.
Both the workspace graph and, where it exists, the bootstrap scaffold's seed graph
are checked.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
GRAPHS = (
    REPO_ROOT / 'docs' / 'knowledge' / 'data',
    REPO_ROOT
    / '.agents'
    / 'plugins'
    / 'agentdev'
    / 'skills'
    / 'iwe-bootstrap'
    / 'assets'
    / 'docs'
    / 'knowledge'
    / 'data',
)
BANNED_KEYS = ('status', 'generated', 'verified')

FRONTMATTER = re.compile(r'\A---\n(.*?)\n---\n', re.S)
BANNED_KEY = re.compile(rf'^({"|".join(BANNED_KEYS)})\s*:', re.M)


def banned_keys_in(root: Path) -> list[str]:
    """Return ``<path>: <key>`` for each banned top-level frontmatter key under ``root``."""
    found = []
    for path in sorted(root.rglob('*.md')):
        match = FRONTMATTER.match(path.read_text())
        if match:
            for key in BANNED_KEY.findall(match.group(1)):
                found.append(f'{path.relative_to(root)}: {key}')
    return found


@pytest.mark.parametrize('root', GRAPHS, ids=['workspace', 'scaffold'])
def test_no_document_sets_a_banned_key(root: Path) -> None:
    """No document under a graph's `data/` carries a banned frontmatter key."""
    if root != GRAPHS[0] and not root.is_dir():
        pytest.skip(f'{root} is absent in this repository')
    assert banned_keys_in(root) == [], f'drop these frontmatter keys in {root}'


@pytest.mark.parametrize('key', BANNED_KEYS)
def test_a_banned_key_is_named(tmp_path: Path, key: str) -> None:
    """A document that sets a banned key is reported with the key; body text and nested keys are not."""
    (tmp_path / 'features').mkdir()
    (tmp_path / 'features' / 'old.md').write_text(
        f'---\ntype: feature\nstage: deprecated\n{key}: x\n---\n# Old\n'
    )
    (tmp_path / 'clean.md').write_text(
        f'---\ntype: note\nsources:\n- resource: a\n  {key}: ignored\n---\n# Clean\n\n{key}: in body\n'
    )
    (tmp_path / 'index.md').write_text('# No frontmatter\n')
    assert banned_keys_in(tmp_path) == [f'features/old.md: {key}']
