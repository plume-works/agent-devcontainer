"""
Shape gate for plan checkboxes in `docs/knowledge/data/plans/`.

A plan with `stage: done` has no unchecked `- [ ]` task under its task section.
The evidence of a ticked task is in the commit that ticks it: see ADR-0093.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import frontmatter
import pytest

PLANS_DIR = Path(__file__).resolve().parents[1] / 'data' / 'plans'

# The plan skill specifies `## Implementation Steps`. `## Tasks` is the older
# heading still used by plans written before it, and a gate that silently skips
# a whole document is the invisibility this gate exists to remove.
TASK_SECTIONS = frozenset({'Implementation Steps', 'Tasks'})

TASK_LINE = re.compile(r'^- \[(?P<mark>[ xX])\]\s+(?P<text>.*)$')
FENCE = re.compile(r'^[ \t]*(?:```|~~~)')
HEADING = re.compile(r'^(?P<hashes>#{1,6})\s+(?P<title>.*)$')

RULE_COMPLETENESS = 'completeness'


@dataclass(frozen=True)
class Violation:
    """A single rule breach, anchored to the line that must change."""

    path: Path
    line: int
    rule: str
    message: str

    def __str__(self) -> str:
        """Render the violation as `path:line [rule] message`."""
        return f'{self.path}:{self.line} [{self.rule}] {self.message}'


@dataclass
class TaskBlock:
    """A checkbox task line plus the indented lines that belong to it."""

    line: int
    ticked: bool
    text: str
    body: list[str]


def task_blocks(text: str) -> list[TaskBlock]:
    """
    Collect the checkbox tasks under a plan's task section.

    Checkboxes elsewhere in the document — the format example under
    `## Approach`, say — are not tasks, and neither is anything inside a fenced
    code block.

    Args:
        text: The full Markdown source of a plan document.

    Returns:
        The task blocks in document order.

    """
    blocks: list[TaskBlock] = []
    current: TaskBlock | None = None
    section: str | None = None
    in_fence = False

    for lineno, line in enumerate(text.splitlines(), start=1):
        if FENCE.match(line):
            in_fence = not in_fence
            if current is not None:
                current.body.append(line)
            continue
        if in_fence:
            if current is not None:
                current.body.append(line)
            continue

        heading = HEADING.match(line)
        if heading:
            current = None
            if len(heading.group('hashes')) <= 2:
                section = heading.group('title').strip()
            continue

        if section not in TASK_SECTIONS:
            current = None
            continue

        task = TASK_LINE.match(line)
        if task:
            current = TaskBlock(
                line=lineno,
                ticked=task.group('mark').lower() == 'x',
                text=task.group('text').strip(),
                body=[],
            )
            blocks.append(current)
            continue

        if current is None:
            continue
        if not line.strip() or line.startswith((' ', '\t')):
            current.body.append(line)
        else:
            current = None

    return blocks


def check_plan(path: Path, text: str) -> list[Violation]:
    """
    Apply the checkbox rule to one plan document.

    Args:
        path: The path reported in violations.
        text: The full Markdown source of the plan.

    Returns:
        Every violation found, in document order — not just the first.

    """
    stage = frontmatter.loads(text).get('stage')
    violations: list[Violation] = []

    for block in task_blocks(text):
        if stage == 'done' and not block.ticked:
            violations.append(
                Violation(
                    path,
                    block.line,
                    RULE_COMPLETENESS,
                    'plan is `stage: done` but this task is unchecked',
                )
            )

    return violations


def check_directory(plans_dir: Path) -> list[Violation]:
    """
    Apply the checkbox rule to every plan in a directory.

    Args:
        plans_dir: Directory holding `*.md` plan documents.

    Returns:
        Every violation found across all plans, grouped by file.

    """
    violations: list[Violation] = []
    for path in sorted(plans_dir.glob('*.md')):
        violations.extend(check_plan(path, path.read_text(encoding='utf-8')))
    return violations


def write_plan(plans_dir: Path, name: str, frontmatter_lines: str, body: str) -> Path:
    """
    Write a fixture plan and return its path.

    Args:
        plans_dir: Directory to write into.
        name: File stem, without the `.md` suffix.
        frontmatter_lines: YAML body of the frontmatter block.
        body: Markdown after the frontmatter.

    Returns:
        The path written.

    """
    plans_dir.mkdir(parents=True, exist_ok=True)
    path = plans_dir / f'{name}.md'
    path.write_text(f'---\n{frontmatter_lines}\n---\n\n{body}', encoding='utf-8')
    return path


def line_of(path: Path, needle: str) -> int:
    """
    Find the 1-based line number of the only line containing `needle`.

    Args:
        path: File to search.
        needle: Substring that must appear on exactly one line.

    Returns:
        The 1-based line number.

    """
    matches = [
        number
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1)
        if needle in line
    ]
    assert len(matches) == 1, f'{needle!r} matched {len(matches)} lines in {path}'
    return matches[0]


ACTIVE_FRONTMATTER = 'type: plan\ncreated: 2026-01-01'
DONE_FRONTMATTER = 'type: plan\ncreated: 2026-01-01\nstage: done\ncompleted: 2026-01-02'


@pytest.fixture
def plans_dir(tmp_path: Path) -> Path:
    """Provide an empty plans directory independent of this repository."""
    return tmp_path / 'plans'


def test_done_plan_with_unchecked_task_is_a_violation(plans_dir: Path) -> None:
    """A shipped plan cannot still be carrying open work."""
    path = write_plan(
        plans_dir,
        '20260101-done-open',
        DONE_FRONTMATTER,
        '# Done with an open task\n'
        '\n'
        '## Implementation Steps\n'
        '\n'
        '- [x] **1. Land the code.**\n'
        '- [ ] **2. Push the branch.**\n',
    )

    violations = check_plan(path, path.read_text(encoding='utf-8'))

    assert [(v.line, v.rule) for v in violations] == [
        (line_of(path, '2. Push the branch.'), RULE_COMPLETENESS)
    ]


def test_ticked_task_needs_no_evidence_line(plans_dir: Path) -> None:
    """The evidence of a tick is in the commit that ticks it, not in the plan."""
    path = write_plan(
        plans_dir,
        '20260101-no-evidence',
        ACTIVE_FRONTMATTER,
        '# No evidence\n\n## Implementation Steps\n\n- [x] **1. Push the branch.**\n',
    )

    assert check_plan(path, path.read_text(encoding='utf-8')) == []


def test_checkboxes_outside_implementation_steps_are_not_tasks(plans_dir: Path) -> None:
    """The format example under `## Approach` documents the rule, it is not a task."""
    path = write_plan(
        plans_dir,
        '20260101-approach-example',
        DONE_FRONTMATTER,
        '# Approach example\n'
        '\n'
        '## Approach\n'
        '\n'
        '- [ ] **3. Sync with `--locked`.** Illustrative, not a task.\n'
        '\n'
        '## Implementation Steps\n'
        '\n'
        '- [x] **1. Push the branch.**\n',
    )

    assert check_plan(path, path.read_text(encoding='utf-8')) == []


def test_fenced_checkbox_inside_implementation_steps_is_ignored(plans_dir: Path) -> None:
    """A checkbox quoted in a code fence is documentation, not a task."""
    path = write_plan(
        plans_dir,
        '20260101-fenced-example',
        DONE_FRONTMATTER,
        '# Fenced example\n'
        '\n'
        '## Implementation Steps\n'
        '\n'
        '- [x] **1. Document the format.** It looks like this:\n'
        '\n'
        '``` markdown\n'
        '- [ ] **9. An open box in an example.**\n'
        '```\n',
    )

    assert check_plan(path, path.read_text(encoding='utf-8')) == []


@pytest.mark.parametrize('heading', sorted(TASK_SECTIONS))
def test_both_task_section_headings_are_audited(plans_dir: Path, heading: str) -> None:
    """Plans predating `## Implementation Steps` use `## Tasks` and still count."""
    path = write_plan(
        plans_dir,
        '20260101-heading',
        DONE_FRONTMATTER,
        f'# Heading variant\n\n## {heading}\n\n- [ ] **1. Push the branch.**\n',
    )

    violations = check_plan(path, path.read_text(encoding='utf-8'))

    assert [(v.line, v.rule) for v in violations] == [
        (line_of(path, '1. Push the branch.'), RULE_COMPLETENESS)
    ]


def test_every_violation_is_reported_not_just_the_first(plans_dir: Path) -> None:
    """A session fixing one breach must be able to see the rest."""
    path = write_plan(
        plans_dir,
        '20260101-many',
        DONE_FRONTMATTER,
        '# Many breaches\n'
        '\n'
        '## Implementation Steps\n'
        '\n'
        '- [ ] **1. First.**\n'
        '- [x] **2. Second.**\n'
        '- [ ] **3. Third.**\n',
    )

    violations = check_plan(path, path.read_text(encoding='utf-8'))

    assert [v.line for v in violations] == [
        line_of(path, '1. First.'),
        line_of(path, '3. Third.'),
    ]
    assert all(str(v).startswith(f'{path}:') for v in violations)


def test_check_directory_spans_every_plan(plans_dir: Path) -> None:
    """The gate runs over the directory, not one file a session remembered."""
    write_plan(
        plans_dir,
        '20260101-clean',
        DONE_FRONTMATTER,
        '# Clean\n\n## Implementation Steps\n\n- [x] **1. Land it.**\n',
    )
    write_plan(
        plans_dir,
        '20260102-dirty',
        DONE_FRONTMATTER,
        '# Dirty\n\n## Implementation Steps\n\n- [ ] **1. Land it.**\n',
    )

    violations = check_directory(plans_dir)

    assert [(v.path.name, v.rule) for v in violations] == [
        ('20260102-dirty.md', RULE_COMPLETENESS)
    ]


def test_repository_plans_satisfy_the_checkbox_rules() -> None:
    """Every plan in this workspace obeys the rule it defines."""
    violations = check_directory(PLANS_DIR)

    assert not violations, 'plan checkbox violations:\n' + '\n'.join(
        str(violation) for violation in violations
    )
