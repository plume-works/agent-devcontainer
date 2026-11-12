"""
Checks for the shape the bug and feature schemas require.

Each test copies the graph into `/tmp`, changes one conforming bug or feature
document the way a hand-written one would, and asserts whether
`iwe schema validate` accepts it or refuses it and names the document.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
import re
import shutil
import subprocess
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA = REPO_ROOT / 'docs' / 'knowledge' / 'data'
IWE_CONFIG = REPO_ROOT / '.iwe'
EXAMPLES = (
    REPO_ROOT
    / '.agents'
    / 'plugins'
    / 'agentdev'
    / 'skills'
    / 'iwe-bootstrap'
    / 'assets'
    / 'docs'
    / 'knowledge'
    / 'data'
)
TMP_ROOT = Path('/tmp/agentdev-tests')

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


def _set_field(name: str, value: str | None) -> Callable[[str], str]:
    """Build a mutation that sets frontmatter `name` to `value`, or removes it on None."""

    def mutate(content: str) -> str:
        line = re.compile(rf'^{name}: .*\n', re.M)
        assert line.search(content), f'frontmatter field {name!r} not found'
        return line.sub('' if value is None else f'{name}: {value}\n', content, count=1)

    return mutate


def _add_after(name: str, anchor: str) -> Callable[[str], str]:
    """Build a mutation that adds an empty-bodied `## name` just after `## anchor`."""

    def mutate(content: str) -> str:
        end = _section(content, anchor).end()
        return content[:end] + f'## {name}\n\nText.\n\n' + content[end:]

    return mutate


def _strip_bug_prefix(content: str) -> str:
    """Remove the `Bug: ` prefix from the H1."""
    return re.sub(r'^# Bug: ', '# ', content, count=1, flags=re.M)


def _seed(data: Path, *examples: str) -> None:
    """Copy bootstrap example documents into the graph, so each lane has a live member."""
    for key in examples:
        target = data / f'{key.replace(".example", "")}.md'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(EXAMPLES / f'{key}.md', target)


@pytest.fixture(scope='module')
def workspace() -> Iterator[Path]:
    """Copy the configuration and graph into a workspace private to this run."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'body-shape-schemas-{uuid4().hex}'
    try:
        (root / 'docs' / 'knowledge').mkdir(parents=True)
        shutil.copytree(IWE_CONFIG, root / '.iwe')
        shutil.copytree(DATA, root / 'docs' / 'knowledge' / 'data')
        _seed(root / 'docs' / 'knowledge' / 'data', 'features/streak-widget.example')
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


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
        ('bugs', _move_after('Root cause', 'Symptom'), 'is missing'),
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


@pytest.mark.parametrize(
    ('document', 'mutate'),
    [
        ('bugs', _set_field('stage', None)),
        ('bugs', _set_field('severity', None)),
        ('bugs', _set_field('severity', 'urgent')),
        ('bugs', _set_field('stage', 'open')),
    ],
    ids=['bug-no-stage', 'bug-no-severity', 'bug-bad-severity', 'bug-bad-stage'],
    indirect=['document'],
)
def test_malformed_bug_frontmatter_is_rejected(
    workspace: Path, document: Path, mutate: Callable[[str], str]
) -> None:
    """A bug without a valid stage and severity fails and is named."""
    document.write_text(mutate(document.read_text()))
    result = _validate(workspace)
    assert result.returncode != 0
    assert document.stem in result.stdout


def _neither_solution_nor_fix(content: str) -> str:
    """Remove any `## Potential solution` and `## Fix` sections."""
    for name in ('Potential solution', 'Fix'):
        if any(m.group().startswith(f'## {name}\n') for m in SECTION.finditer(content)):
            content = _drop(name)(content)
    return content


def _both_solution_and_fix(content: str) -> str:
    """Ensure the bug carries a `## Potential solution` followed by a `## Fix`."""
    content = _neither_solution_nor_fix(content)
    content = _add_after('Potential solution', 'Root cause')(content)
    return _add_after('Fix', 'Potential solution')(content)


@pytest.mark.parametrize(
    ('document', 'mutate'),
    [
        ('bugs', _neither_solution_nor_fix),
        ('bugs', _both_solution_and_fix),
    ],
    ids=['bug-no-optional-sections', 'bug-both-optional-sections'],
    indirect=['document'],
)
def test_optional_bug_sections_are_accepted(
    workspace: Path, document: Path, mutate: Callable[[str], str]
) -> None:
    """A bug validates with neither or both of Potential solution and Fix."""
    document.write_text(mutate(document.read_text()))
    result = _validate(workspace)
    assert result.returncode == 0, result.stdout + result.stderr
