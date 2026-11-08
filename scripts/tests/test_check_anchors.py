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


TARGETS = {
    'src/tool.py': (
        'LIMIT = 3\n\n\nclass Store:\n    """Store."""\n\n'
        '    def append(self) -> None:\n        """Append."""\n\n\n'
        'def main() -> int:\n    """Run."""\n    return 0\n'
    ),
    'src/run.sh': '#!/usr/bin/env bash\nsetup_env() {\n  :\n}\n',
    'docs/guide.md': (
        '# Guide\n\n## Workflow 2: Handle the Result\n\nNever reset   it.\n\n'
        '## Notes\n\nA note.\n\n## Notes\n\nAnother.\n\n```\n## Not a heading\n```\n'
    ),
    '.github/workflows/ci.yml': (
        'on:\n  push:\njobs:\n  ci:\n    steps:\n      - id: lint\n        run: x\n'
        '      - name: Build\n        run: y\n'
    ),
    'config.json': '{"a": {"b": 1}}\n',
    'pyproject.toml': '[tool.ruff]\nline-length = 99\n',
    'Makefile': 'build:\n\techo hi\n',
    'docker/app.Dockerfile': 'FROM python:3 AS builder\nRUN true\n',
}

ACTIVE_PLAN = 'docs/knowledge/data/plans/20260101-demo.md'


def plan(references: str, stage: str = '', steps: str = '') -> str:
    """Return a plan document with the given Key references body."""
    front = f'---\ntype: plan\n{stage}---\n'
    return (
        f'{front}\n# Demo\n\n## Implementation Steps\n\n{steps}\n\n'
        f'## Key references\n\n{references}\n\n## Trailer\n\n`missing.py::gone`\n'
    )


@pytest.fixture
def targets(write: Write) -> None:
    """Write the files anchors point at."""
    for relative, text in TARGETS.items():
        write(relative, text)


@pytest.mark.usefixtures('targets')
@pytest.mark.parametrize(
    'anchor',
    [
        '`src/tool.py::main`',
        '`src/tool.py::Store.append`',
        '`src/tool.py::LIMIT`',
        '`src/run.sh::setup_env`',
        '`docs/guide.md#workflow-2-handle-the-result`',
        '`docs/guide.md#notes-1`',
        '`docs/guide.md#workflow-2-handle-the-result › "Never reset it"`',
        '`docs/guide.md › "Another."`',
        '`.github/workflows/ci.yml#jobs.ci.steps.lint`',
        '`.github/workflows/ci.yml#jobs.ci.steps.Build`',
        '`.github/workflows/ci.yml#on.push`',
        '`config.json#a.b`',
        '`pyproject.toml#tool.ruff.line-length`',
        '`Makefile#build`',
        '`docker/app.Dockerfile#builder`',
        '`owner/repo#123`',
    ],
)
def test_anchor_forms_resolve(write: Write, run: Run, anchor: str) -> None:
    """Each anchor form resolves against its target."""
    write(ACTIVE_PLAN, plan(f'- {anchor} — target'))
    result = run()
    assert result.returncode == 0, result.stdout


@pytest.mark.usefixtures('targets')
@pytest.mark.parametrize(
    ('anchor', 'reason'),
    [
        ('`src/tool.py::run`', 'symbol `run` not found'),
        ('`src/tool.py::Store.drop`', 'symbol `Store.drop` not found'),
        ('`src/run.sh::teardown`', 'symbol `teardown` not found'),
        ('`docs/guide.md#workflow-3`', 'heading `#workflow-3` not found'),
        ('`docs/guide.md#not-a-heading`', 'heading `#not-a-heading` not found'),
        ('`docs/guide.md#notes › "Another."`', 'quote "Another." not found'),
        ('`.github/workflows/ci.yml#jobs.ci.steps.test`', 'key path'),
        ('`config.json#a.c`', 'key path'),
        ('`Makefile#install`', 'target or stage'),
        ('`docker/app.Dockerfile#runtime`', 'target or stage'),
        ('`src/gone.py::main`', 'file not found'),
    ],
)
def test_broken_anchors_fail(write: Write, run: Run, anchor: str, reason: str) -> None:
    """A renamed symbol, removed heading, missing key, reworded quote, or missing file fails."""
    write(ACTIVE_PLAN, plan(f'- {anchor} — target'))
    result = run()
    assert result.returncode == 1
    assert f'{ACTIVE_PLAN}:' in result.stdout
    assert '[anchor]' in result.stdout
    assert reason in result.stdout


@pytest.mark.usefixtures('targets')
def test_quote_spans_wrapped_lines(write: Write, run: Run) -> None:
    """A quote matches across line wraps in the anchor and the target."""
    write(
        ACTIVE_PLAN, plan('- `docs/guide.md#workflow-2-handle-the-result › "Never\n  reset it"`')
    )
    assert run().returncode == 0


@pytest.mark.usefixtures('targets')
@pytest.mark.parametrize(
    ('relative', 'text'),
    [
        (ACTIVE_PLAN, plan('- `src/tool.py::main`', stage='stage: done\ncompleted: 2026-01-02\n')),
        (ACTIVE_PLAN, plan('- `src/tool.py::main`', stage='stage: cancelled\n')),
        (ACTIVE_PLAN, plan('- `src/tool.py::main`', steps='- [ ] Create `src/new.py::main`')),
        ('docs/knowledge/data/bugs/fixed.md', '---\ntype: bug\nstage: done\n---\n`a.py::b`\n'),
        ('docs/knowledge/data/spec/thing.md', '---\ntype: spec\n---\n`a.py::b`\n'),
    ],
)
def test_out_of_scope_anchors_are_not_resolved(
    write: Write, run: Run, relative: str, text: str
) -> None:
    """Closed plans, a plan's tasks and other sections, done bugs, and specs are not resolved."""
    write(relative, text)
    assert run().returncode == 0, run().stdout


@pytest.mark.usefixtures('targets')
@pytest.mark.parametrize(
    'relative',
    [
        'docs/knowledge/data/bugs/open.md',
        'docs/knowledge/data/backlog/item.md',
        'docs/knowledge/data/architecture/design.md',
    ],
)
def test_live_documents_resolve_everywhere(write: Write, run: Run, relative: str) -> None:
    """Open bugs and backlog items and architecture documents resolve their whole body."""
    stage = '' if 'architecture' in relative else 'stage: pending\n'
    text = f'---\ntype: x\n{stage}---\n\nSee `src/tool.py::gone`.\n'
    write(relative, text)
    result = run()
    assert result.returncode == 1
    assert f'{relative}:{text.count(chr(10))} [anchor]' in result.stdout
