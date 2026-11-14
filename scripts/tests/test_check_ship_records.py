"""Tests for scripts/check-ship-records.py run against made-up bug and plan documents."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
import re
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


CLOSED_STAGE = re.compile(r'^stage: (done|cancelled)$', re.M)


@pytest.fixture
def write_at(tree: Path) -> Write:
    """Return a helper that writes a document at a path relative to the tree."""

    def _write(relative: str, text: str) -> Path:
        path = tree / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        return path

    return _write


@pytest.fixture
def write(write_at: Write) -> Write:
    """Return a helper that writes a document where it belongs: closed ones in the archive."""

    def _write(name: str, text: str) -> Path:
        folder = 'data/archive/1.0.0/items' if CLOSED_STAGE.search(text) else 'data/items'
        return write_at(f'{folder}/{name}', text)

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

`iwe-ship-reviewer` did this review on 2026-11-14.

- [x] Verify found no CRITICAL problem — correct: PASS, 0 CRITICAL
- [x] Every ADR that the plan proposed is `stage: accepted` — correct: data/adr/0001-example
- [x] Every ADR that the plan superseded is `stage: superseded` and in the archive — not applicable: the plan superseded no ADR
- [x] The plan is `stage: done` with `completed` and no `rank` — correct: 2026-11-14
- [x] Every feature in `release` is `stage: implemented` — not applicable: `release` lists no feature
- [x] Every bug in `release` is `stage: done` with no `rank` — correct: data/bugs/example
- [x] Every bug in `release` has a `## Fix` that links this plan — correct: data/bugs/example
- [x] The plan and every feature and bug that it completed are in the archive, and no hub links them — correct: data/archive/next-release/plans/example
"""

ADR_REVIEW = """## Ship review

Reviewed by `iwe-ship-reviewer` on 2026-11-13.

- [x] Verify reported zero CRITICAL — confirmed: PASS, 0 CRITICAL
- [x] Every ADR the plan proposed is `stage: accepted` — confirmed: data/adr/0001-example
- [x] Every ADR the plan superseded is `stage: superseded` and archived — N/A: the plan superseded no ADR
- [x] The plan is `stage: done` with `completed` and no `rank` — confirmed: 2026-11-13
- [x] Every feature in `release` is `stage: implemented` — N/A: `release` lists no feature
- [x] Every bug in `release` is `stage: done` with no `rank` — confirmed: data/bugs/example
- [x] Every bug in `release` has a `## Fix` that links this plan — confirmed: data/bugs/example
- [x] The plan and every feature and bug it closed are archived with no hub link — confirmed: data/archive/next-release/plans/example
"""

SPEC_REVIEW = """## Ship review

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
    SPEC_REVIEW.split('- [x] Every `## Rationale`')[0]
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


def test_spec_ship_review_passes(write: Write) -> None:
    """A Ship review in the structure that has spec and rationale items passes."""
    result = run(write('plan.md', plan(SPEC_REVIEW)))
    assert (result.returncode, result.stdout) == (0, '')


def test_spec_ship_review_still_fails_when_malformed(write: Write) -> None:
    """A spec-structure review with an unticked item fails against the current one."""
    text = plan(SPEC_REVIEW.replace('- [x] Every `## Rationale`', '- [ ] Every `## Rationale`'))
    result = run(write('plan.md', text))
    assert result.returncode == 1
    assert 'Every ADR that the plan proposed' in result.stdout


def test_adr_ship_review_passes(write: Write) -> None:
    """A Ship review in the structure whose items end with `confirmed` or `N/A` passes."""
    result = run(write('plan.md', plan(ADR_REVIEW)))
    assert (result.returncode, result.stdout) == (0, '')


def test_adr_ship_review_still_fails_when_malformed(write: Write) -> None:
    """An ADR-structure review that has an item with no tick fails, and the output names the new structure."""
    text = plan(ADR_REVIEW.replace('- [x] Every feature', '- [ ] Every feature'))
    result = run(write('plan.md', text))
    assert result.returncode == 1
    assert 'did this review on' in result.stdout


def test_old_endings_in_the_current_structure_fail(write: Write) -> None:
    """The items of the new structure fail when they end with `confirmed` or `N/A`."""
    text = plan(
        REVIEW.replace('— correct:', '— confirmed:').replace('— not applicable:', '— N/A:')
    )
    result = run(write('plan.md', text))
    assert result.returncode == 1
    assert 'must end in `correct: <evidence>`' in result.stdout


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
    text = plan(
        ''.join(line for line in REVIEW.splitlines(True) if 'in the archive, and' not in line)
    )
    result = run(path := write('plan.md', text))
    assert result.returncode == 1
    assert f'{path}:{line_of(text, "## Ship review")} ' in result.stdout
    assert 'missing item "The plan and every feature and bug that it completed' in result.stdout


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
        REVIEW.replace(
            '- [x] Every ADR that the plan superseded', '- [ ] Every ADR that the plan superseded'
        )
    )
    result = run(path := write('plan.md', text))
    assert result.returncode == 1
    assert f'{path}:{line_of(text, "plan superseded")} ' in result.stdout
    assert 'not ticked' in result.stdout


def test_item_with_neither_ending_fails(write: Write) -> None:
    """An item that ends in neither `correct:` nor `not applicable:` fails, and the output names its line."""
    text = plan(REVIEW.replace('— correct: data/adr/0001-example', '— looks fine'))
    result = run(path := write('plan.md', text))
    assert result.returncode == 1
    assert f'{path}:{line_of(text, "plan proposed")} ' in result.stdout


@pytest.mark.parametrize(
    ('needle', 'ending'),
    [
        ('Verify found', '— correct: PASS, 0 CRITICAL'),
        ('The plan is `stage: done`', '— correct: 2026-11-14'),
        ('no hub links them', '— correct: data/archive/next-release/plans/example'),
    ],
)
def test_na_on_a_mandatory_item_fails(write: Write, needle: str, ending: str) -> None:
    """The Verify, plan-stage, and archive items can never be `not applicable`."""
    review = ''.join(
        line.replace(ending, '— not applicable: skipped') if needle in line else line
        for line in REVIEW.splitlines(True)
    )
    text = plan(review)
    result = run(path := write('plan.md', text))
    assert result.returncode == 1
    assert f'{path}:{line_of(text, needle)} ' in result.stdout
    assert 'never takes `not applicable`' in result.stdout


def test_missing_reviewer_line_fails(write: Write) -> None:
    """A Ship review without its reviewer line fails."""
    text = plan(REVIEW.replace('`iwe-ship-reviewer` did this review on 2026-11-14.\n', ''))
    result = run(write('plan.md', text))
    assert result.returncode == 1
    assert 'did this review on' in result.stdout
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


def item(kind: str, stage: str | None) -> str:
    """Return a minimal document of ``kind`` at ``stage`` (no stage when None)."""
    line = '' if stage is None else f'stage: {stage}\n'
    fix = '\n## Fix\n\nFixed.\n' if kind == 'bug' else ''
    return f'---\ntype: {kind}\n{line}---\n\n# Example\n{fix}'


@pytest.mark.parametrize(
    ('kind', 'stage'),
    [('plan', 'done'), ('plan', 'cancelled'), ('bug', 'done'), ('task', 'cancelled')],
)
def test_closed_item_outside_the_archive_fails(write_at: Write, kind: str, stage: str) -> None:
    """A closed plan, bug, or task left outside data/archive/ fails, naming the document."""
    path = write_at(f'docs/knowledge/data/{kind}s/example.md', item(kind, stage))
    result = run(path)
    assert result.returncode == 1
    assert f'{path}:1 ' in result.stdout
    assert 'outside data/archive/' in result.stdout


@pytest.mark.parametrize(
    ('kind', 'stage'),
    [('plan', None), ('bug', 'pending'), ('bug', 'planned'), ('task', 'pending')],
)
def test_open_item_inside_the_archive_fails(write_at: Write, kind: str, stage: str | None) -> None:
    """An active plan, or an open bug or task, inside data/archive/ fails."""
    path = write_at(f'docs/knowledge/data/archive/next-release/{kind}s/x.md', item(kind, stage))
    result = run(path)
    assert result.returncode == 1
    assert 'sits in data/archive/' in result.stdout


@pytest.mark.parametrize(
    ('folder', 'stage', 'fails'),
    [
        ('features', 'implemented', True),
        ('features', 'deprecated', True),
        ('features', 'accepted', False),
        ('archive/1.0.0/features', 'proposed', True),
        ('archive/1.0.0/features', 'implemented', False),
    ],
)
def test_feature_placement_follows_its_stage(
    write_at: Write, folder: str, stage: str, fails: bool
) -> None:
    """A feature is live only at proposed or accepted, and archived at any other stage."""
    path = write_at(f'docs/knowledge/data/{folder}/x.md', item('feature', stage))
    assert run(path).returncode == (1 if fails else 0)


@pytest.mark.parametrize(
    ('folder', 'stage', 'fails'),
    [
        ('adr', 'proposed', False),
        ('adr', 'accepted', False),
        ('adr', 'rejected', True),
        ('adr', 'deprecated', True),
        ('adr', 'superseded', True),
        ('archive/next-release/adr', 'proposed', True),
        ('archive/next-release/adr', 'accepted', True),
        ('archive/next-release/adr', 'rejected', False),
        ('archive/next-release/adr', 'deprecated', False),
        ('archive/next-release/adr', 'superseded', False),
    ],
)
def test_adr_placement_follows_its_stage(
    write_at: Write, folder: str, stage: str, fails: bool
) -> None:
    """An ADR at proposed or accepted is live; an ADR at another stage is in the archive."""
    path = write_at(f'docs/knowledge/data/{folder}/0001-x.md', item('adr', stage))
    result = run(path)
    assert result.returncode == (1 if fails else 0)
    if fails:
        assert f'{path}:1 adr at ' in result.stdout


def test_release_page_with_a_link_fails_naming_the_line(write_at: Write) -> None:
    """A release page holding a Markdown link fails at that line; plain text passes."""
    text = '---\ntype: release\nstage: released\n---\n\n# 1.0.0\n\n## Added\n\n[Focus](../features/focus.md)\n'
    path = write_at('docs/knowledge/data/releases/1.0.0.md', text)
    result = run(path)
    assert result.returncode == 1
    assert f'{path}:{line_of(text, "[Focus]")} ' in result.stdout
    path.write_text(text.replace('[Focus](../features/focus.md)', 'Focus sessions'))
    assert run(path).returncode == 0
