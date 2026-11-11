#!/usr/bin/env python3
"""
Gate the records Ship leaves in the knowledge graph.

Checks each bug and plan document named on the command line, prints every violation as
``path:line message``, and exits 1 when there is any. The rules: see spec/pre-commit-gate.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import re
import sys

FENCE = re.compile(r'^\s*(```|~~~)')
FRONTMATTER_FIELD = re.compile(r'^(?P<key>[\w-]+):\s*(?P<value>.*?)\s*$')
HEADING = re.compile(r'^(?P<level>#{1,6})\s')
REVIEWER = re.compile(r'^Reviewed by `iwe-ship-reviewer` on \d{4}-\d{2}-\d{2}\.$')
ITEM = re.compile(r'^- \[(?P<tick>.)\] (?P<text>.+?) — (?P<ending>.*)$')


class Item:
    """One Ship review item: its text and the endings it may take."""

    def __init__(self, text: str, *, evidence: bool = True, not_applicable: bool = True) -> None:
        self.text = text
        self.evidence = evidence
        self.not_applicable = not_applicable

    def ending_error(self, ending: str) -> str | None:
        """Return why an item's ending is malformed, or None when it is well formed."""
        if self.not_applicable and re.fullmatch(r'N/A: \S.*', ending):
            return None
        if ending.startswith('N/A'):
            return 'never takes `N/A`' if not self.not_applicable else 'must be `N/A: <reason>`'
        if self.evidence and re.fullmatch(r'confirmed: \S.*', ending):
            return None
        if not self.evidence and ending == 'confirmed':
            return None
        shape = '`confirmed: <evidence>`' if self.evidence else '`confirmed`'
        return f'must end in {shape}' + (' or `N/A: <reason>`' if self.not_applicable else '')


SHIP_REVIEW_ITEMS = (
    Item('Verify reported zero CRITICAL', not_applicable=False),
    Item('Every `## Spec changes` operation is in its spec'),
    Item('Every spec the plan created is linked from `data/spec.md`'),
    Item('Every spec the plan retired was removed with `iwe delete`'),
    Item('The plan is `stage: done` with `completed` and no `rank`', not_applicable=False),
    Item('Every feature in `release` is `stage: implemented`'),
    Item('Every bug in `release` is `stage: done` with no `rank`'),
    Item('Every bug in `release` has a `## Fix` that links this plan'),
    Item(
        'Ship edited no hub, release page, or `data/log.md`', evidence=False, not_applicable=False
    ),
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
    """Return the Ship review heading's line and its non-blank lines, or None without one."""
    heading = None
    section: list[tuple[int, str]] = []
    for number, line in body_lines(lines):
        match = HEADING.match(line)
        if heading is None:
            if line.rstrip() == '## Ship review':
                heading = number
        elif match and len(match['level']) <= 2:
            break
        elif line.strip():
            section.append((number, line.rstrip()))
    return None if heading is None else (heading, section)


def check_item(item: Item, line: str) -> str | None:
    """Return why one item line differs from the expected item, or None when it matches."""
    match = ITEM.match(line)
    if not match:
        return f'expected item "{item.text}", found a line that is not a review item'
    if match['text'] != item.text:
        return f'expected item "{item.text}", found "{match["text"]}"'
    if match['tick'] != 'x':
        return f'item "{item.text}" is not ticked'
    error = item.ending_error(match['ending'])
    return None if error is None else f'item "{item.text}" {error}'


def check_plan(lines: list[str]) -> list[tuple[int, str]]:
    """Return the violations of a plan's Ship review section against the fixed structure."""
    found = ship_review(lines)
    if found is None:
        return []
    heading, section = found
    violations: list[tuple[int, str]] = []
    items = section
    if section and REVIEWER.match(section[0][1]):
        items = section[1:]
    else:
        line = section[0][0] if section else heading
        violations.append(
            (line, 'Ship review must open with "Reviewed by `iwe-ship-reviewer` on <YYYY-MM-DD>."')
        )
        if section and not ITEM.match(section[0][1]):
            items = section[1:]
    for item, (number, line) in zip(SHIP_REVIEW_ITEMS, items, strict=False):
        error = check_item(item, line)
        if error:
            violations.append((number, error))
    for item in SHIP_REVIEW_ITEMS[len(items) :]:
        violations.append((heading, f'Ship review is missing item "{item.text}"'))
    for number, _ in items[len(SHIP_REVIEW_ITEMS) :]:
        violations.append((number, 'Ship review has a line after its last item'))
    return violations


def check(path: Path) -> list[str]:
    """Return every violation in one document, formatted ``path:line message``."""
    lines = path.read_text(encoding='utf-8').splitlines()
    kind = frontmatter(lines).get('type')
    violations = []
    if kind == 'bug':
        violations = check_bug(lines)
    elif kind == 'plan':
        violations = check_plan(lines)
    return [f'{path}:{line} {message}' for line, message in violations]


def main(argv: list[str]) -> int:
    """Check every path given and report all violations."""
    violations = [violation for arg in argv for violation in check(Path(arg))]
    for violation in violations:
        print(violation)
    return 1 if violations else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
