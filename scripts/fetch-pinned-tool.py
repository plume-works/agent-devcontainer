#!/usr/bin/env python3
"""
Download pinned tools for this machine's architecture and write their binaries to a directory.

Each entry of ``docker/devcontainer/pinned-tools.yml`` is fetched, verified against its recorded
checksum, and only its named binaries are written out; a ``deb`` entry is written as its package
file. The image build installs every entry with ``--all``; Renovate's post-upgrade task fetches
a just-bumped tool the image does not carry yet.
"""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import platform
import sys
import tarfile
import tempfile
from typing import Any
import urllib.error
import urllib.request
import zipfile

import yaml

PINNED_TOOLS = 'docker/devcontainer/pinned-tools.yml'
ARCHITECTURES = ('amd64', 'arm64')
MACHINE_ARCHITECTURES = {'x86_64': 'amd64', 'amd64': 'amd64', 'aarch64': 'arm64', 'arm64': 'arm64'}
DOWNLOAD_TIMEOUT_SECONDS = 120


class FetchError(Exception):
    """A pinned tool that cannot be downloaded, verified, or unpacked."""


def load_tools(path: Path) -> dict[str, dict[str, Any]]:
    """Map each entry's name to the entry."""
    return {tool['name']: tool for tool in yaml.safe_load(path.read_text())['tools']}


def suffix(tool: dict[str, Any]) -> str:
    return '' if tool.get('bare_binary') else '.' + tool.get('extension', 'tar.gz')


def url(tool: dict[str, Any], arch: str) -> str:
    """Return the entry's download URL for one architecture."""
    version = str(tool['version'])
    asset = (
        tool['asset_prefix']
        .replace('{version}', version)
        .replace('{bare_version}', version.removeprefix('v'))
    )
    return (
        f'{tool["url_prefix"]}/{version}/{asset}{tool["archives"][arch]["target"]}{suffix(tool)}'
    )


def _architecture() -> str:
    """Return this machine's architecture in the pins' vocabulary."""
    machine = platform.machine().lower()
    if machine not in MACHINE_ARCHITECTURES:
        raise FetchError(f'unsupported machine architecture: {machine}')
    return MACHINE_ARCHITECTURES[machine]


def _download(source: str, target: Path) -> str:
    """Write a URL's body to target and return its SHA-256."""
    digest = hashlib.sha256()
    try:
        with (
            urllib.request.urlopen(source, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response,
            target.open('wb') as out,
        ):
            while chunk := response.read(1 << 20):
                digest.update(chunk)
                out.write(chunk)
    except (urllib.error.URLError, OSError) as error:
        raise FetchError(f'download failed: {source}: {error}') from error
    return digest.hexdigest()


def _read_member(archive: Path, member: str) -> bytes:
    """Return one file's bytes from a tar or zip archive."""
    if zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as bundle:
            try:
                return bundle.read(member)
            except KeyError as error:
                raise FetchError(f'{archive.name}: no file {member}') from error
    with tarfile.open(archive) as bundle:
        try:
            extracted = bundle.extractfile(member)
        except KeyError as error:
            raise FetchError(f'{archive.name}: no file {member}') from error
        if extracted is None:
            raise FetchError(f'{archive.name}: {member} is not a regular file')
        return extracted.read()


def fetch(tool: dict[str, Any], destination: Path, arch: str) -> list[Path]:
    """Write the entry's binaries, or its package file, into destination; return their paths."""
    name, version = tool['name'], str(tool['version'])
    if arch not in tool['archives']:
        raise FetchError(f'{name} is not available for architecture {arch}')
    destination.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination) as scratch:
        archive = Path(scratch) / f'{name}{suffix(tool)}'
        actual = _download(url(tool, arch), archive)
        recorded = str(tool['archives'][arch]['checksum']).removeprefix('sha256:')
        if actual != recorded:
            raise FetchError(f'{name} {version} ({arch}) hashes to {actual}, not {recorded}')
        if tool.get('deb'):
            target = destination / f'{name}.deb'
            archive.replace(target)
            return [target]
        if tool.get('bare_binary'):
            target = destination / name
            archive.replace(target)
            target.chmod(0o755)
            return [target]
        directory = tool.get('binaries_dir', '').replace('{version}', version)
        # Every binary is read before any is written, so a short archive installs nothing.
        bodies = {
            binary: _read_member(archive, f'{directory}/{binary}'.lstrip('/'))
            for binary in tool.get('binaries', [name])
        }
    installed = []
    for binary, body in bodies.items():
        target = destination / binary
        target.write_bytes(body)
        target.chmod(0o755)
        installed.append(target)
    return installed


def main(argv: list[str] | None = None) -> int:
    """Fetch the named tools, or every tool, into the destination directory."""
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('destination', type=Path, help='Directory to write the binaries to.')
    parser.add_argument('names', nargs='*', help='Entry names in the pin file.')
    parser.add_argument('--all', action='store_true', help='Fetch every entry.')
    parser.add_argument('--pins', type=Path, default=Path(PINNED_TOOLS))
    args = parser.parse_args(argv)
    if bool(args.names) == args.all:
        parser.error('name the tools to fetch, or pass --all')
    try:
        tools = load_tools(args.pins)
        names = list(tools) if args.all else args.names
        arch = _architecture()
        for name in names:
            if name not in tools:
                raise FetchError(f'{args.pins}: no pinned tool named {name}')
            for path in fetch(tools[name], args.destination, arch):
                print(path)
    except (FetchError, OSError, tarfile.TarError, zipfile.BadZipFile) as error:
        print(f'fetch-pinned-tool: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
