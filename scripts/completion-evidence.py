#!/usr/bin/env python3
"""
Keep the evidence of a ticked plan task in the message of the commit that ticks it.

``check-message <message-file>`` runs as a ``commit-msg`` hook. A commit that ticks a plan task
ticks one task only, and its message has one completion evidence block with text.
``check-push`` runs as a ``pre-push`` hook and applies the same rules to each pushed commit.
``show <N>`` prints the ticked plan task and the block of each commit of pull request ``N``.
See ADR-0093.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import os
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
SCISSORS = ' ------------------------ >8 ------------------------'
# The characters from which `core.commentChar=auto` selects, in the sequence that Git uses.
AUTO_COMMENTS = '#;@!$%^&|:'


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


def comment_string(message: str) -> str:
    """Return the comment string that Git uses for a message it gives to the editor."""
    found = subprocess.run(
        ['git', 'config', '--get-regexp', r'^core\.comment(char|string)$'],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.splitlines()
    comment = found[-1].partition(' ')[2] if found else '#'
    if comment != 'auto':
        return comment
    lines = message.splitlines()
    return next((char for char in AUTO_COMMENTS if char + SCISSORS in lines), '#')


def evidence_blocks(message: str, comment: str = '#') -> list[str]:
    """
    Find the completion evidence blocks of a commit message.

    Args:
        message: The commit message. Git removes the scissors line and all the text after it.
        comment: The start of a comment line, which Git removes.

    Returns:
        The text of each block, without the trailer paragraph at the end of the message.

    """
    lines = message.splitlines()
    if comment + SCISSORS in lines:
        lines = lines[: lines.index(comment + SCISSORS)]
    lines = [line.rstrip() for line in lines if not line.startswith(comment)]
    starts = [
        index + 2
        for index in range(len(lines) - 1)
        if (lines[index].strip(), lines[index + 1].strip().lower()) == HEADER
    ]
    blocks: list[str] = []
    for number, start in enumerate(starts):
        end = starts[number + 1] - 2 if number + 1 < len(starts) else len(lines)
        # A trailer paragraph follows a blank line, so the header line stays in the text here.
        body = '\n'.join(lines[start - 1 : end]).rstrip()
        rest, blank, last = body.rpartition('\n\n')
        if number + 1 == len(starts) and blank and all(map(TRAILER.match, last.splitlines())):
            body = rest
        blocks.append(body.partition('\n')[2].strip())
    return blocks


def base() -> str:
    """Return the tree of `HEAD`, or the empty tree before the first commit."""
    tree = subprocess.run(
        ['git', 'rev-parse', '--verify', '--quiet', 'HEAD^{tree}'],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.strip()
    return tree or git('hash-object', '-t', 'tree', '/dev/null').strip()


def check_message(message_file: str) -> int:
    """Check the staged ticks against the commit message; return the exit code."""
    if Path(git('rev-parse', '--git-path', 'MERGE_HEAD').strip()).exists():
        return 0
    # `diff-index` is a low-level Git command,
    # so diff settings of the user do not change its file lines.
    diff = git('diff-index', '--cached', '-p', '--no-color', '-U0', base(), '--', PLANS_PATHSPEC)
    staged = ticks(diff)
    if not staged:
        return 0
    if len(staged) > 1:
        print('A commit ticks one plan task only. This commit ticks:', file=sys.stderr)
        for tick in staged:
            print(f'  {tick}', file=sys.stderr)
        return 1
    with open(message_file, encoding='utf-8') as handle:
        message = handle.read()
    blocks = evidence_blocks(message, comment_string(message))
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


def commit_ticks(commit: str) -> list[Tick]:
    """Return the plan tasks that a commit ticks, compared with its parent."""
    return ticks(git('diff-tree', '--root', '--no-color', '-U0', commit, '--', PLANS_PATHSPEC))


def check_push() -> int:
    """Check each pushed commit that is not a merge commit; return the exit code."""
    to_ref = os.environ.get('PRE_COMMIT_TO_REF')
    if not to_ref:
        print('check-push runs as a pre-push hook: PRE_COMMIT_TO_REF is not set.', file=sys.stderr)
        return 2
    from_ref = os.environ.get('PRE_COMMIT_FROM_REF')
    span = [f'{from_ref}..{to_ref}'] if from_ref else [to_ref, '--not', '--remotes']
    problems = []
    for commit in git('rev-list', '--reverse', '--no-merges', *span).split():
        found = commit_ticks(commit)
        if not found:
            continue
        name = f'{commit[:12]} {git("log", "-1", "--format=%s", commit).strip()}'
        blocks = evidence_blocks(git('log', '-1', '--format=%B', commit))
        if len(found) > 1:
            problems.append(f'{name}\n  ticks more than one plan task:')
            problems.extend(f'    {tick}' for tick in found)
        elif len(blocks) != 1 or not blocks[0]:
            problems.append(f'{name}\n  ticks {found[0]}\n  with no completion evidence block.')
    if problems:
        print('A pushed commit breaks the completion evidence rules:', file=sys.stderr)
        print('\n'.join(problems), file=sys.stderr)
    return 1 if problems else 0


def show(number: int) -> int:
    """Print the ticked plan task and the block of each commit of a pull request."""
    head = fetch(f'refs/pull/{number}/head')
    main = fetch('refs/heads/main')
    commits = git('rev-list', '--reverse', '--no-merges', head, f'^{main}').split()
    for commit in commits:
        found = commit_ticks(commit)
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
    commands.add_parser('check-push')
    commands.add_parser('show').add_argument('number', type=int)
    arguments = parser.parse_args(argv)
    if arguments.command == 'check-message':
        return check_message(arguments.message_file)
    if arguments.command == 'check-push':
        return check_push()
    return show(arguments.number)


if __name__ == '__main__':
    sys.exit(main())
