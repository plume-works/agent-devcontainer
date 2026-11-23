"""Tests for scripts/fetch-pinned-tool.py against locally stored release archives."""

from __future__ import annotations

from collections.abc import Iterator
import hashlib
import importlib.util
import io
from pathlib import Path
import shutil
import sys
import tarfile
from uuid import uuid4
import zipfile

import pytest
from scratch import TMP_ROOT

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / 'scripts/fetch-pinned-tool.py'


def _load_script():
    """Load the hyphen-named script as a module."""
    spec = importlib.util.spec_from_file_location('fetch_pinned_tool', SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


fetch_tool = _load_script()
BINARIES = {'tool': b'#!/bin/sh\necho tool\n', 'toold': b'#!/bin/sh\necho toold\n'}


def tar_gz(files: dict[str, bytes]) -> bytes:
    """Return a tar.gz holding the given files."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as bundle:
        for name, body in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(body)
            bundle.addfile(info, io.BytesIO(body))
    return buffer.getvalue()


def zip_bytes(files: dict[str, bytes]) -> bytes:
    """Return a zip holding the given files."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as bundle:
        for name, body in files.items():
            bundle.writestr(name, body)
    return buffer.getvalue()


@pytest.fixture
def root() -> Iterator[Path]:
    """Create a scratch tree with an empty release directory."""
    TMP_ROOT.mkdir(exist_ok=True)
    path = TMP_ROOT / f'fetch-pinned-tool-{uuid4().hex}'
    (path / 'releases/v1').mkdir(parents=True)
    try:
        yield path
    finally:
        shutil.rmtree(path)


def pin(root: Path, body: bytes, extra: str = '', checksum: str | None = None, suffix='.tar.gz'):
    """Publish body as every architecture's asset and pin it under that checksum."""
    for target in ('x86_64-linux', 'aarch64-linux'):
        (root / f'releases/v1/tool-{target}{suffix}').write_bytes(body)
    digest = checksum or hashlib.sha256(body).hexdigest()
    pins = root / 'pinned-tools.yml'
    pins.write_text(
        'tools:\n'
        '  - name: tool\n'
        '    version: v1\n'
        f'    url_prefix: file://{root / "releases"}\n'
        '    asset_prefix: tool-\n'
        f'{extra}'
        '    archives:\n'
        '      amd64:\n'
        '        target: x86_64-linux\n'
        f'        checksum: {digest}\n'
        '      arm64:\n'
        '        target: aarch64-linux\n'
        f'        checksum: {digest}\n'
    )
    return pins


def fetch(root: Path, pins: Path, *names: str) -> int:
    return fetch_tool.main([str(root / 'bin'), *names, '--pins', str(pins)])


def test_installs_every_binary_executable(root: Path) -> None:
    """Each listed binary lands in the destination with its archived content."""
    pins = pin(root, tar_gz(BINARIES), '    binaries: [tool, toold]\n')

    assert fetch(root, pins, 'tool') == 0

    for name, body in BINARIES.items():
        assert (root / 'bin' / name).read_bytes() == body
        assert (root / 'bin' / name).stat().st_mode & 0o111
    assert sorted(path.name for path in (root / 'bin').iterdir()) == sorted(BINARIES)


def test_all_fetches_every_entry(root: Path) -> None:
    pins = pin(root, tar_gz({'tool': BINARIES['tool']}))

    assert fetch_tool.main([str(root / 'bin'), '--all', '--pins', str(pins)]) == 0

    assert (root / 'bin/tool').read_bytes() == BINARIES['tool']


def test_a_binary_under_a_directory_in_a_zip(root: Path) -> None:
    pins = pin(
        root,
        zip_bytes({'tool-v1/tool': BINARIES['tool']}),
        '    extension: zip\n    binaries_dir: "tool-{version}"\n',
        suffix='.zip',
    )

    assert fetch(root, pins, 'tool') == 0

    assert (root / 'bin/tool').read_bytes() == BINARIES['tool']


def test_a_bare_binary_is_the_asset_itself(root: Path) -> None:
    pins = pin(root, BINARIES['tool'], '    bare_binary: true\n', suffix='')

    assert fetch(root, pins, 'tool') == 0

    assert (root / 'bin/tool').read_bytes() == BINARIES['tool']
    assert (root / 'bin/tool').stat().st_mode & 0o111


def test_a_deb_is_written_as_its_package_file(root: Path) -> None:
    pins = pin(root, b'!<arch>\n', '    extension: deb\n    deb: true\n', suffix='.deb')

    assert fetch(root, pins, 'tool') == 0

    assert (root / 'bin/tool.deb').read_bytes() == b'!<arch>\n'


def test_a_checksum_mismatch_installs_nothing(root: Path) -> None:
    """An archive that does not hash to its pin is rejected before anything is unpacked."""
    pins = pin(root, tar_gz(BINARIES), '    binaries: [tool, toold]\n', checksum='f' * 64)

    assert fetch(root, pins, 'tool') == 1

    assert list((root / 'bin').iterdir()) == []


def test_a_binary_missing_from_the_archive_installs_nothing(root: Path) -> None:
    """A listed binary the archive lacks is an error, not a partial install."""
    pins = pin(root, tar_gz({'tool': BINARIES['tool']}), '    binaries: [tool, toold]\n')

    assert fetch(root, pins, 'tool') == 1

    assert list((root / 'bin').iterdir()) == []


def test_an_unknown_tool_fails(root: Path) -> None:
    """A name with no pinned entry is reported, not silently skipped."""
    pins = pin(root, tar_gz(BINARIES))

    assert fetch(root, pins, 'other') == 1


def test_the_url_substitutes_the_version_without_its_prefix() -> None:
    tool = {
        'version': 'v2.5.0',
        'url_prefix': 'https://example.invalid/download',
        'asset_prefix': 'tool_{bare_version}_',
        'archives': {'amd64': {'target': 'linux_amd64'}},
    }

    assert fetch_tool.url(tool, 'amd64') == (
        'https://example.invalid/download/v2.5.0/tool_2.5.0_linux_amd64.tar.gz'
    )
