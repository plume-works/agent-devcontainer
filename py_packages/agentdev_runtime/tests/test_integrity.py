"""The installed distribution checked against its RECORD hashes and file set."""

import base64
import hashlib
from importlib import metadata
from pathlib import Path

from agentdev_runtime import integrity
import pytest


def record_line(root: Path, relative: str) -> str:
    digest = hashlib.sha256((root / relative).read_bytes()).digest()
    encoded = base64.urlsafe_b64encode(digest).rstrip(b'=').decode()
    return f'{relative},sha256={encoded},{(root / relative).stat().st_size}'


@pytest.fixture
def installed(tmp_path: Path) -> metadata.Distribution:
    """Lay out site-packages with a package, a dist-info, and an entry point beside it."""
    site = tmp_path / 'lib/site-packages'
    package = site / 'pkg'
    info = site / 'pkg-1.0.dist-info'
    package.mkdir(parents=True)
    info.mkdir()
    (tmp_path / 'bin').mkdir()
    (package / '__init__.py').write_text('')
    (package / 'cli.py').write_text('print(1)\n')
    (info / 'METADATA').write_text('Name: pkg\nVersion: 1.0\n')
    (tmp_path / 'bin/pkg').write_text('#!python\n')
    files = ['pkg/__init__.py', 'pkg/cli.py', 'pkg-1.0.dist-info/METADATA', '../../bin/pkg']
    lines = [record_line(site, name) for name in files]
    (info / 'RECORD').write_text('\n'.join([*lines, 'pkg-1.0.dist-info/RECORD,,']) + '\n')
    return metadata.PathDistribution(info)


def test_an_untouched_install_passes(installed: metadata.Distribution) -> None:
    integrity.verify(installed)


def test_bytecode_written_at_run_time_is_ignored(installed: metadata.Distribution) -> None:
    cache = Path(str(installed.locate_file('pkg/__pycache__')))
    cache.mkdir()
    (cache / 'cli.cpython-312.pyc').write_bytes(b'x')
    integrity.verify(installed)


def test_bytecode_for_no_recorded_module_is_refused(installed: metadata.Distribution) -> None:
    cache = Path(str(installed.locate_file('pkg/__pycache__')))
    cache.mkdir()
    (cache / 'evil.cpython-312.pyc').write_bytes(b'x')
    with pytest.raises(integrity.IntegrityError, match='was added'):
        integrity.verify(installed)


def test_a_removed_metadata_file_is_refused(installed: metadata.Distribution) -> None:
    Path(str(installed.locate_file('pkg-1.0.dist-info/METADATA'))).unlink()
    with pytest.raises(integrity.IntegrityError, match='METADATA differs'):
        integrity.verify(installed)


def test_a_patched_file_is_refused(installed: metadata.Distribution) -> None:
    Path(str(installed.locate_file('pkg/cli.py'))).write_text('print(2)\n')
    with pytest.raises(integrity.IntegrityError, match='differs from the image'):
        integrity.verify(installed)


def test_a_patched_entry_point_is_refused(installed: metadata.Distribution) -> None:
    Path(str(installed.locate_file('../../bin/pkg'))).write_text('#!evil\n')
    with pytest.raises(integrity.IntegrityError, match=integrity.REMEDY):
        integrity.verify(installed)


def test_a_removed_file_is_refused(installed: metadata.Distribution) -> None:
    Path(str(installed.locate_file('pkg/cli.py'))).unlink()
    with pytest.raises(integrity.IntegrityError):
        integrity.verify(installed)


def test_an_added_file_is_refused(installed: metadata.Distribution) -> None:
    Path(str(installed.locate_file('pkg/extra.py'))).write_text('')
    with pytest.raises(integrity.IntegrityError, match='was added'):
        integrity.verify(installed)


def test_the_development_install_passes() -> None:
    integrity.verify()


def test_an_installed_runtime_without_a_record_is_refused(
    installed: metadata.Distribution,
) -> None:
    Path(str(installed.locate_file('pkg-1.0.dist-info/RECORD'))).unlink()
    with pytest.raises(integrity.IntegrityError, match='no RECORD'):
        integrity.verify(installed)


def test_a_source_checkout_is_not_checked(tmp_path: Path) -> None:
    info = tmp_path / 'pkg.egg-info'
    info.mkdir()
    (info / 'PKG-INFO').write_text('Name: pkg\nVersion: 1.0\n')
    integrity.verify(metadata.PathDistribution(info))
