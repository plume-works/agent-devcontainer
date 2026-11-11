"""Tests for scripts/check-ship-records.py run against made-up bug and plan documents."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/check-ship-records.py'

Write = Callable[[str, str], Path]
Run = Callable[..., subprocess.CompletedProcess[str]]


@pytest.fixture
def tree() -> Iterator[Path]:
    """Yield an empty directory under the tests' scratch root."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'check-ship-records-{uuid4().hex}'
    root.mkdir()
    yield root
    shutil.rmtree(root)


@pytest.fixture
def write(tree: Path) -> Write:
    """Return a helper that writes a document under the tree."""

    def _write(name: str, text: str) -> Path:
        path = tree / name
        path.write_text(text)
        return path

    return _write


def run(*paths: Path) -> subprocess.CompletedProcess[str]:
    """Run the checker on the given documents."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *map(str, paths)],
        capture_output=True,
        text=True,
        check=False,
    )


def bug(stage: str, fix: bool) -> str:
    """Return a bug document at the given stage, with or without a Fix section."""
    text = f'---\ntype: bug\nstage: {stage}\n---\n\n# Bug: example\n\n## Symptom\n\nIt breaks.\n'
    return text + ('\n## Fix\n\nFixed by a plan.\n' if fix else '')


def test_done_bug_without_fix_fails(write: Write) -> None:
    """A done bug with no Fix section fails, naming the document."""
    path = write('bug.md', bug('done', fix=False))
    result = run(path)
    assert result.returncode == 1
    assert f'{path}:1 ' in result.stdout
    assert '## Fix' in result.stdout


def test_done_bug_with_fix_passes(write: Write) -> None:
    """A done bug with a Fix section passes."""
    result = run(write('bug.md', bug('done', fix=True)))
    assert (result.returncode, result.stdout) == (0, '')


@pytest.mark.parametrize('stage', ['pending', 'planned', 'cancelled'])
def test_open_or_cancelled_bug_without_fix_passes(write: Write, stage: str) -> None:
    """A bug that is not done needs no Fix section."""
    result = run(write('bug.md', bug(stage, fix=False)))
    assert (result.returncode, result.stdout) == (0, '')


def test_fix_heading_in_a_code_fence_does_not_count(write: Write) -> None:
    """A Fix heading quoted inside a fenced code block is not the document's Fix section."""
    text = bug('done', fix=False) + '\n```markdown\n## Fix\n```\n'
    assert run(write('bug.md', text)).returncode == 1


def test_every_violation_is_reported(write: Write) -> None:
    """The checker reports every failing document, not only the first."""
    first = write('first.md', bug('done', fix=False))
    second = write('second.md', bug('done', fix=False))
    result = run(first, write('ok.md', bug('done', fix=True)), second)
    assert result.returncode == 1
    assert f'{first}:1 ' in result.stdout
    assert f'{second}:1 ' in result.stdout
