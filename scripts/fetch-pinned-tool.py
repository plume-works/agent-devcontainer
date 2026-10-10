#!/usr/bin/env python3
"""
Download one dev_tools pinned tool for this machine's architecture and unpack its binaries.

The archive is fetched from the URL ``refresh-pin-checksums.py`` renders, verified against the
recorded checksum, and its binaries are written to the destination directory. Renovate's
post-upgrade task uses it to run a just-bumped tool the image does not carry yet.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
from pathlib import Path
import platform
import sys
import tarfile
import tempfile
from types import ModuleType
import urllib.error
import urllib.request

DEV_TOOLS_DEFAULTS = 'ansible/roles/dev_tools/defaults/main.yml'
MACHINE_ARCHITECTURES = {'x86_64': 'amd64', 'amd64': 'amd64', 'aarch64': 'arm64', 'arm64': 'arm64'}


class FetchError(Exception):
    """A pinned tool that cannot be downloaded, verified, or unpacked."""


def _refresh_module() -> ModuleType:
    """Load refresh-pin-checksums.py, whose hyphenated name rules out a plain import."""
    path = Path(__file__).with_name('refresh-pin-checksums.py')
    spec = importlib.util.spec_from_file_location('refresh_pin_checksums', path)
    if spec is None or spec.loader is None:
        raise FetchError(f'cannot load {path}')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _architecture() -> str:
    """Return this machine's architecture in the pins' vocabulary."""
    machine = platform.machine().lower()
    if machine not in MACHINE_ARCHITECTURES:
        raise FetchError(f'unsupported machine architecture: {machine}')
    return MACHINE_ARCHITECTURES[machine]


def _download(url: str, target: Path, timeout: int) -> str:
    """Write a URL's body to target and return its SHA-256."""
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response, target.open('wb') as out:
            while chunk := response.read(1 << 20):
                digest.update(chunk)
                out.write(chunk)
    except (urllib.error.URLError, OSError) as error:
        raise FetchError(f'download failed: {url}: {error}') from error
    return digest.hexdigest()


def fetch(name: str, destination: Path, repo_root: Path) -> list[Path]:
    """Install the named tool's binaries into destination; return their paths."""
    refresh = _refresh_module()
    defaults = refresh.yaml.safe_load((repo_root / DEV_TOOLS_DEFAULTS).read_text())
    spec = refresh.PIN_FILES[DEV_TOOLS_DEFAULTS]
    tools = {tool['name']: tool for tool in defaults[spec.list_var]}
    pins = {pin.key: pin for pin in spec.pins(defaults, repo_root)}
    if name not in tools:
        raise FetchError(f'{DEV_TOOLS_DEFAULTS}: no pinned tool named {name}')
    tool, pin, arch = tools[name], pins[name], _architecture()
    if tool.get('extension', 'tar.gz') != 'tar.gz' or tool.get('binaries_in_asset_dir'):
        raise FetchError(f'{name}: only flat tar.gz archives are supported')

    destination.mkdir(parents=True, exist_ok=True)
    installed = []
    with tempfile.TemporaryDirectory(dir=destination) as scratch:
        archive = Path(scratch) / f'{name}.tar.gz'
        actual = _download(pin.urls[arch], archive, refresh.DOWNLOAD_TIMEOUT_SECONDS)
        recorded = refresh._digest_of(pin.checksums[arch])
        if actual != recorded:
            raise FetchError(f'{name} {pin.version} ({arch}) hashes to {actual}, not {recorded}')
        with tarfile.open(archive) as bundle:
            for binary in tool.get('binaries', [name]):
                member = bundle.extractfile(binary)
                if member is None:
                    raise FetchError(f'{name} {pin.version}: archive has no file {binary}')
                target = destination / binary
                target.write_bytes(member.read())
                target.chmod(0o755)
                installed.append(target)
    return installed


def main(argv: list[str] | None = None) -> int:
    """Fetch the named tool into the destination directory."""
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('name', help='The tool entry name in dev_tools_pinned_tools.')
    parser.add_argument('destination', type=Path, help='Directory to write the binaries to.')
    parser.add_argument('--repo-root', type=Path, default=Path.cwd())
    args = parser.parse_args(argv)
    try:
        for path in fetch(args.name, args.destination, args.repo_root):
            print(path)
    except (FetchError, KeyError, tarfile.TarError) as error:
        print(f'fetch-pinned-tool: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
