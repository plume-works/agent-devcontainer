"""
Rejection checks for the body shape the bug and feature schemas require.

Each test copies the graph into the repo-root `.tmp/`, breaks one conforming
bug or feature document the way a hand-written one would, and asserts that
`iwe schema validate` refuses it and names the section at fault.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
import re
import shutil
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA = REPO_ROOT / 'docs' / 'knowledge' / 'data'
IWE_CONFIG = REPO_ROOT / '.iwe'
TMP_ROOT = REPO_ROOT / '.tmp'

SECTION = re.compile(r'^## .+\n(?:(?!## ).*\n?)*', re.M)

pytestmark = pytest.mark.skipif(
    shutil.which('iwe') is None,
    reason='the iwe CLI is not installed',
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


def _section(content: str, name: str) -> re.Match[str]:
    """Return the `## name` section, through the line before the next H2."""
    for match in SECTION.finditer(content):
        if match.group().startswith(f'## {name}\n'):
            return match
    raise AssertionError(f'section {name!r} not found')


def _drop(name: str) -> Callable[[str], str]:
    """Build a mutation that removes the `## name` section."""

    def mutate(content: str) -> str:
        match = _section(content, name)
        return content[: match.start()] + content[match.end() :]

    return mutate


def _move_after(name: str, anchor: str) -> Callable[[str], str]:
    """Build a mutation that moves `## name` to just after `## anchor`."""

    def mutate(content: str) -> str:
        moved = _section(content, name).group()
        content = _drop(name)(content)
        end = _section(content, anchor).end()
        return content[:end] + moved + content[end:]

    return mutate


def _strip_bug_prefix(content: str) -> str:
    """Remove the `Bug: ` prefix from the H1."""
    return re.sub(r'^# Bug: ', '# ', content, count=1, flags=re.M)


@pytest.fixture(scope='module')
def workspace() -> Path:
    """Copy the configuration and graph into an isolated workspace."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / 'body-shape-schemas'
    if root.exists():
        shutil.rmtree(root)
    (root / 'docs' / 'knowledge').mkdir(parents=True)
    shutil.copytree(IWE_CONFIG, root / '.iwe')
    shutil.copytree(DATA, root / 'docs' / 'knowledge' / 'data')
    return root


@pytest.fixture
def document(workspace: Path, request: pytest.FixtureRequest) -> Iterator[Path]:
    """Yield the first document in the requested lane, restored after the test."""
    path = sorted((workspace / 'docs' / 'knowledge' / 'data' / request.param).glob('*.md'))[0]
    original = path.read_text()
    yield path
    path.write_text(original)


def test_unmodified_graph_validates(workspace: Path) -> None:
    """The copied graph passes, so each rejection below is the mutation's."""
    result = _validate(workspace)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ('document', 'mutate', 'reported'),
    [
        ('bugs', _drop('Root cause'), 'required section "Root cause" is missing'),
        ('bugs', _move_after('Fix', 'Symptom'), 'is missing'),
        ('bugs', _strip_bug_prefix, 'is missing'),
        ('features', _drop('Edge cases'), 'required section "Edge cases" is missing'),
        ('features', _move_after('Open questions', 'Purpose'), 'is missing'),
    ],
    ids=[
        'bug-missing-section',
        'bug-out-of-order',
        'bug-title-prefix',
        'feature-missing-section',
        'feature-out-of-order',
    ],
    indirect=['document'],
)
def test_malformed_body_is_rejected(
    workspace: Path, document: Path, mutate: Callable[[str], str], reported: str
) -> None:
    """A document missing, reordering, or misnaming a required section fails."""
    document.write_text(mutate(document.read_text()))
    result = _validate(workspace)
    assert result.returncode != 0
    assert document.stem in result.stdout
    assert reported in result.stdout
