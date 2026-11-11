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


def check(path: Path) -> list[str]:
    """Return every violation in one document, formatted ``path:line message``."""
    lines = path.read_text(encoding='utf-8').splitlines()
    kind = frontmatter(lines).get('type')
    violations = check_bug(lines) if kind == 'bug' else []
    return [f'{path}:{line} {message}' for line, message in violations]


def main(argv: list[str]) -> int:
    """Check every path given and report all violations."""
    violations = [violation for arg in argv for violation in check(Path(arg))]
    for violation in violations:
        print(violation)
    return 1 if violations else 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
