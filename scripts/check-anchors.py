#!/usr/bin/env python3
"""
Reject line-number references in the knowledge graph and the agentdev catalog.

Lists every violation as ``path:line [rule] message`` and exits 1 when there is any.
See spec/line-free-anchors.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys

SCAN_GLOBS = (
    'docs/knowledge/data/**/*.md',
    '.agents/plugins/agentdev/skills/**/*.md',
    '.agents/plugins/agentdev/agents/**/*.md',
)

LINE_NUMBER_FORMS = (
    re.compile(r'[\w./-]*[\w-]\.[A-Za-z][A-Za-z0-9]{0,4}:\d+'),
    re.compile(r'[\w./-]*(?:Dockerfile|Makefile|Containerfile)[\w.-]*:\d+'),
    re.compile(r'#L\d+'),
    re.compile(r'\blines? \d+', re.IGNORECASE),
)


@dataclass(frozen=True)
class Violation:
    """One rule breach in one scanned document."""

    path: Path
    line: int
    rule: str
    message: str

    def __str__(self) -> str:
        """Render as ``path:line [rule] message``."""
        return f'{self.path}:{self.line} [{self.rule}] {self.message}'


def scanned_files(root: Path) -> list[Path]:
    """Return every Markdown file the line-number gate scans, sorted."""
    return sorted({path for pattern in SCAN_GLOBS for path in root.glob(pattern)})


def line_number_violations(root: Path, path: Path) -> list[Violation]:
    """Return one violation per line-number reference in ``path``."""
    found = []
    for number, text in enumerate(path.read_text().splitlines(), start=1):
        matches = {m.end(): m.group(0) for form in LINE_NUMBER_FORMS for m in form.finditer(text)}
        found.extend(
            Violation(
                path.relative_to(root),
                number,
                'line-number',
                f'`{reference}` records a line number; use an anchor',
            )
            for _, reference in sorted(matches.items())
        )
    return found


def main(argv: list[str]) -> int:
    """Check the tree rooted at ``argv[0]`` (default: the current directory)."""
    root = Path(argv[0] if argv else '.').resolve()
    violations = [v for path in scanned_files(root) for v in line_number_violations(root, path)]
    for violation in violations:
        print(violation)
    return 1 if violations else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
