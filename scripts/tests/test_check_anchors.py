"""Tests for scripts/check-anchors.py run against synthetic repository trees."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/check-anchors.py'

Run = Callable[[], subprocess.CompletedProcess[str]]
Write = Callable[[str, str], Path]


@pytest.fixture
def tree() -> Iterator[Path]:
    """Yield an empty repository root under the tests' scratch directory."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'check-anchors-{uuid4().hex}'
    root.mkdir()
    yield root
    shutil.rmtree(root)


@pytest.fixture
def write(tree: Path) -> Write:
    """Return a helper that writes a file under the tree."""

    def _write(relative: str, text: str) -> Path:
        path = tree / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    return _write


@pytest.fixture
def run(tree: Path) -> Run:
    """Return a helper that runs the checker on the tree."""

    def _run() -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(SCRIPT), str(tree)], capture_output=True, text=True, check=False
        )

    return _run


GRAPH_DOC = 'docs/knowledge/data/bugs/example.md'


@pytest.mark.parametrize(
    'reference',
    [
        'see `scripts/x.py:120`',
        'see scripts/x.py:120-130',
        'the `Dockerfile:12` stage',
        'the `docker/Dockerfile.base:3` stage',
        'https://github.com/o/r/blob/main/x.py#L42',
        'at line 42 of the file',
        'Lines 3 and 4',
    ],
)
def test_line_number_forms_fail(write: Write, run: Run, reference: str) -> None:
    """Every line-number form in a graph document fails the gate."""
    write(GRAPH_DOC, f'# Bug\n\n{reference}\n')
    result = run()
    assert result.returncode == 1
    assert result.stdout.count(f'{GRAPH_DOC}:3 [line-number]') == 1


@pytest.mark.parametrize(
    'reference',
    [
        '`scripts/x.py::main`',
        '`README.md#usage`',
        '`.github/workflows/ci.yml#jobs.ci.steps.lint`',
        '`SKILL.md#workflow-2 › "never reset it"`',
        'listens on localhost:8080',
        'a line-number reference',
    ],
)
def test_anchors_pass(write: Write, run: Run, reference: str) -> None:
    """Anchor-syntax references and host:port without an extension pass."""
    write(GRAPH_DOC, f'# Bug\n\n{reference}\n')
    result = run()
    assert result.returncode == 0, result.stdout


@pytest.mark.parametrize(
    'relative',
    [
        '.agents/plugins/agentdev/skills/demo/SKILL.md',
        '.agents/plugins/agentdev/skills/demo/references/page.md',
        '.agents/plugins/agentdev/agents/demo.agent.md',
    ],
)
def test_catalog_files_are_scanned(write: Write, run: Run, relative: str) -> None:
    """Catalog skills and agents are in the scan scope."""
    write(relative, 'cite `x.py:7`\n')
    assert run().returncode == 1


def test_files_outside_scope_are_ignored(write: Write, run: Run) -> None:
    """A file outside the graph and the catalog is not scanned."""
    write('README.md', 'cite `x.py:7`\n')
    write('docs/knowledge/AGENTS.md', 'cite `x.py:7`\n')
    assert run().returncode == 0


def test_fenced_blocks_are_scanned_and_every_violation_listed(write: Write, run: Run) -> None:
    """A fenced block is not exempt, and every violation is reported."""
    write(GRAPH_DOC, '# Bug\n\n```\nx.py:1\n```\n\nline 2 and y.py:9\n')
    result = run()
    assert result.returncode == 1
    assert len(result.stdout.splitlines()) == 3
