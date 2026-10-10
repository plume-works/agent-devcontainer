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

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / 'scripts/fetch-pinned-tool.py'
TMP_ROOT = REPO_ROOT / '.tmp'


def _load_script():
    """Load the hyphen-named script as a module."""
    spec = importlib.util.spec_from_file_location('fetch_pinned_tool', SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


fetch_tool = _load_script()
DEV_TOOLS = fetch_tool.DEV_TOOLS_DEFAULTS
DEV_TOOLS_TASK = fetch_tool._refresh_module().PIN_FILES[DEV_TOOLS].task_file
BINARIES = {'tool': b'#!/bin/sh\necho tool\n', 'toold': b'#!/bin/sh\necho toold\n'}


def archive(files: dict[str, bytes]) -> bytes:
    """Return a flat tar.gz holding the given files."""
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as bundle:
        for name, body in files.items():
            info = tarfile.TarInfo(name)
            info.size = len(body)
            bundle.addfile(info, io.BytesIO(body))
    return buffer.getvalue()


@pytest.fixture
def repo() -> Iterator[Path]:
    """Create a tree with the real install task and an empty release directory."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'fetch-pinned-tool-{uuid4().hex}'
    (root / DEV_TOOLS_TASK).parent.mkdir(parents=True)
    (root / DEV_TOOLS).parent.mkdir(parents=True, exist_ok=True)
    (root / 'releases/v1').mkdir(parents=True)
    shutil.copy(REPO_ROOT / DEV_TOOLS_TASK, root / DEV_TOOLS_TASK)
    try:
        yield root
    finally:
        shutil.rmtree(root)


def pin(root: Path, body: bytes, checksum: str | None = None) -> None:
    """Publish body as every architecture's archive and pin it under that checksum."""
    for target in ('x86_64-linux', 'aarch64-linux'):
        (root / f'releases/v1/tool-{target}.tar.gz').write_bytes(body)
    digest = checksum or hashlib.sha256(body).hexdigest()
    (root / DEV_TOOLS).write_text(
        'dev_tools_pinned_tools:\n'
        '  - name: tool\n'
        '    version: v1\n'
        f'    url_prefix: file://{root / "releases"}\n'
        '    asset_prefix: tool-\n'
        '    binaries: [tool, toold]\n'
        '    archives:\n'
        '      amd64:\n'
        '        target: x86_64-linux\n'
        f'        checksum: {digest}\n'
        '      arm64:\n'
        '        target: aarch64-linux\n'
        f'        checksum: {digest}\n'
    )


def test_installs_every_binary_executable(repo: Path) -> None:
    """Each listed binary lands in the destination with its archived content."""
    pin(repo, archive(BINARIES))

    code = fetch_tool.main(['tool', str(repo / 'bin'), '--repo-root', str(repo)])

    assert code == 0
    for name, body in BINARIES.items():
        assert (repo / 'bin' / name).read_bytes() == body
        assert (repo / 'bin' / name).stat().st_mode & 0o111
    assert sorted(path.name for path in (repo / 'bin').iterdir()) == sorted(BINARIES)


def test_a_checksum_mismatch_installs_nothing(repo: Path) -> None:
    """An archive that does not hash to its pin is rejected before anything is unpacked."""
    pin(repo, archive(BINARIES), checksum='f' * 64)

    code = fetch_tool.main(['tool', str(repo / 'bin'), '--repo-root', str(repo)])

    assert code == 1
    assert list((repo / 'bin').iterdir()) == []


def test_a_binary_missing_from_the_archive_fails(repo: Path) -> None:
    """A listed binary the archive lacks is an error, not a partial install."""
    pin(repo, archive({'tool': BINARIES['tool']}))

    code = fetch_tool.main(['tool', str(repo / 'bin'), '--repo-root', str(repo)])

    assert code == 1


def test_an_unknown_tool_fails(repo: Path) -> None:
    """A name with no pinned entry is reported, not silently skipped."""
    pin(repo, archive(BINARIES))

    code = fetch_tool.main(['other', str(repo / 'bin'), '--repo-root', str(repo)])

    assert code == 1
