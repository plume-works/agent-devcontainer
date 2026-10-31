#!/usr/bin/env python3

"""
Apply ShellCheck's suggested fixes to every shell script under the working directory.

Usage:
  shellcheck_fix.py

Vendored trees, virtual environments, and .tmp are skipped. Exits with
ShellCheck's status when it fails outright (status above 1), otherwise with the
status of applying its diff. Standard library only.
"""

from __future__ import annotations

from fnmatch import fnmatchcase
import os
from pathlib import Path
import subprocess
import sys
import tempfile

PRUNED = ('*/vendor', './.venv*', './.tmp')


def _pruned(path: str) -> bool:
    return any(fnmatchcase(path, pattern) for pattern in PRUNED)


def shell_scripts() -> list[str]:
    """Return every *.sh path below '.', relative to it, outside the pruned trees."""
    found = []
    for directory, subdirectories, files in os.walk('.'):
        subdirectories[:] = [
            name for name in subdirectories if not _pruned(os.path.join(directory, name))
        ]
        for name in files:
            path = os.path.join(directory, name)
            if fnmatchcase(name.lower(), '*.sh') and not _pruned(path):
                found.append(os.path.relpath(path, '.'))
    return sorted(found)


def main(arguments: list[str]) -> int:
    """Collect ShellCheck's diff for the scripts and apply it."""
    if arguments in (['-h'], ['--help']):
        print(__doc__.strip())
        return 0
    Path('.tmp').mkdir(exist_ok=True)
    scripts = shell_scripts()
    if not scripts:
        return 0
    descriptor, findings_diff = tempfile.mkstemp(
        prefix='shellcheck-fix.', suffix='.diff', dir='.tmp'
    )
    try:
        with os.fdopen(descriptor, 'w') as findings:
            status = subprocess.run(
                ['shellcheck', '-f', 'diff', *scripts], check=False, stdout=findings
            ).returncode
        if status > 1:
            return status
        if os.path.getsize(findings_diff) > 0:
            return subprocess.run(['git', 'apply', findings_diff], check=False).returncode
        return 0
    finally:
        os.unlink(findings_diff)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
