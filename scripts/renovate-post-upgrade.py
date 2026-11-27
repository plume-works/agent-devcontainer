#!/usr/bin/env python3
"""Renovate's one post-upgrade task: see ADR-0050."""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.request

# Declares the iwe that the hooks and .iwe/ migrations run: see ADR-0111.
TOOLCHAIN = 'mise.toml'
# Pins the mise release, and its digests, for hosts without mise: see ADR-0111.
INSTALLER = 'scripts/install-toolchain'
MISE_RELEASES = 'https://github.com/jdx/mise/releases/download'


def run(*command: str, check: bool = True) -> int:
    return subprocess.run(command, check=check).returncode


def mise_checksums(version: str) -> str:
    """Return the SHASUMS256.txt of mise release VERSION; MISE_RELEASES_URL overrides the host."""
    base = os.environ.get('MISE_RELEASES_URL', MISE_RELEASES)
    with urllib.request.urlopen(f'{base}/v{version}/SHASUMS256.txt') as response:
        return response.read().decode()


def refresh_mise_digests() -> None:
    """Rewrite the installer's per-architecture digests from its MISE_VERSION's release."""
    installer = Path(INSTALLER)
    text = installer.read_text()
    match = re.search(r'^readonly MISE_VERSION=(\S+)$', text, re.MULTILINE)
    if match is None:
        raise SystemExit(f'renovate-post-upgrade: no MISE_VERSION in {INSTALLER}')
    version = match.group(1)
    digests = {}
    for line in mise_checksums(version).splitlines():
        digest, _, name = line.partition('  ')
        digests[name] = digest
    for arch in ('x64', 'arm64'):
        asset = f'./mise-v{version}-linux-{arch}-musl'
        if not re.fullmatch(r'[0-9a-f]{64}', digests.get(asset, '')):
            raise SystemExit(f'renovate-post-upgrade: no checksum for {asset}')
        constant = f'readonly MISE_SHA256_{arch.upper()}='
        text = re.sub(f'^{constant}.*$', f'{constant}{digests[asset]}', text, flags=re.MULTILINE)
    installer.write_text(text)


def changed_files() -> list[str]:
    """Return Renovate's uncommitted edits in its clone: the bump against HEAD."""
    tracked = subprocess.run(
        ['git', 'diff', '--name-only', '--diff-filter=d', 'HEAD'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    untracked = subprocess.run(
        ['git', 'ls-files', '--others', '--exclude-standard'],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    return [*tracked, *untracked]


def main() -> int:
    root = subprocess.run(
        ['git', 'rev-parse', '--show-toplevel'], check=True, capture_output=True, text=True
    ).stdout.strip()
    os.chdir(root)
    changed = changed_files()
    if not changed:
        return 0
    if INSTALLER in changed:
        refresh_mise_digests()
    # The image carries the old iwe; the bumped one migrates .iwe/ and runs the hooks' `iwe`.
    locked: tuple[str, ...] = ()
    if TOOLCHAIN in changed:
        os.environ['MISE_TRUSTED_CONFIG_PATHS'] = root
        locked = ('mise', 'exec', '--locked', '--')
        run(*locked, 'iwe', 'normalize')
    # pre-commit through uv, not the image's copy: see ADR-0050.
    # Post-upgrade runs on the base branch; the guard is for commits.
    skip = os.environ.get('SKIP')
    os.environ['SKIP'] = f'{skip},no-commit-to-branch' if skip else 'no-commit-to-branch'
    pre_commit = (*locked, 'uv', 'run', '--frozen', 'pre-commit', 'run', '--files')
    if run(*pre_commit, *changed_files(), check=False):
        run(*pre_commit, *changed_files())
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except subprocess.CalledProcessError as error:
        sys.exit(error.returncode)
