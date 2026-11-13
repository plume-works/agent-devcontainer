#!/usr/bin/env python3
"""
Count how often a commit that changes a spec's source files also changes the spec.

Usage: source-coupling.py   (from the repository root)

A spec's source files are the repository paths under ``sources`` in its frontmatter, with
``README.md`` and paths under ``docs/knowledge`` left out. Dependency-bump commits are skipped.
"""

from __future__ import annotations

from pathlib import Path
import re
import subprocess

SPECS = Path('docs/knowledge/data/spec')
BUMP_SUBJECTS = ('^Update ', '^chore(deps)', '^Lock file')


def git(*args: str) -> str:
    """Return the output of one git command."""
    return subprocess.run(['git', *args], capture_output=True, text=True, check=True).stdout


def source_files(spec: Path) -> list[str]:
    """Return the existing repository files a spec lists as sources."""
    frontmatter = spec.read_text().split('---')[1]
    paths = re.findall(r'resource:\s*(\S+)', frontmatter)
    return [
        path
        for path in paths
        if not path.startswith(('http', 'docs/knowledge'))
        and path != 'README.md'
        and Path(path).exists()
    ]


def main() -> None:
    """Print, for each spec and in total, the source commits that also changed the spec."""
    total = shared = 0
    print(f'{"spec":34} source-commits with-spec-edit')
    for spec in sorted(SPECS.glob('*.md')):
        spec_commits = git('log', '--follow', '--format=%H', '--', str(spec)).split()
        sources = source_files(spec)
        if not spec_commits or not sources:
            continue
        skip = [f'--grep={subject}' for subject in BUMP_SUBJECTS]
        since = f'{spec_commits[-1]}..HEAD'
        log = git('log', '--format=%H', '--invert-grep', *skip, since, '--', *sources)
        source_commits = set(log.split())
        both = source_commits & set(spec_commits)
        total += len(source_commits)
        shared += len(both)
        print(f'{spec.stem:34} {len(source_commits):14} {len(both):14}')
    print(f'{"total":34} {total:14} {shared:14}  ({100 * shared / total:.0f}%)')


if __name__ == '__main__':
    main()
