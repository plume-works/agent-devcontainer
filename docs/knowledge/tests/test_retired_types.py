"""
Rejection checks for the retired `spec` and `architecture` document types.

Behavior and its rationale live in `openspec/specs/`; see
openspec/specs/project-knowledge. Each test copies the graph into `/tmp`, adds one
document of a retired type, and asserts that `iwe schema validate` refuses it.
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


@pytest.fixture
def workspace() -> Iterator[Path]:
    """Copy the configuration and graph into a workspace private to this test."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'retired-types-{uuid4().hex}'
    try:
        (root / 'docs' / 'knowledge').mkdir(parents=True)
        shutil.copytree(IWE_CONFIG, root / '.iwe')
        shutil.copytree(DATA, root / 'docs' / 'knowledge' / 'data')
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _validate(workspace: Path) -> subprocess.CompletedProcess[str]:
    """Run `iwe schema validate` at the workspace root."""
    return subprocess.run(
        ['iwe', 'schema', 'validate'],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )


def test_the_copied_graph_validates(workspace: Path) -> None:
    """The unmodified copy passes, so a failure below is the added document's."""
    result = _validate(workspace)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize('doc_type', ['spec', 'architecture'])
def test_a_retired_type_is_rejected(workspace: Path, doc_type: str) -> None:
    """A document typed `spec` or `architecture` in its old folder fails, named by its key."""
    folder = doc_type
    doc = workspace / 'docs' / 'knowledge' / 'data' / folder / 'retired.md'
    doc.parent.mkdir()
    doc.write_text(f'---\ntype: {doc_type}\ndescription: A retired type.\n---\n\n# Retired\n')
    result = _validate(workspace)
    assert result.returncode != 0
    assert f'data/{folder}/retired' in result.stdout + result.stderr
