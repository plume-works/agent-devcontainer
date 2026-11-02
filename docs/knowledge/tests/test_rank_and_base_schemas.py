"""
Checks for the `rank` field on work items and the OKF schema's `type` rule.

Each test copies the graph into `/tmp`, edits one document, and runs
`iwe schema validate` against it.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import re
import shutil
import subprocess
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA = REPO_ROOT / 'docs' / 'knowledge' / 'data'
IWE_CONFIG = REPO_ROOT / '.iwe'
TMP_ROOT = Path('/tmp/agentdev-tests')

FRONTMATTER = re.compile(r'\A---\n(.*?)\n---\n', re.S)
RANK = re.compile(r'^rank:.*\n', re.M)

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


def _with_rank(content: str, rank: str) -> str:
    """Replace the frontmatter's `rank` with the given YAML value."""
    match = FRONTMATTER.match(content)
    assert match is not None, 'document has no frontmatter'
    head = RANK.sub('', match.group(1) + '\n') + f'rank: {rank}\n'
    return f'---\n{head.rstrip()}\n---\n' + content[match.end() :]


@pytest.fixture(scope='module')
def workspace() -> Iterator[Path]:
    """Copy the configuration and graph into a workspace private to this run."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'rank-okf-schema-{uuid4().hex}'
    try:
        (root / 'docs' / 'knowledge').mkdir(parents=True)
        shutil.copytree(IWE_CONFIG, root / '.iwe')
        shutil.copytree(DATA, root / 'docs' / 'knowledge' / 'data')
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _open_item(workspace: Path, lane: str) -> Path:
    """Return the first document in a lane that is not done or cancelled."""
    docs = sorted((workspace / 'docs' / 'knowledge' / 'data' / lane).glob('*.md'))
    return next(
        p
        for p in docs
        if not p.name.endswith('.example.md')
        and not re.search(r'^stage: (done|cancelled)$', p.read_text(), re.M)
    )


@pytest.fixture(params=['plans', 'bugs', 'backlog'])
def work_item(workspace: Path, request: pytest.FixtureRequest) -> Iterator[Path]:
    """Yield an open plan, bug, or task, restored after the test."""
    path = _open_item(workspace, request.param)
    original = path.read_text()
    yield path
    path.write_text(original)


@pytest.mark.parametrize('rank', ['0', '-100', '1.5', 'high', "'100'"])
def test_invalid_rank_is_rejected(workspace: Path, work_item: Path, rank: str) -> None:
    """A rank must be an integer of at least 1."""
    work_item.write_text(_with_rank(work_item.read_text(), rank))
    result = _validate(workspace)
    assert result.returncode != 0
    assert work_item.stem in result.stdout
    assert 'rank' in result.stdout


@pytest.mark.parametrize('rank', ['1', '150', '2300'])
def test_positive_integer_rank_passes(workspace: Path, work_item: Path, rank: str) -> None:
    """Any positive integer is a valid rank."""
    work_item.write_text(_with_rank(work_item.read_text(), rank))
    result = _validate(workspace)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.fixture
def untyped(workspace: Path) -> Iterator[Path]:
    """Yield the path of a new document under data/, removed after the test."""
    path = workspace / 'docs' / 'knowledge' / 'data' / f'untyped-{uuid4().hex[:8]}.md'
    yield path
    path.unlink(missing_ok=True)


@pytest.mark.parametrize(
    'front',
    ['', '---\ndescription: A note.\n---\n', "---\ntype: ''\n---\n"],
    ids=['no-frontmatter', 'no-type', 'empty-type'],
)
def test_document_without_type_is_rejected(workspace: Path, untyped: Path, front: str) -> None:
    """The OKF schema requires a non-empty `type` on every document under data/."""
    untyped.write_text(f'{front}# Untyped note\n\nBody.\n')
    result = _validate(workspace)
    assert result.returncode != 0
    assert untyped.stem in result.stdout


def test_typed_document_passes(workspace: Path, untyped: Path) -> None:
    """A document with any non-empty `type` satisfies the OKF schema."""
    untyped.write_text('---\ntype: note\n---\n# Typed note\n\nBody.\n')
    result = _validate(workspace)
    assert result.returncode == 0, result.stdout + result.stderr


def test_no_schema_declares_status() -> None:
    """The graph has no `status` field; `stage` is the only lifecycle record."""
    declaring = [
        p.name
        for p in sorted((IWE_CONFIG / 'schemas').glob('*.yaml'))
        if re.search(r'^\s+status:', p.read_text(), re.M)
    ]
    assert declaring == []
