#!/usr/bin/env python3
"""
Republish the Git Core PPA's newest git build for Ubuntu as a release of this repository.

The PPA's InRelease index must carry a valid signature from the pinned key; every file
after it is checked against the SHA-256 that the signed index chains to. The release
holds the PPA's .deb files unchanged, and its notes record each file's PPA URL and
SHA-256. A release that already exists is left alone.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import gzip
import hashlib
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import urllib.request

PPA = 'https://ppa.launchpadcontent.net/git-core/ppa/ubuntu'
SERIES = 'noble'
ARCHITECTURES = ('amd64', 'arm64')
KEY_FILE = Path(__file__).resolve().parent / 'git-core-ppa.asc'
KEY_FINGERPRINT = (
    'F911AB184317630C59970973E363C90F8F1B6217'  # gitleaks:allow - public PGP key fingerprint
)
TAG_PREFIX = 'pinned-deps/git/'
# The tag's version drops the epoch and spells `~`, which Git refs forbid, as `-`.
VERSION = re.compile(r'^1:(\d+\.\d+\.\d+-0ppa\d+)~(ubuntu24\.04\.\d+)$')
TIMEOUT_SECONDS = 120


class CacheError(Exception):
    """The PPA's contents cannot be verified or republished."""


@dataclass(frozen=True)
class Package:
    """One .deb the PPA's signed index lists."""

    name: str
    version: str
    arch: str
    url: str
    sha256: str
    size: int


def fetch(url: str) -> bytes:
    """Download a URL into memory."""
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as response:
            return response.read()
    except OSError as error:
        raise CacheError(f'download failed: {url}: {error}') from error


def verified_release(scratch: Path) -> str:
    """Return the InRelease text after checking its signature by the pinned key."""
    signed = scratch / 'InRelease'
    signed.write_bytes(fetch(f'{PPA}/dists/{SERIES}/InRelease'))
    keyring = scratch / 'keyring.gpg'
    subprocess.run(['gpg', '--dearmor', '--output', str(keyring), str(KEY_FILE)], check=True)
    content = scratch / 'InRelease.txt'
    result = subprocess.run(
        [
            'gpgv',
            '--status-fd',
            '1',
            '--keyring',
            str(keyring),
            '--output',
            str(content),
            str(signed),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if f'[GNUPG:] VALIDSIG {KEY_FINGERPRINT} ' not in result.stdout:
        raise CacheError(f'InRelease lacks a valid signature by {KEY_FINGERPRINT}')
    return content.read_text()


def index_digest(release: str, path: str) -> str:
    """Return the SHA-256 the signed InRelease records for one index file."""
    sha256_section = release.split('\nSHA256:\n', 1)[-1]
    for line in sha256_section.splitlines():
        fields = line.split()
        if not line.startswith(' '):
            break
        if len(fields) == 3 and fields[2] == path:
            return fields[0]
    raise CacheError(f'InRelease records no SHA256 for {path}')


def checked(body: bytes, sha256: str, what: str) -> bytes:
    """Return the body when it hashes to the expected SHA-256."""
    actual = hashlib.sha256(body).hexdigest()
    if actual != sha256:
        raise CacheError(f'{what} hashes to {actual}, expected {sha256}')
    return body


def packages(release: str, arch: str) -> dict[str, Package]:
    """Return the git and git-man entries of one architecture's signed Packages index."""
    path = f'main/binary-{arch}/Packages.gz'
    url = f'{PPA}/dists/{SERIES}/{path}'
    body = checked(fetch(url), index_digest(release, path), url)
    found = {}
    for stanza in gzip.decompress(body).decode().split('\n\n'):
        fields = dict(re.findall(r'^([\w-]+): (.*)$', stanza, re.MULTILINE))
        if fields.get('Package') in ('git', 'git-man'):
            found[fields['Package']] = Package(
                name=fields['Package'],
                version=fields['Version'],
                arch=fields['Architecture'],
                url=f'{PPA}/{fields["Filename"]}',
                sha256=fields['SHA256'],
                size=int(fields['Size']),
            )
    if set(found) != {'git', 'git-man'}:
        raise CacheError(f'{url} lists {sorted(found)}, not git and git-man')
    return found


def newest_build(release: str) -> list[Package]:
    """Return the git build every architecture carries, with its one git-man package."""
    by_arch = {arch: packages(release, arch) for arch in ARCHITECTURES}
    versions = {entries['git'].version for entries in by_arch.values()}
    versions |= {entries['git-man'].version for entries in by_arch.values()}
    if len(versions) != 1:
        raise CacheError(f'architectures disagree on the version: {sorted(versions)}')
    return [by_arch[arch]['git'] for arch in ARCHITECTURES] + [
        by_arch[ARCHITECTURES[0]]['git-man']
    ]


def tag_of(version: str) -> str:
    """Return the release tag for a PPA package version."""
    match = VERSION.match(version)
    if match is None:
        raise CacheError(f'version {version} does not match {VERSION.pattern}')
    return f'{TAG_PREFIX}{match.group(1)}-{match.group(2)}'


def release_exists(tag: str) -> bool:
    """Tell whether the repository already has a release for the tag."""
    shown = subprocess.run(['gh', 'release', 'view', tag], capture_output=True, check=False)
    return shown.returncode == 0


def notes(version: str, assets: list[tuple[str, Package]]) -> str:
    """Return the release notes: each asset's PPA source and SHA-256."""
    rows = '\n'.join(
        f'| `{name}` | <{package.url}> | `{package.sha256}` |' for name, package in assets
    )
    return (
        f'The Git Core PPA build `{version}` for Ubuntu 24.04 ({SERIES}), unchanged.\n\n'
        f'The PPA index was verified against key `{KEY_FINGERPRINT}`.\n\n'
        '| Asset | Downloaded from | SHA-256 |\n'
        '| --- | --- | --- |\n'
        f'{rows}\n'
    )


def publish(dry_run: bool) -> int:
    """Republish the PPA's newest build unless a release for it exists."""
    with tempfile.TemporaryDirectory() as directory:
        scratch = Path(directory)
        build = newest_build(verified_release(scratch))
        version = build[0].version
        tag = tag_of(version)
        if not dry_run and release_exists(tag):
            print(f'{tag}: already released')
            return 0
        assets = []
        for package in build:
            name = f'{package.name}_{tag.removeprefix(TAG_PREFIX)}_{package.arch}.deb'
            body = checked(fetch(package.url), package.sha256, package.url)
            if len(body) != package.size:
                raise CacheError(f'{package.url} is {len(body)} bytes, expected {package.size}')
            (scratch / name).write_bytes(body)
            assets.append((name, package))
        (scratch / 'SHA256SUMS').write_text(
            ''.join(f'{package.sha256}  {name}\n' for name, package in assets)
        )
        (scratch / 'notes.md').write_text(notes(version, assets))
        files = [str(scratch / name) for name, _ in assets] + [str(scratch / 'SHA256SUMS')]
        if dry_run:
            print((scratch / 'notes.md').read_text())
            print(f'{tag}: would publish {", ".join(name for name, _ in assets)}')
            return 0
        subprocess.run(
            [
                'gh',
                'release',
                'create',
                tag,
                *files,
                '--title',
                f'git {version}',
                '--notes-file',
                str(scratch / 'notes.md'),
                '--latest=false',
            ],
            check=True,
        )
        print(f'{tag}: released')
    return 0


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and republish the newest build."""
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument(
        '--dry-run', action='store_true', help='Verify and download, but publish nothing.'
    )
    args = parser.parse_args(argv)
    try:
        return publish(args.dry_run)
    except CacheError as error:
        print(f'cache_ppa_release: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
