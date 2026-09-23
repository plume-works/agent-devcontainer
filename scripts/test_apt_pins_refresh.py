"""Tests for the apt pin refresh package-index cache."""

import gzip
import importlib.util
import os
import pathlib
from types import ModuleType
import urllib.error

import pytest

SCRIPT_PATH = pathlib.Path(__file__).with_name('apt-pins-refresh.py')
CACHE_NAME = 'https_archive_example_dists_noble_main_binary_amd64.gz'


@pytest.fixture
def apt_pins_refresh() -> ModuleType:
    """Load the hyphenated refresh script as an importable module."""
    spec = importlib.util.spec_from_file_location('apt_pins_refresh', SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def component_url() -> str:
    """Return a representative apt component URL."""
    return 'https://archive.example/dists/noble/main/binary-amd64'


def packages_payload(version: str) -> bytes:
    """Build a compressed single-package index."""
    contents = f'Package: example\nVersion: {version}\n\n'.encode()
    return gzip.compress(contents)


class Response:
    """Provide the context-manager interface returned by urlopen."""

    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> 'Response':
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        """Return the configured response payload."""
        return self.payload


def raise_error(error: Exception) -> None:
    """Raise a configured download error from a urlopen replacement."""
    raise error


def test_fetch_index_reuses_fresh_cache(
    apt_pins_refresh: ModuleType,
    component_url: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Avoid a network request while the cached index is fresh."""
    monkeypatch.setattr(apt_pins_refresh, 'CACHE_DIR', tmp_path)
    monkeypatch.setattr(apt_pins_refresh.time, 'time', lambda: 1_000.0)
    cached = tmp_path / CACHE_NAME
    cached.write_bytes(packages_payload('1.0'))
    os.utime(cached, (999.0, 999.0))

    def unexpected_request(*_args: object, **_kwargs: object) -> None:
        pytest.fail('fresh cache triggered a network request')

    monkeypatch.setattr(apt_pins_refresh.urllib.request, 'urlopen', unexpected_request)

    assert apt_pins_refresh.fetch_index(component_url) == {'example': ['1.0']}


@pytest.mark.parametrize('cached_at', [900.0, 2_000.0])
def test_fetch_index_refreshes_expired_or_future_cache(
    apt_pins_refresh: ModuleType,
    component_url: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    cached_at: float,
) -> None:
    """Replace an expired or future-dated package index."""
    monkeypatch.setattr(apt_pins_refresh, 'CACHE_DIR', tmp_path)
    monkeypatch.setattr(apt_pins_refresh, 'CACHE_TTL_SECONDS', 100)
    monkeypatch.setattr(apt_pins_refresh.time, 'time', lambda: 1_000.0)
    cached = tmp_path / CACHE_NAME
    cached.write_bytes(packages_payload('1.0'))
    os.utime(cached, (cached_at, cached_at))
    monkeypatch.setattr(
        apt_pins_refresh.urllib.request,
        'urlopen',
        lambda *_args, **_kwargs: Response(packages_payload('2.0')),
    )

    assert apt_pins_refresh.fetch_index(component_url) == {'example': ['2.0']}


def test_fetch_index_treats_404_as_empty(
    apt_pins_refresh: ModuleType,
    component_url: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return an empty index for a missing component."""
    monkeypatch.setattr(apt_pins_refresh, 'CACHE_DIR', tmp_path)
    error = urllib.error.HTTPError(component_url, 404, 'Not Found', {}, None)
    monkeypatch.setattr(
        apt_pins_refresh.urllib.request,
        'urlopen',
        lambda *_args, **_kwargs: raise_error(error),
    )

    assert apt_pins_refresh.fetch_index(component_url) == {}


@pytest.mark.parametrize(
    'error',
    [
        urllib.error.HTTPError('https://example.invalid', 403, 'Forbidden', {}, None),
        urllib.error.URLError('network unavailable'),
        TimeoutError('timed out'),
    ],
)
def test_fetch_index_fails_on_non_404_download_errors(
    apt_pins_refresh: ModuleType,
    component_url: str,
    tmp_path: pathlib.Path,
    monkeypatch: pytest.MonkeyPatch,
    error: Exception,
) -> None:
    """Fail rather than resolving pins from an incomplete repository view."""
    monkeypatch.setattr(apt_pins_refresh, 'CACHE_DIR', tmp_path)
    monkeypatch.setattr(
        apt_pins_refresh.urllib.request,
        'urlopen',
        lambda *_args, **_kwargs: raise_error(error),
    )

    with pytest.raises(SystemExit):
        apt_pins_refresh.fetch_index(component_url)
    assert not (tmp_path / CACHE_NAME).exists()
