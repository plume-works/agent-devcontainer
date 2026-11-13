"""
Checks for the shape the `adr` schema requires.

Each test copies the graph into `/tmp`, writes one ADR into `data/adr/`, and
asserts whether `iwe schema validate` accepts it or refuses it and names it.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA = REPO_ROOT / 'docs' / 'knowledge' / 'data'
IWE_CONFIG = REPO_ROOT / '.iwe'
TMP_ROOT = Path('/tmp/agentdev-tests')

pytestmark = pytest.mark.skipif(
    shutil.which('iwe') is None,
    reason='the iwe CLI is not installed',
)

FRONTMATTER = """---
type: adr
stage: {stage}
description: The timer counts wall-clock time.
---
"""

ONE_PARAGRAPH = """
# The timer counts wall-clock time

A session can pause while the laptop sleeps. The timer counts wall-clock time,
because users expect the session to end at the time it shows.
"""

UNKNOWN_SECTION = (
    ONE_PARAGRAPH
    + """
## Status

Accepted.
"""
)

ALL_SECTIONS = (
    ONE_PARAGRAPH
    + """
## Considered Options

- Count only the time the process runs. Rejected: the session ends late.

## Consequences

- A session that sleeps through its end stops when the laptop wakes.
"""
)


def _validate(workspace: Path) -> subprocess.CompletedProcess[str]:
    """Run `iwe schema validate` at the workspace root."""
    return subprocess.run(
        ['iwe', 'schema', 'validate'],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture
def workspace() -> Iterator[Path]:
    """Copy the configuration and graph into a workspace private to this test."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'adr-schema-{uuid4().hex}'
    try:
        (root / 'docs' / 'knowledge').mkdir(parents=True)
        shutil.copytree(IWE_CONFIG, root / '.iwe')
        shutil.copytree(DATA, root / 'docs' / 'knowledge' / 'data')
        (root / 'docs' / 'knowledge' / 'data' / 'adr').mkdir(exist_ok=True)
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _write_adr(workspace: Path, text: str) -> Path:
    """Write the ADR `adr/9999-fixture-decision` and return its path."""
    path = workspace / 'docs' / 'knowledge' / 'data' / 'adr' / '9999-fixture-decision.md'
    path.write_text(text)
    return path


@pytest.mark.parametrize('body', [ONE_PARAGRAPH, ALL_SECTIONS], ids=['one-paragraph', 'all'])
def test_conforming_adr_validates(workspace: Path, body: str) -> None:
    """An ADR of one paragraph, with or without the optional sections, passes."""
    _write_adr(workspace, FRONTMATTER.format(stage='accepted') + body)
    result = _validate(workspace)
    assert result.returncode == 0, result.stdout + result.stderr


def test_unknown_section_is_rejected(workspace: Path) -> None:
    """An ADR with a section the schema does not permit fails and is named."""
    path = _write_adr(workspace, FRONTMATTER.format(stage='accepted') + UNKNOWN_SECTION)
    result = _validate(workspace)
    assert result.returncode != 0
    assert path.stem in result.stdout


def test_unknown_stage_is_rejected(workspace: Path) -> None:
    """An ADR with a stage outside the lifecycle fails and is named."""
    path = _write_adr(workspace, FRONTMATTER.format(stage='approved') + ONE_PARAGRAPH)
    result = _validate(workspace)
    assert result.returncode != 0
    assert path.stem in result.stdout
