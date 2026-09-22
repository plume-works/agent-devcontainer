#!/usr/bin/env python3
"""
Refresh the pinned apt versions used by the Ansible roles.

Every role that installs apt packages reads its versions from
``ansible/roles/<role>/vars/apt_pins_<suite>_<arch>.yml``. This script resolves
the newest version of each package name in those files from the apt
repositories the role actually enables, for every ``(suite, arch)`` pair
present on disk, and rewrites the version values in place.

Renovate keeps the pins current in normal operation (see the ``deb`` custom
managers in ``.github/renovate.json``). Run this script when a package name is
added or removed, or to re-derive every pin from scratch.

Usage::

    scripts/apt-pins-refresh.py            # rewrite the pin files
    scripts/apt-pins-refresh.py --check    # fail if any pin is out of date
"""

import argparse
import gzip
import pathlib
import re
import shutil
import subprocess
import sys
from typing import Iterable
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
ROLES_DIR = ROOT / 'ansible' / 'roles'
CACHE_DIR = ROOT / '.tmp' / 'apt-pins-cache'

PIN_FILE_RE = re.compile(r'^apt_pins_(?P<suite>[a-z]+)_(?P<arch>[a-z0-9]+)\.yml$')
PIN_LINE_RE = re.compile(
    r'^(?P<indent>\s+)(?P<pkg>[a-z0-9][a-z0-9+.\-]*):\s*"(?P<version>[^"]*)"\s*$'
)

# Ubuntu ships the archive for amd64 and the ports mirror for every other
# architecture. Both expose the same suite/component layout.
UBUNTU_MIRRORS = {
    'amd64': 'http://archive.ubuntu.com/ubuntu',
    'arm64': 'http://ports.ubuntu.com/ubuntu-ports',
}
UBUNTU_POCKETS = ('', '-updates', '-security', '-backports')
UBUNTU_COMPONENTS = ('main', 'universe', 'restricted', 'multiverse')

# Third-party repositories, keyed by the family name used in ROLE_REPOS below.
# The third element is the suite to request when it is not the Ubuntu release
# the pins are being resolved for.
THIRD_PARTY = {
    'kitware': ('https://apt.kitware.com/ubuntu', ('main',), None),
    'docker': ('https://download.docker.com/linux/ubuntu', ('stable',), None),
    'git-core': ('https://ppa.launchpadcontent.net/git-core/ppa/ubuntu', ('main',), None),
    'github-cli': ('https://cli.github.com/packages', ('main',), 'stable'),
    # The Node major lives in the repository URL, so it is pinned by the
    # NodeSource setup script the nodejs role runs, not by a version here.
    # Keep this in step with that script's URL in
    # ansible/roles/nodejs/tasks/main.yml.
    'nodesource': ('https://deb.nodesource.com/node_24.x', ('main',), 'nodistro'),
}

# The apt sources a role resolves against unless ROLE_REPOS narrows or widens
# it. Must stay in step with the registryUrls the `deb` custom managers use in
# .github/renovate.json, otherwise Renovate would propose a version this script
# would revert.
DEFAULT_REPOS = {'ubuntu'}

# Roles whose apt sources are wider than DEFAULT_REPOS, because the role adds a
# repository itself or inherits one from a role that runs before it.
ROLE_REPOS = {
    'cmake_kitware': {'ubuntu', 'kitware'},
    # Installs cmake as well, after cmake_kitware has added the Kitware
    # repository, and adds the git-core PPA that its git packages come from.
    'dev_tools': {'ubuntu', 'kitware', 'git-core'},
    'github_cli': {'ubuntu', 'github-cli'},
    'install_docker': {'ubuntu', 'docker'},
    'nodejs': {'ubuntu', 'nodesource'},
}


def component_urls(suite: str, arch: str, families: set[str]) -> list[str]:
    """Build every ``binary-<arch>`` component URL a role may resolve against."""
    urls = []
    if 'ubuntu' in families:
        mirror = UBUNTU_MIRRORS.get(arch)
        if mirror is None:
            raise SystemExit(f'No Ubuntu mirror configured for architecture {arch}')
        for pocket in UBUNTU_POCKETS:
            for component in UBUNTU_COMPONENTS:
                urls.append(f'{mirror}/dists/{suite}{pocket}/{component}/binary-{arch}')
    for family, (base, components, suite_override) in THIRD_PARTY.items():
        if family not in families:
            continue
        for component in components:
            dist = suite_override or suite
            urls.append(f'{base}/dists/{dist}/{component}/binary-{arch}')
    return urls


def fetch_index(component_url: str) -> dict[str, list[str]]:
    """Download and parse one ``Packages.gz`` index into ``{package: [versions]}``."""
    cache_name = re.sub(r'[^a-zA-Z0-9]+', '_', component_url).strip('_') + '.gz'
    cached = CACHE_DIR / cache_name
    if not cached.exists():
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        url = f'{component_url}/Packages.gz'
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                payload = response.read()
        except (urllib.error.URLError, urllib.error.HTTPError) as error:
            # A missing component (for example a pocket with no packages for an
            # architecture) is normal; record it as empty rather than failing.
            print(f'  warning: {url}: {error}', file=sys.stderr)
            cached.write_bytes(gzip.compress(b''))
            return {}
        cached.write_bytes(payload)

    index: dict[str, list[str]] = {}
    package = None
    with gzip.open(cached, 'rt', encoding='utf-8', errors='replace') as stream:
        for line in stream:
            if line.startswith('Package: '):
                package = line[9:].strip()
            elif line.startswith('Version: ') and package:
                index.setdefault(package, []).append(line[9:].strip())
            elif not line.strip():
                package = None
    return index


def newest(versions: Iterable[str]) -> str | None:
    """Return the highest version according to ``dpkg --compare-versions``."""
    best = None
    for version in versions:
        if best is None:
            best = version
            continue
        compared = subprocess.run(['dpkg', '--compare-versions', version, 'gt', best], check=False)
        if compared.returncode == 0:
            best = version
    return best


def refresh_file(path: pathlib.Path, check: bool) -> tuple[int, int]:
    """Resolve and rewrite every pin in one file, returning (updated, unresolved)."""
    match = PIN_FILE_RE.match(path.name)
    suite, arch = match.group('suite'), match.group('arch')
    role = path.parent.parent.name
    families = ROLE_REPOS.get(role, DEFAULT_REPOS)

    lines = path.read_text(encoding='utf-8').splitlines()

    index: dict[str, list[str]] = {}
    for component_url in component_urls(suite, arch, families):
        for package, versions in fetch_index(component_url).items():
            index.setdefault(package, []).extend(versions)

    updated = 0
    unresolved = 0
    for position, line in enumerate(lines):
        pin = PIN_LINE_RE.match(line)
        if not pin:
            continue
        package = pin.group('pkg')
        resolved = newest(index.get(package, []))
        if resolved is None:
            print(
                f'  {path.name}: {package}: not found in any {role} repository',
                file=sys.stderr,
            )
            unresolved += 1
            continue
        if resolved != pin.group('version'):
            updated += 1
            print(f'  {role}/{suite}/{arch}: {package} -> {resolved}')
            lines[position] = f'{pin.group("indent")}{package}: "{resolved}"'

    if updated and not check:
        path.write_text('\n'.join(lines).rstrip() + '\n', encoding='utf-8')
    return updated, unresolved


def main() -> int:
    """Refresh every pin file on disk, or report the ones that are out of date."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--check',
        action='store_true',
        help='report out-of-date pins without rewriting the files',
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='discard the downloaded package indices before resolving',
    )
    args = parser.parse_args()

    if shutil.which('dpkg') is None:
        raise SystemExit('dpkg is required to compare Debian version strings')
    if args.no_cache and CACHE_DIR.exists():
        shutil.rmtree(CACHE_DIR)

    pin_files = sorted(ROLES_DIR.glob('*/vars/apt_pins_*.yml'))
    if not pin_files:
        raise SystemExit(f'No pin files found under {ROLES_DIR}')

    updated = 0
    unresolved = 0
    for path in pin_files:
        if not PIN_FILE_RE.match(path.name):
            print(f'Skipping unrecognised pin file name: {path}', file=sys.stderr)
            continue
        file_updated, file_unresolved = refresh_file(path, args.check)
        updated += file_updated
        unresolved += file_unresolved

    if unresolved:
        print(f'{unresolved} package(s) could not be resolved', file=sys.stderr)
        return 1
    if args.check and updated:
        print(f'{updated} pin(s) are out of date; run without --check', file=sys.stderr)
        return 1
    print(f'{len(pin_files)} pin file(s) processed, {updated} pin(s) changed')
    return 0


if __name__ == '__main__':
    sys.exit(main())
