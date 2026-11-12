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


REVIEW = """## Ship review

Reviewed by `iwe-ship-reviewer` on 2026-11-11.

- [x] Verify reported zero CRITICAL — confirmed: PASS, 0 CRITICAL
- [x] Every `## Spec changes` operation is in its spec — confirmed: data/spec/example
- [x] Every spec the plan created is linked from `data/spec.md` — N/A: no spec created
- [x] Every spec the plan retired was removed with `iwe delete` — N/A: no spec retired
- [x] The plan is `stage: done` with `completed` and no `rank` — confirmed: 2026-11-11
- [x] Every feature in `release` is `stage: implemented` — N/A: `release` lists no feature
- [x] Every bug in `release` is `stage: done` with no `rank` — confirmed: data/bugs/example
- [x] Every bug in `release` has a `## Fix` that links this plan — confirmed: data/bugs/example
- [x] Every `## Rationale` entry the plan names is in its spec — confirmed: data/spec/example
- [x] The plan and every feature and bug it closed are archived with no hub link — confirmed: data/archive/next-release/plans/example
"""

EARLIER_REVIEW = (
    REVIEW.split('- [x] Every `## Rationale`')[0]
    + '- [x] Ship edited no hub, release page, or `data/log.md` — confirmed\n'
)

PLAN_HEAD = '---\ntype: plan\nstage: done\n---\n\n# Example plan\n\n## Context\n\nWhy.\n\n'


def plan(review: str = REVIEW) -> str:
    """Return a plan document whose Ship review section is the given text."""
    return PLAN_HEAD + review


def line_of(text: str, needle: str) -> int:
    """Return the 1-based line number of the first line in text containing needle."""
    return next(i for i, line in enumerate(text.splitlines(), 1) if needle in line)


def test_plan_without_ship_review_passes(write: Write) -> None:
    """A plan with no Ship review section passes."""
    result = run(write('plan.md', PLAN_HEAD))
    assert (result.returncode, result.stdout) == (0, '')


def test_well_formed_ship_review_passes(write: Write) -> None:
    """A Ship review in the fixed structure passes, followed by another section."""
    result = run(write('plan.md', plan() + '\n## Verification results\n\nAll green.\n'))
    assert (result.returncode, result.stdout) == (0, '')


def test_earlier_ship_review_passes(write: Write) -> None:
    """A Ship review stamped in the earlier structure, ending with the hub item, passes."""
    result = run(write('plan.md', plan(EARLIER_REVIEW)))
    assert (result.returncode, result.stdout) == (0, '')


def test_earlier_ship_review_still_fails_when_malformed(write: Write) -> None:
    """An earlier-structure review with an unticked item fails against the current one."""
    text = plan(EARLIER_REVIEW.replace('- [x] Ship edited', '- [ ] Ship edited'))
    result = run(write('plan.md', text))
    assert result.returncode == 1


def test_ship_review_inside_a_code_fence_is_not_checked(write: Write) -> None:
    """A Ship review quoted in a fenced block, as a plan quotes its template, is skipped."""
    text = PLAN_HEAD + '```markdown\n' + REVIEW.replace('[x]', '[ ]') + '```\n'
    assert run(write('plan.md', text)).returncode == 0


def test_missing_item_fails_naming_the_section(write: Write) -> None:
    """A Ship review missing its last item fails and names the missing item."""
    text = plan(''.join(line for line in REVIEW.splitlines(True) if 'archived with' not in line))
    result = run(path := write('plan.md', text))
    assert result.returncode == 1
    assert f'{path}:{line_of(text, "## Ship review")} ' in result.stdout
    assert 'missing item "The plan and every feature and bug it closed' in result.stdout


def test_reordered_items_fail_naming_the_line(write: Write) -> None:
    """Two swapped items fail, each naming its line."""
    lines = REVIEW.splitlines(True)
    first = line_of(REVIEW, 'Every feature')
    lines[first - 1], lines[first] = lines[first], lines[first - 1]
    text = plan(''.join(lines))
    result = run(path := write('plan.md', text))
    assert result.returncode == 1
    assert f'{path}:{line_of(text, "Every bug in `release` is")} ' in result.stdout
    assert f'{path}:{line_of(text, "Every feature")} ' in result.stdout


def test_unticked_item_fails_naming_the_line(write: Write) -> None:
    """An unticked item fails, naming its line."""
    text = plan(
        REVIEW.replace('- [x] Every spec the plan retired', '- [ ] Every spec the plan retired')
    )
    result = run(path := write('plan.md', text))
    assert result.returncode == 1
    assert f'{path}:{line_of(text, "plan retired")} ' in result.stdout
    assert 'not ticked' in result.stdout


def test_item_with_neither_ending_fails(write: Write) -> None:
    """An item ending in neither `confirmed` nor `N/A:` fails, naming its line."""
    text = plan(REVIEW.replace('— confirmed: data/spec/example', '— looks fine'))
    result = run(path := write('plan.md', text))
    assert result.returncode == 1
    assert f'{path}:{line_of(text, "Spec changes")} ' in result.stdout


@pytest.mark.parametrize(
    ('needle', 'ending'),
    [
        ('Verify reported', '— confirmed: PASS, 0 CRITICAL'),
        ('The plan is `stage: done`', '— confirmed: 2026-11-11'),
        ('archived with no hub link', '— confirmed: data/archive/next-release/plans/example'),
    ],
)
def test_na_on_a_mandatory_item_fails(write: Write, needle: str, ending: str) -> None:
    """The Verify, plan-stage, and archive items never take `N/A`."""
    review = ''.join(
        line.replace(ending, '— N/A: skipped') if needle in line else line
        for line in REVIEW.splitlines(True)
    )
    text = plan(review)
    result = run(path := write('plan.md', text))
    assert result.returncode == 1
    assert f'{path}:{line_of(text, needle)} ' in result.stdout
    assert 'never takes `N/A`' in result.stdout


def test_missing_reviewer_line_fails(write: Write) -> None:
    """A Ship review without its reviewer line fails."""
    text = plan(REVIEW.replace('Reviewed by `iwe-ship-reviewer` on 2026-11-11.\n', ''))
    result = run(write('plan.md', text))
    assert result.returncode == 1
    assert 'Reviewed by' in result.stdout
    assert 'expected item' not in result.stdout


def wrap(review: str) -> str:
    """Return the review with each item longer than 80 columns wrapped as `iwe normalize` does."""
    wrapped = []
    for line in review.splitlines():
        if line.startswith('- [') and len(line) > 80:
            cut = line.rindex(' ', 0, 81)
            wrapped += [line[:cut], f'  {line[cut + 1 :]}']
        else:
            wrapped.append(line)
    return '\n'.join(wrapped) + '\n'


def test_wrapped_items_pass(write: Write) -> None:
    """Items wrapped onto an indented continuation line pass, as `iwe normalize` leaves them."""
    text = plan(wrap(REVIEW))
    assert any(line.startswith('  ') for line in text.splitlines())
    result = run(write('plan.md', text))
    assert (result.returncode, result.stdout) == (0, '')


def test_wrapped_unticked_item_fails_naming_its_first_line(write: Write) -> None:
    """A wrapped item that breaks a rule is reported at the line the item starts on."""
    text = plan(
        wrap(
            REVIEW.replace('- [x] Every bug in `release` has', '- [ ] Every bug in `release` has')
        )
    )
    result = run(path := write('plan.md', text))
    assert result.returncode == 1
    assert f'{path}:{line_of(text, "- [ ] Every bug in `release` has")} ' in result.stdout
