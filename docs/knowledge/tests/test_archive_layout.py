"""
Checks for the schema bindings of the archive, finding, and guide layout.

Each test writes one document into a scratch graph under `/tmp` that carries this
repository's `.iwe/` configuration, and asserts whether `iwe schema validate`
accepts it or refuses it and names the document.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
IWE_CONFIG = REPO_ROOT / '.iwe'
TMP_ROOT = Path('/tmp/agentdev-tests')

pytestmark = pytest.mark.skipif(
    shutil.which('iwe') is None,
    reason='the iwe CLI is not installed',
)

FINDING = """---
type: finding
---

# A measured behaviour

## Question

What happens?

## Measurement

It happened.

## Closing

Closed when it is explained.
"""

GUIDE = """---
type: guide
---

# Run the thing

Run it.
"""

ARCHIVED_PLAN = """---
type: plan
created: 2026-01-01
stage: done
completed: 2026-01-02
release: internal
---

# An archived plan
"""


@pytest.fixture
def workspace() -> Iterator[Path]:
    """Create an empty graph carrying the repository's IWE configuration."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'archive-layout-{uuid4().hex}'
    try:
        (root / 'docs' / 'knowledge' / 'data').mkdir(parents=True)
        shutil.copytree(IWE_CONFIG, root / '.iwe')
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _write(workspace: Path, key: str, content: str) -> None:
    """Write `content` as the document at `key`."""
    path = workspace / 'docs' / 'knowledge' / f'{key}.md'
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def _validate(workspace: Path) -> subprocess.CompletedProcess[str]:
    """Run `iwe schema validate` at the workspace root."""
    return subprocess.run(
        ['iwe', 'schema', 'validate'],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize(
    ('key', 'content'),
    [
        ('data/findings/measured', FINDING),
        ('data/guides/run-the-thing', GUIDE),
        ('data/archive/2.1.0/plans/20260101-archived', ARCHIVED_PLAN),
        ('data/archive/next-release/plans/20260101-archived', ARCHIVED_PLAN),
    ],
    ids=['finding', 'guide', 'archived-plan', 'next-release-plan'],
)
def test_conforming_document_validates(workspace: Path, key: str, content: str) -> None:
    """A document of each new kind that follows its schema passes."""
    _write(workspace, key, content)
    result = _validate(workspace)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ('key', 'content'),
    [
        (
            'data/archive/2.1.0/plans/20260101-archived',
            ARCHIVED_PLAN.replace('stage: done', 'stage: shipped'),
        ),
        ('data/findings/measured', FINDING[: FINDING.index('## Closing')]),
        (
            'data/findings/measured',
            FINDING.replace('type: finding\n', 'type: finding\nstage: done\n'),
        ),
        (
            'data/guides/run-the-thing',
            GUIDE.replace('type: guide\n', 'type: guide\nstage: done\n'),
        ),
    ],
    ids=[
        'archived-plan-invalid-stage',
        'finding-without-closing',
        'finding-with-stage',
        'guide-with-stage',
    ],
)
def test_broken_document_is_rejected(workspace: Path, key: str, content: str) -> None:
    """A document that breaks its type's schema fails validation, named by key."""
    _write(workspace, key, content)
    result = _validate(workspace)
    assert result.returncode != 0
    assert key in result.stdout
