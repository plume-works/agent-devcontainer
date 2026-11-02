#!/usr/bin/env python3

"""
Read and edit the dependency records of a manual stacked pull request.

A dependent pull request names its predecessors twice: as ``- #<P>`` entries in
its body's ``## Depends on`` section, and as ``Depends-on: #<P>`` trailers on
its branch's commits. Each entry's line is replaced by its merge record once the
predecessor is reconnected; every other byte of the body is kept.

Standard library only.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess
from typing import NamedTuple

HEADING = '## Depends on'

_HEADING = re.compile(r'^##[ \t]+Depends on[ \t]*$')
_SECTION_END = re.compile(r'^#{1,2}[ \t]')
_FENCE = re.compile(r'^[ \t]{0,3}(```|~~~)')
_LIST_ITEM = re.compile(r'^[-*+][ \t]')
_ENTRY = re.compile(
    r'^- #(?P<number>[0-9]+)'
    r'(?: — merged as (?P<merge>[0-9a-f]{7,40}) \(head (?P<head>[0-9a-f]{7,40})\), reconnected)?'
    r'[ \t]*$'
)
_TRAILER = re.compile(r'^#([0-9]+)$')


class DependsOnError(Exception):
    """A body or branch whose dependency records cannot be read or edited."""


class Entry(NamedTuple):
    """One ``- #<P>`` entry; `merge` and `head` are set once it carries a record."""

    number: int
    line: int
    merge: str | None
    head: str | None


class Section(NamedTuple):
    """The first ``## Depends on`` section, as line indexes into the body."""

    heading: int
    end: int
    entries: tuple[Entry, ...]
    invalid: tuple[int, ...]


def _content(line: str) -> str:
    """Return `line` without its line ending."""
    return line.rstrip('\r\n')


def find_section(body: str) -> Section | None:
    """Return the body's first ``## Depends on`` section outside a code fence, if any."""
    lines = body.splitlines(keepends=True)
    fence: str | None = None
    heading: int | None = None
    entries: list[Entry] = []
    invalid: list[int] = []
    for index, raw in enumerate(lines):
        line = _content(raw)
        fence_match = _FENCE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            fence = marker if fence is None else (None if marker == fence else fence)
            continue
        if fence is not None:
            continue
        if heading is None:
            if _HEADING.match(line):
                heading = index
            continue
        if _SECTION_END.match(line):
            return Section(heading, index, tuple(entries), tuple(invalid))
        entry = _ENTRY.match(line)
        if entry:
            entries.append(Entry(int(entry['number']), index, entry['merge'], entry['head']))
        elif _LIST_ITEM.match(line):
            invalid.append(index)
    if heading is None:
        return None
    return Section(heading, len(lines), tuple(entries), tuple(invalid))


def entries(body: str) -> list[Entry]:
    """List the section's entries in order; empty when the body has no section."""
    section = find_section(body)
    return list(section.entries) if section else []


def record_line(number: int, merge: str, head: str) -> str:
    """Return the merge record that replaces the ``- #<number>`` entry."""
    return f'- #{number} — merged as {merge} (head {head}), reconnected'


def record_merge(body: str, number: int, merge: str, head: str) -> str:
    """Replace entry `number`'s line with its merge record, keeping every other byte."""
    section = find_section(body)
    if section is None:
        raise DependsOnError(f'the body has no {HEADING} section')
    matches = [entry for entry in section.entries if entry.number == number]
    if len(matches) != 1:
        raise DependsOnError(f'{HEADING} lists #{number} {len(matches)} times, not once')
    lines = body.splitlines(keepends=True)
    original = lines[matches[0].line]
    ending = original[len(_content(original)) :]
    lines[matches[0].line] = record_line(number, merge, head) + ending
    edited = ''.join(lines)
    if [entry.number for entry in entries(edited)] != [entry.number for entry in section.entries]:
        raise DependsOnError(f'rewriting #{number} changed the {HEADING} entries')
    return edited


def parse_trailers(text: str) -> list[int]:
    """Return the pull request numbers of ``Depends-on`` trailer values, first seen first."""
    numbers: list[int] = []
    for value in text.split():
        match = _TRAILER.match(value.strip())
        if match and int(match.group(1)) not in numbers:
            numbers.append(int(match.group(1)))
    return numbers


def read_trailers(ref: str, *exclude: str, cwd: Path | None = None) -> list[int]:
    """
    Return the ``Depends-on`` trailers of commits reachable from `ref`, oldest first.

    Commits reachable from any `exclude` ref are skipped, so a caller can drop
    trailers a predecessor's own branch carries.
    """
    arguments = [
        'git',
        'log',
        '--reverse',
        '--format=%(trailers:key=Depends-on,valueonly,separator=%x20)',
        ref,
    ]
    if exclude:
        arguments += ['--not', *exclude]
    completed = subprocess.run(arguments, check=False, capture_output=True, text=True, cwd=cwd)
    if completed.returncode != 0:
        raise DependsOnError(f'git log {ref} failed: {completed.stderr.strip()}')
    return parse_trailers(completed.stdout)
