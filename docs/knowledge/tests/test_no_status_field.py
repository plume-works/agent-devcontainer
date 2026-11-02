"""
Checks that no graph document sets OKF's optional `status`.

`stage` is the one lifecycle field, so `status` is the graph's single departure
from OKF. Both the workspace graph and the bootstrap scaffold's seed graph are
checked.
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

FRONTMATTER = re.compile(r'\A---\n(.*?)\n---\n', re.S)
STATUS_KEY = re.compile(r'^status\s*:', re.M)


def documents_with_status(root: Path) -> list[str]:
    """Return the paths, relative to ``root``, of documents whose frontmatter sets `status`."""
    found = []
    for path in sorted(root.rglob('*.md')):
        match = FRONTMATTER.match(path.read_text())
        if match and STATUS_KEY.search(match.group(1)):
            found.append(str(path.relative_to(root)))
    return found


@pytest.mark.parametrize('root', GRAPHS, ids=['workspace', 'scaffold'])
def test_no_document_sets_status(root: Path) -> None:
    """No document under a graph's `data/` carries a `status` key."""
    assert documents_with_status(root) == [], f'drop `status` from these documents in {root}'


def test_a_status_key_is_named(tmp_path: Path) -> None:
    """A document that sets `status` is reported by path; body text and nested keys are not."""
    (tmp_path / 'features').mkdir()
    (tmp_path / 'features' / 'old.md').write_text(
        '---\ntype: feature\nstage: deprecated\nstatus: deprecated\n---\n# Old\n'
    )
    (tmp_path / 'clean.md').write_text(
        '---\ntype: note\ngenerated:\n  status: ignored\n---\n# Clean\n\nstatus: in body\n'
    )
    (tmp_path / 'index.md').write_text('# No frontmatter\n')
    assert documents_with_status(tmp_path) == ['features/old.md']
