#!/usr/bin/env python3
"""
Keep each support file in docs/knowledge/ a symbolic link to its iwe-bootstrap scaffold copy.

Run from the repository root. Makes a missing link, replaces a copy that has the same bytes as
its scaffold copy, and reports every other difference. Never deletes a file. Prints one line for
each change or report, and exits 1 when there is any.
"""

from __future__ import annotations

from collections.abc import Iterator
import filecmp
import os
from pathlib import Path

SCAFFOLD = Path('.agents/plugins/agentdev-iwe/skills/iwe-bootstrap/assets/docs/knowledge')
KNOWLEDGE = Path('docs/knowledge')
# Names at the top of docs/knowledge/ that the repository owns: never links.
OWNED = frozenset({'data', 'tests', 'LICENSE.md', '.gitignore'})


def entries(top: Path) -> Iterator[Path]:
    """Yield each file and link under top, relative to it, without the owned names."""
    for directory, dirs, files in os.walk(top):
        here = Path(directory).relative_to(top)
        if here == Path('.'):
            dirs[:] = [name for name in dirs if name not in OWNED]
        linked = [name for name in dirs if (Path(directory) / name).is_symlink()]
        for name in sorted([*files, *linked]):
            relative = here / name
            if relative.parts[0] not in OWNED:
                yield relative


def under_a_link(path: Path) -> bool:
    """Return whether a directory between docs/knowledge/ and path is a link."""
    return any(parent.is_symlink() for parent in path.parents if KNOWLEDGE in parent.parents)


def place(relative: Path) -> str | None:
    """Make docs/knowledge/<relative> a link to its scaffold copy, or say why not."""
    copy, path = SCAFFOLD / relative, KNOWLEDGE / relative
    target = os.path.relpath(copy, path.parent)
    if path.is_symlink():
        if path.resolve() == copy.resolve():
            return None
        return f'{path}: link to {os.readlink(path)}, not to {target}'
    if under_a_link(path):
        return f'{path}: a directory above it is a link; make that directory a real one'
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)
        return f'{path}: made a link to {target}'
    if filecmp.cmp(path, copy, shallow=False):
        path.unlink()
        path.symlink_to(target)
        return f'{path}: replaced the copy with a link to {target}'
    return f'different: {path} vs {copy}'


def stray(relative: Path, support: set[Path]) -> str | None:
    """
    Report a file in docs/knowledge/ that has no scaffold copy.

    The caller never gives this function a file that the repository owns.
    """
    path = KNOWLEDGE / relative
    if relative in support:
        return None
    if path.is_symlink() and not path.exists():
        return f'{path}: link does not resolve'
    if relative.parts[0] == 'schema' and not path.is_symlink():
        return f'{path}: belongs in the scaffold'
    return None


def main() -> int:
    """
    Place each support file and report each file that has no scaffold copy.

    Exit 1 when the script changes or reports a file.
    """
    support = set(entries(SCAFFOLD))
    lines = [line for relative in sorted(support) if (line := place(relative))]
    lines += [line for relative in entries(KNOWLEDGE) if (line := stray(relative, support))]
    for line in lines:
        print(line)
    return 1 if lines else 0


if __name__ == '__main__':
    raise SystemExit(main())
