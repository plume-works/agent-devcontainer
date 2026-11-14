#!/usr/bin/env python3
"""
Gate the records Ship leaves in the knowledge graph.

Checks each bug, plan, backlog task, feature, ADR, and release document named on the command line,
prints every violation as ``path:line message``, and exits 1 when there is any. The rules: see
spec/pre-commit-gate and spec/iwe-workflow-skills.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import re
import sys

FENCE = re.compile(r'^\s*(```|~~~)')
FRONTMATTER_FIELD = re.compile(r'^(?P<key>[\w-]+):\s*(?P<value>.*?)\s*$')
HEADING = re.compile(r'^(?P<level>#{1,6})\s')
ITEM = re.compile(r'^- \[(?P<tick>.)\] (?P<text>.+?) — (?P<ending>.*)$')
LINK = re.compile(r'(?<!!)\[[^\]]*\]\([^)\s]+\)')
CLOSED = frozenset({'done', 'cancelled'})
LIVE_FEATURE = frozenset({'proposed', 'accepted'})
LIVE_ADR = frozenset({'proposed', 'accepted'})


class Item:
    """One Ship review item: its text and the endings it may take."""

    def __init__(self, text: str, *, evidence: bool = True, not_applicable: bool = True) -> None:
        self.text = text
        self.evidence = evidence
        self.not_applicable = not_applicable


class Structure:
    """One fixed Ship review structure: its first line, the words at the end of its items, and its items."""

    def __init__(self, opening: str, items: tuple[Item, ...], *, holds: str, absent: str) -> None:
        self.opening = opening
        parts = map(re.escape, opening.split('<YYYY-MM-DD>'))
        self.reviewer = re.compile('^' + r'\d{4}-\d{2}-\d{2}'.join(parts) + '$')
        self.items = items
        self.holds = holds
        self.absent = absent

    def ending_error(self, item: Item, ending: str) -> str | None:
        """Return why an item's ending is malformed, or None when it is well formed."""
        absent = re.escape(self.absent)
        if item.not_applicable and re.fullmatch(rf'{absent}: \S.*', ending):
            return None
        if ending.startswith(self.absent):
            if not item.not_applicable:
                return f'never takes `{self.absent}`'
            return f'must be `{self.absent}: <reason>`'
        if item.evidence and re.fullmatch(rf'{re.escape(self.holds)}: \S.*', ending):
            return None
        if not item.evidence and ending == self.holds:
            return None
        shape = f'`{self.holds}: <evidence>`' if item.evidence else f'`{self.holds}`'
        return f'must end in {shape}' + (
            f' or `{self.absent}: <reason>`' if item.not_applicable else ''
        )


SHIP_REVIEW = Structure(
    '`iwe-ship-reviewer` did this review on <YYYY-MM-DD>.',
    (
        Item('Verify found no CRITICAL problem', not_applicable=False),
        Item('Every ADR that the plan proposed is `stage: accepted`'),
        Item('Every ADR that the plan superseded is `stage: superseded` and in the archive'),
        Item('The plan is `stage: done` with `completed` and no `rank`', not_applicable=False),
        Item('Every feature in `release` is `stage: implemented`'),
        Item('Every bug in `release` is `stage: done` with no `rank`'),
        Item('Every bug in `release` has a `## Fix` that links this plan'),
        Item(
            'The plan and every feature and bug that it completed are in the archive, '
            'and no hub links them',
            not_applicable=False,
        ),
    ),
    holds='correct',
    absent='not applicable',
)
OLD_OPENING = 'Reviewed by `iwe-ship-reviewer` on <YYYY-MM-DD>.'
ADR_ITEMS = (
    Item('Verify reported zero CRITICAL', not_applicable=False),
    Item('Every ADR the plan proposed is `stage: accepted`'),
    Item('Every ADR the plan superseded is `stage: superseded` and archived'),
    Item('The plan is `stage: done` with `completed` and no `rank`', not_applicable=False),
    Item('Every feature in `release` is `stage: implemented`'),
    Item('Every bug in `release` is `stage: done` with no `rank`'),
    Item('Every bug in `release` has a `## Fix` that links this plan'),
    Item(
        'The plan and every feature and bug it closed are archived with no hub link',
        not_applicable=False,
    ),
)
SPEC_ITEMS = (
    ADR_ITEMS[0],
    Item('Every `## Spec changes` operation is in its spec'),
    Item('Every spec the plan created is linked from `data/spec.md`'),
    Item('Every spec the plan retired was removed with `iwe delete`'),
    *ADR_ITEMS[3:7],
    Item('Every `## Rationale` entry the plan names is in its spec'),
    ADR_ITEMS[7],
)
EARLIEST_ITEMS = (
    *SPEC_ITEMS[:-2],
    Item(
        'Ship edited no hub, release page, or `data/log.md`', evidence=False, not_applicable=False
    ),
)
EARLIER_STRUCTURES = tuple(
    Structure(OLD_OPENING, items, holds='confirmed', absent='N/A')
    for items in (ADR_ITEMS, SPEC_ITEMS, EARLIEST_ITEMS)
)


def frontmatter(lines: list[str]) -> dict[str, str]:
    """Return the top-level scalar fields of the document's YAML frontmatter."""
    if not lines or lines[0].strip() != '---':
        return {}
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == '---':
            break
        match = FRONTMATTER_FIELD.match(line)
        if match:
            fields[match['key']] = match['value']
    return fields


def body_lines(lines: list[str]) -> Iterator[tuple[int, str]]:
    """Yield ``(line number, line)`` for each body line outside fenced code blocks."""
    start = 0
    if lines and lines[0].strip() == '---':
        start = next((i + 1 for i in range(1, len(lines)) if lines[i].strip() == '---'), 0)
    fenced = False
    for index in range(start, len(lines)):
        line = lines[index]
        if FENCE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            yield index + 1, line


def check_bug(lines: list[str]) -> list[tuple[int, str]]:
    """Return the violations of a bug document: a done bug needs a Fix section."""
    if frontmatter(lines).get('stage') != 'done':
        return []
    if any(line.rstrip() == '## Fix' for _, line in body_lines(lines)):
        return []
    return [(1, 'bug is at stage: done but has no `## Fix` section')]


def ship_review(lines: list[str]) -> tuple[int, list[tuple[int, str]]] | None:
    """
    Return the Ship review heading's line and its logical lines, or None without one.

    An indented line continues the line above it, as `iwe normalize` wraps a long item.
    """
    heading = None
    section: list[tuple[int, str]] = []
    for number, line in body_lines(lines):
        match = HEADING.match(line)
        if heading is None:
            if line.rstrip() == '## Ship review':
                heading = number
        elif match and len(match['level']) <= 2:
            break
        elif section and line[:1].isspace() and line.strip():
            start, text = section[-1]
            section[-1] = (start, f'{text} {line.strip()}')
        elif line.strip():
            section.append((number, line.rstrip()))
    return None if heading is None else (heading, section)


def check_item(structure: Structure, item: Item, line: str) -> str | None:
    """Return why one item line differs from the expected item, or None when it matches."""
    match = ITEM.match(line)
    if not match:
        return f'expected item "{item.text}", found a line that is not a review item'
    if match['text'] != item.text:
        return f'expected item "{item.text}", found "{match["text"]}"'
    if match['tick'] != 'x':
        return f'item "{item.text}" is not ticked'
    error = structure.ending_error(item, match['ending'])
    return None if error is None else f'item "{item.text}" {error}'


def check_plan(lines: list[str]) -> list[tuple[int, str]]:
    """
    Return the violations of a plan's Ship review against the fixed structure.

    A review that matches one of the earlier structures passes; otherwise the
    violations reported are those against the current one.
    """
    found = ship_review(lines)
    if found is None:
        return []
    violations = check_structure(*found, SHIP_REVIEW)
    if violations and any(not check_structure(*found, e) for e in EARLIER_STRUCTURES):
        return []
    return violations


def check_structure(
    heading: int, section: list[tuple[int, str]], structure: Structure
) -> list[tuple[int, str]]:
    """Return the violations of a Ship review's lines against one fixed structure."""
    violations: list[tuple[int, str]] = []
    expected = structure.items
    items = section
    if section and structure.reviewer.match(section[0][1]):
        items = section[1:]
    else:
        line = section[0][0] if section else heading
        violations.append((line, f'Ship review must open with "{structure.opening}"'))
        if section and not ITEM.match(section[0][1]):
            items = section[1:]
    for item, (number, line) in zip(expected, items, strict=False):
        error = check_item(structure, item, line)
        if error:
            violations.append((number, error))
    for item in expected[len(items) :]:
        violations.append((heading, f'Ship review is missing item "{item.text}"'))
    for number, _ in items[len(expected) :]:
        violations.append((number, 'Ship review has a line after its last item'))
    return violations


def archived(path: Path) -> bool:
    """Return whether ``path`` lies under the knowledge base's ``data/archive/``."""
    parts = path.parts
    return any(parts[i : i + 2] == ('data', 'archive') for i in range(len(parts) - 1))


def check_placement(kind: str, stage: str, inside: bool) -> list[tuple[int, str]]:
    """Return a violation when a work item, feature, or ADR is on the wrong side of the archive."""
    if kind == 'feature':
        live = stage in LIVE_FEATURE
    elif kind == 'adr':
        live = stage in LIVE_ADR
    elif kind in ('plan', 'bug', 'task'):
        live = stage not in CLOSED
    else:
        return []
    if inside and live:
        return [(1, f'{kind} at {stage or "no stage"} is open but sits in data/archive/')]
    if not inside and not live:
        return [(1, f'{kind} at stage: {stage} is closed but sits outside data/archive/')]
    return []


def check_release(lines: list[str]) -> list[tuple[int, str]]:
    """Return one violation per release-page line that holds a Markdown link."""
    return [
        (number, 'release page holds a Markdown link; write its text instead')
        for number, line in body_lines(lines)
        if LINK.search(line)
    ]


def check(path: Path) -> list[str]:
    """Return every violation in one document, formatted ``path:line message``."""
    lines = path.read_text(encoding='utf-8').splitlines()
    fields = frontmatter(lines)
    kind = fields.get('type', '')
    violations = check_placement(kind, fields.get('stage', ''), archived(path))
    if kind == 'bug':
        violations += check_bug(lines)
    elif kind == 'plan':
        violations += check_plan(lines)
    elif kind == 'release':
        violations += check_release(lines)
    return [f'{path}:{line} {message}' for line, message in violations]


def main(argv: list[str]) -> int:
    """Check every path given and report all violations."""
    violations = [violation for arg in argv for violation in check(Path(arg))]
    for violation in violations:
        print(violation)
    return 1 if violations else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
