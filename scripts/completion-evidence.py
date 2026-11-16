#!/usr/bin/env python3
"""
Keep the evidence of a ticked plan task in the message of the commit that ticks it.

``check-message <message-file>`` runs as a ``commit-msg`` hook. A commit that ticks a plan task
ticks one task only, and its message has one completion evidence block with text.
``show <N>`` prints the ticked plan task and the block of each commit of pull request ``N``.
See ADR-0093.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys

PLANS = 'docs/knowledge/data/plans/'
PLANS_PATHSPEC = f':(top){PLANS}'
HEADER = ('---', 'completion evidence:')
FILE_LINE = re.compile(r'^\+\+\+ b/(?P<path>.+)$')
OPEN_LINE = re.compile(r'^-- \[ \] (?P<text>.*)$')
TICKED_LINE = re.compile(r'^\+- \[[xX]\] (?P<text>.*)$')
TRAILER = re.compile(r'^[A-Za-z][A-Za-z0-9-]*: \S')


@dataclass(frozen=True)
class Tick:
    """One plan task that changed from `- [ ]` to `- [x]`."""

    path: str
    text: str

    def __str__(self) -> str:
        """Give the tick as `path: task text`."""
        return f'{self.path}: {self.text}'


def git(*arguments: str) -> str:
    """Run Git and return its stdout."""
    return subprocess.run(['git', *arguments], check=True, capture_output=True, text=True).stdout


def ticks(diff: str) -> list[Tick]:
    """
    Find the plan tasks that a unified diff ticks.

    Args:
        diff: Unified diff output of the plans directory.

    Returns:
        Each ticked plan task, in diff order.

    """
    found: list[Tick] = []
    path = ''
    opened: Counter[str] = Counter()
    for line in diff.splitlines():
        if line.startswith('diff --git '):
            path, opened = '', Counter()
        elif match := FILE_LINE.match(line):
            path = match['path']
        elif match := OPEN_LINE.match(line):
            opened[match['text'].strip()] += 1
        elif (match := TICKED_LINE.match(line)) and path.startswith(PLANS):
            text = match['text'].strip()
            if opened[text]:
                opened[text] -= 1
                found.append(Tick(path, text))
    return found


def evidence_blocks(message: str) -> list[str]:
    """
    Find the completion evidence blocks of a commit message.

    Args:
        message: The commit message; lines that start with `#` are comments.

    Returns:
        The text of each block, without the trailer paragraph at the end of the message.

    """
    lines = [line.rstrip() for line in message.splitlines() if not line.startswith('#')]
    starts = [
        index + 2
        for index in range(len(lines) - 1)
        if (lines[index].strip(), lines[index + 1].strip().lower()) == HEADER
    ]
    blocks: list[str] = []
    for number, start in enumerate(starts):
        end = starts[number + 1] - 2 if number + 1 < len(starts) else len(lines)
        body = '\n'.join(lines[start:end]).strip()
        if number + 1 == len(starts):
            paragraphs = body.split('\n\n')
            if all(TRAILER.match(line) for line in paragraphs[-1].splitlines()):
                body = '\n\n'.join(paragraphs[:-1]).strip()
        blocks.append(body)
    return blocks


def check_message(message_file: str) -> int:
    """Check the staged ticks against the commit message; return the exit code."""
    if Path(git('rev-parse', '--git-path', 'MERGE_HEAD').strip()).exists():
        return 0
    staged = ticks(git('diff', '--cached', '--no-color', '-U0', '--', PLANS_PATHSPEC))
    if not staged:
        return 0
    if len(staged) > 1:
        print('A commit ticks one plan task only. This commit ticks:', file=sys.stderr)
        for tick in staged:
            print(f'  {tick}', file=sys.stderr)
        return 1
    with open(message_file, encoding='utf-8') as handle:
        blocks = evidence_blocks(handle.read())
    if len(blocks) == 1 and blocks[0]:
        return 0
    problem = 'more than one' if len(blocks) > 1 else 'no' if not blocks else 'an empty'
    print(
        f'The commit ticks {staged[0]}\n'
        f'and its message has {problem} completion evidence block. End the message with:\n\n'
        '---\ncompletion evidence:\n<how it was checked>',
        file=sys.stderr,
    )
    return 1


def fetch(ref: str) -> str:
    """Fetch one ref from `origin` and return its commit."""
    git('fetch', '--quiet', 'origin', ref)
    return git('rev-parse', 'FETCH_HEAD').strip()


def show(number: int) -> int:
    """Print the ticked plan task and the block of each commit of a pull request."""
    head = fetch(f'refs/pull/{number}/head')
    main = fetch('refs/heads/main')
    commits = git('rev-list', '--reverse', '--no-merges', head, f'^{main}').split()
    for commit in commits:
        diff = git('diff-tree', '--root', '--no-color', '-U0', commit, '--', PLANS_PATHSPEC)
        found = ticks(diff)
        if not found:
            continue
        blocks = evidence_blocks(git('log', '-1', '--format=%B', commit))
        print(f'{commit[:12]} {git("log", "-1", "--format=%s", commit).strip()}')
        for tick in found:
            print(f'  ticks {tick}')
        print('\n'.join(blocks) if any(blocks) else '(no completion evidence)')
        print()
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run a subcommand and return its exit code."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    commands = parser.add_subparsers(dest='command', required=True)
    commands.add_parser('check-message').add_argument('message_file')
    commands.add_parser('show').add_argument('number', type=int)
    arguments = parser.parse_args(argv)
    if arguments.command == 'check-message':
        return check_message(arguments.message_file)
    return show(arguments.number)


if __name__ == '__main__':
    sys.exit(main())
