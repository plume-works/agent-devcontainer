#!/usr/bin/env python3

"""
Recognize a repository's default branch, for agentdev skill scripts.

Importable through the ``sys.path`` entry that reaches ``bin/``, and runnable:

  git_default_branch.py is-default <branch>   exit 0 when <branch> is main or master
  git_default_branch.py remote <remote>       print the remote's default branch

Standard library only.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

USAGE = """\
Usage:
  git_default_branch.py is-default <branch>
  git_default_branch.py remote <remote>
"""


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(list(arguments), check=False, capture_output=True, text=True)


def is_default_branch(branch: str) -> bool:
    """Return whether `branch` carries a conventional default-branch name."""
    return branch in ('main', 'master')


def remote_default_branch(remote: str) -> str | None:
    """
    Return the branch `remote` calls its default, or None when nothing knows.

    ``refs/remotes/<remote>/HEAD`` answers first, then GitHub's answer for the
    remote URL.
    """
    symref = _run('git', 'symbolic-ref', '--quiet', '--short', f'refs/remotes/{remote}/HEAD')
    if symref.returncode == 0:
        return symref.stdout.strip().removeprefix(f'{remote}/')
    if shutil.which('gh') is None:
        return None
    url = _run('git', 'remote', 'get-url', remote)
    if url.returncode != 0:
        return None
    view = _run(
        'gh',
        'repo',
        'view',
        url.stdout.strip(),
        '--json',
        'defaultBranchRef',
        '--jq',
        '.defaultBranchRef.name',
    )
    name = view.stdout.strip()
    if view.returncode != 0 or not name:
        return None
    return name


def main(arguments: list[str]) -> int:
    """Run one command-line request; exit 1 for a no, 2 for bad usage."""
    if len(arguments) == 2 and arguments[0] == 'is-default':
        return 0 if is_default_branch(arguments[1]) else 1
    if len(arguments) == 2 and arguments[0] == 'remote':
        name = remote_default_branch(arguments[1])
        if name is None:
            return 1
        print(name)
        return 0
    if arguments in (['-h'], ['--help']):
        print(USAGE, end='')
        return 0
    print(USAGE, end='', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
