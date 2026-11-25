#!/usr/bin/env python3
"""
Fail when py_packages/agentdev_lib/ changed since the latest agentdev-lib/* tag at the same version.

Run from the repository root, with the tags fetched. Compares HEAD with the highest
agentdev-lib/<version> tag. Exits 0 when there is no tag, nothing changed, or the version is new;
exits 1, saying why, when the package changed and kept the tagged version.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tomllib

PACKAGE = Path('py_packages/agentdev_lib')
TAG_PREFIX = 'agentdev-lib/'


def git(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run git and return the completed process."""
    return subprocess.run(['git', *arguments], capture_output=True, text=True, check=False)


def main() -> int:
    """Compare HEAD's package with the latest tag and return the exit status."""
    tags = git('tag', '--list', f'{TAG_PREFIX}*', '--sort=-version:refname')
    if tags.returncode != 0:
        print(f'ERROR: git tag failed: {tags.stderr.strip()}', file=sys.stderr)
        return 2
    if not tags.stdout.split():
        print('No agentdev-lib tag yet; nothing to compare.')
        return 0
    latest = tags.stdout.split()[0]
    diff = git('diff', '--quiet', latest, 'HEAD', '--', str(PACKAGE))
    if diff.returncode == 0:
        print(f'{PACKAGE}/ is unchanged since {latest}.')
        return 0
    if diff.returncode != 1:
        print(f'ERROR: git diff failed: {diff.stderr.strip()}', file=sys.stderr)
        return 2
    pyproject = (PACKAGE / 'pyproject.toml').read_text(encoding='utf-8')
    version = tomllib.loads(pyproject)['project']['version']
    if f'{TAG_PREFIX}{version}' != latest:
        print(f'{PACKAGE}/ changed since {latest}, and its version is now {version}.')
        return 0
    print(
        f'ERROR: {PACKAGE}/ changed since {latest} but keeps version {version}. '
        f'Raise the version in {PACKAGE}/pyproject.toml.',
        file=sys.stderr,
    )
    return 1


if __name__ == '__main__':
    sys.exit(main())
