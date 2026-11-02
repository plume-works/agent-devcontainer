#!/usr/bin/env python3

"""
Check a candidate pull request body's ``## Depends on`` section before it is applied.

The section must stay readable and editable by the parser pr-restack-all uses.
Standard library only.
"""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import depends_on  # noqa: E402  (path set above so the plugin's bin/ resolves)
import result_codes as rc  # noqa: E402
from skill_common import print_error, Stop  # noqa: E402

PREFLIGHT_ERROR = 2
NO_SECTION = 3
UNPARSEABLE = 4
SECTION_CHANGED = 5
ENTRIES_MISMATCH = 6

USAGE = """\
Check a candidate pull request body's '## Depends on' section before it is applied.

Usage:
  check_depends_on.py <body-file|-> [--current <body-file>] [--depends-on <pr>]...

  <body-file|->           The candidate body; '-' reads it from stdin
  --current <body-file>   The body the pull request has now. When it carries a
                          section, the candidate must carry it byte-for-byte
  --depends-on <pr>       Repeatable. The section is required and must list
                          exactly these pull requests, in this order
  -h, --help              Show this help text.

A body without the section passes unless --depends-on or --current requires one.

Results (RESULT / exit code):
  SUCCESS           0  The body can be applied
  PREFLIGHT_ERROR   2  Bad usage or an unreadable file
  NO_SECTION        3  A required '## Depends on' section is missing
  UNPARSEABLE       4  The section has no entry, a list item that is not an
                       entry, a repeated entry, or an entry that cannot be rewritten
  SECTION_CHANGED   5  The section differs from the current body's
  ENTRIES_MISMATCH  6  The entries differ from --depends-on
"""


def section_text(body: str, section: depends_on.Section) -> str:
    """Return the section's lines, without trailing blank lines."""
    lines = body.splitlines(keepends=True)[section.heading : section.end]
    while lines and not lines[-1].strip():
        lines.pop()
    return ''.join(lines)


def check(candidate: str, current: str | None, expected: list[int]) -> int:
    """Return the result code for `candidate`, printing why it fails."""
    section = depends_on.find_section(candidate)
    current_section = depends_on.find_section(current) if current is not None else None
    if section is None:
        if expected or current_section is not None:
            print_error(f'The body has no {depends_on.HEADING} section.')
            return NO_SECTION
        return 0
    lines = candidate.splitlines()
    if not section.entries:
        print_error(f'{depends_on.HEADING} lists no "- #<number>" entry.')
        return UNPARSEABLE
    for index in section.invalid:
        print_error(f'{depends_on.HEADING} holds a list item that is not an entry: {lines[index]}')
        return UNPARSEABLE
    for entry in section.entries:
        try:
            depends_on.record_merge(candidate, entry.number, '0' * 8, '0' * 8)
        except depends_on.DependsOnError as failure:
            print_error(str(failure))
            return UNPARSEABLE
    if current_section is not None:
        if section_text(candidate, section) != section_text(current, current_section):
            print_error(f"{depends_on.HEADING} differs from the pull request's current one.")
            return SECTION_CHANGED
    numbers = [entry.number for entry in section.entries]
    if expected and numbers != expected:
        print_error(f'{depends_on.HEADING} lists {numbers}, not {expected}.')
        return ENTRIES_MISMATCH
    return 0


def read(path: str) -> str:
    """Read a body from a file, or from stdin for '-'."""
    try:
        return sys.stdin.read() if path == '-' else Path(path).read_text(encoding='utf-8')
    except OSError as failure:
        print_error(f'Cannot read {path}: {failure}')
        raise Stop(PREFLIGHT_ERROR) from failure


def run(arguments: list[str]) -> int:
    """Parse the command line and check the body."""
    body_path = ''
    current_path = ''
    expected: list[int] = []
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument in ('-h', '--help'):
            print(USAGE, end='')
            return 0
        if argument in ('--current', '--depends-on'):
            if not remaining:
                print_error(f'Missing value for {argument}')
                return PREFLIGHT_ERROR
            value = remaining.pop(0)
            if argument == '--current':
                current_path = value
            elif value.removeprefix('#').isdigit():
                expected.append(int(value.removeprefix('#')))
            else:
                print_error(f'--depends-on takes a pull request number, not {value!r}')
                return PREFLIGHT_ERROR
        elif (argument.startswith('-') and argument != '-') or body_path:
            print_error(f'Unexpected argument: {argument}')
            print(USAGE, end='', file=sys.stderr)
            return PREFLIGHT_ERROR
        else:
            body_path = argument
    if not body_path:
        print_error('Missing the candidate body.')
        print(USAGE, end='', file=sys.stderr)
        return PREFLIGHT_ERROR
    current = read(current_path) if current_path else None
    return check(read(body_path), current, expected)


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES.update(
        {
            NO_SECTION: 'NO_SECTION',
            UNPARSEABLE: 'UNPARSEABLE',
            SECTION_CHANGED: 'SECTION_CHANGED',
            ENTRIES_MISMATCH: 'ENTRIES_MISMATCH',
        }
    )
    rc.install()
    rc.run(main)
