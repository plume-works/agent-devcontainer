"""Tests for scripts/cache-git-ppa-release.py against a locally signed fake PPA."""

from __future__ import annotations

from collections.abc import Iterator
import gzip
import hashlib
import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / 'scripts/cache-git-ppa-release.py'
VERSION = '1:2.47.1-0ppa1~ubuntu24.04.1'
TAG = 'pinned-deps/git/2.47.1-0ppa1-ubuntu24.04.1'
GH_STUB = """#!/usr/bin/env bash
echo "gh $*" >> "$GH_LOG"
for arg in "$@"; do [ -f "$arg" ] && sha256sum "$arg" >> "$GH_LOG"; done
[ "$1 $2" = 'release view' ] && exit "$(cat "$GH_VIEW_STATUS")"
exit 0
"""


def _load_script():
    """Load the hyphen-named script as a module."""
    spec = importlib.util.spec_from_file_location('cache_git_ppa_release', SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


cache = _load_script()


def gpg(home: Path, *args: str) -> str:
    """Run gpg in a scratch home and return its stdout."""
    return subprocess.run(
        ['gpg', '--homedir', str(home), '--batch', '--pinentry-mode', 'loopback', *args],
        capture_output=True,
        text=True,
        check=True,
    ).stdout


def new_key(home: Path, name: str) -> str:
    """Create a signing key in a scratch home and return its fingerprint."""
    home.mkdir(mode=0o700)
    gpg(
        home,
        '--passphrase',
        '',
        '--quick-gen-key',
        f'{name} <{name}@example.invalid>',
        'ed25519',
        'sign',
        'never',
    )
    listing = gpg(home, '--with-colons', '--list-keys')
    return next(line.split(':')[9] for line in listing.splitlines() if line.startswith('fpr:'))


def packages_index(arch: str, debs: dict[str, bytes]) -> bytes:
    """Return a gzipped Packages index that lists git and git-man for one architecture."""
    stanzas = []
    for name in ('git', 'git-man'):
        deb_arch = 'all' if name == 'git-man' else arch
        body = debs[f'{name}_{deb_arch}']
        stanzas.append(
            f'Package: {name}\nVersion: {VERSION}\nArchitecture: {deb_arch}\n'
            f'Filename: pool/main/g/git/{name}_{deb_arch}.deb\n'
            f'Size: {len(body)}\nSHA256: {hashlib.sha256(body).hexdigest()}\n'
        )
    return gzip.compress('\n'.join(stanzas).encode())


class FakePpa:
    """The URLs the script downloads, served from memory, and the key that signs them."""

    def __init__(self, scratch: Path) -> None:
        self.home = scratch / 'ppa-gnupg'
        self.fingerprint = new_key(self.home, 'ppa')
        self.debs = {
            key: f'{key} package body'.encode()
            for key in ('git_amd64', 'git_arm64', 'git-man_all')
        }
        self.urls: dict[str, bytes] = {}
        self.indexes = {arch: packages_index(arch, self.debs) for arch in cache.ARCHITECTURES}
        for key, body in self.debs.items():
            name, arch = key.split('_')
            self.urls[f'{cache.PPA}/pool/main/g/git/{name}_{arch}.deb'] = body
        for arch, body in self.indexes.items():
            self.urls[f'{cache.PPA}/dists/{cache.SERIES}/main/binary-{arch}/Packages.gz'] = body
        self.sign(self.home)

    def sign(self, home: Path) -> None:
        """Publish an InRelease that chains to the current indexes, signed in ``home``."""
        rows = ''.join(
            f' {hashlib.sha256(body).hexdigest()} {len(body)} main/binary-{arch}/Packages.gz\n'
            for arch, body in self.indexes.items()
        )
        plain = home / 'InRelease.txt'
        plain.write_text(f'Origin: fake\nSuite: {cache.SERIES}\nSHA256:\n{rows}')
        signed = gpg(home, '--passphrase', '', '--clearsign', '--output', '-', str(plain))
        self.urls[f'{cache.PPA}/dists/{cache.SERIES}/InRelease'] = signed.encode()

    def fetch(self, url: str) -> bytes:
        if url not in self.urls:
            raise cache.CacheError(f'download failed: {url}: not served')
        return self.urls[url]


@pytest.fixture
def scratch() -> Iterator[Path]:
    root = TMP_ROOT / f'ppa-{uuid4().hex[:8]}'
    root.mkdir(parents=True)
    yield root
    subprocess.run(['gpgconf', '--homedir', str(root / 'ppa-gnupg'), '--kill', 'all'], check=False)
    shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def ppa(scratch: Path, monkeypatch: pytest.MonkeyPatch) -> FakePpa:
    """Serve a signed fake PPA, pin its key in the script, and record ``gh`` calls."""
    fake = FakePpa(scratch)
    key_file = scratch / 'pinned.asc'
    key_file.write_text(gpg(fake.home, '--armor', '--export', fake.fingerprint))
    monkeypatch.setattr(cache, 'KEY_FILE', key_file)
    monkeypatch.setattr(cache, 'KEY_FINGERPRINT', fake.fingerprint)
    monkeypatch.setattr(cache, 'fetch', fake.fetch)
    bin_dir = scratch / 'bin'
    bin_dir.mkdir()
    (bin_dir / 'gh').write_text(GH_STUB)
    (bin_dir / 'gh').chmod(0o755)
    (scratch / 'view-status').write_text('1')
    monkeypatch.setenv('PATH', f'{bin_dir}:{os.environ["PATH"]}')
    monkeypatch.setenv('GNUPGHOME', str(fake.home))
    monkeypatch.setenv('GH_LOG', str(scratch / 'gh.log'))
    monkeypatch.setenv('GH_VIEW_STATUS', str(scratch / 'view-status'))
    return fake


def gh_log(scratch: Path) -> str:
    log = scratch / 'gh.log'
    return log.read_text() if log.exists() else ''


def test_a_verified_build_is_released_unchanged_and_not_as_latest(
    ppa: FakePpa, scratch: Path
) -> None:
    assert cache.main([]) == 0

    log = gh_log(scratch)
    create = next(line for line in log.splitlines() if line.startswith('gh release create'))
    assert f'gh release create {TAG} ' in create
    assert create.endswith('--latest=false')
    for body in ppa.debs.values():
        assert hashlib.sha256(body).hexdigest() in log


def test_an_existing_release_is_never_replaced(ppa: FakePpa, scratch: Path) -> None:
    (scratch / 'view-status').write_text('0')

    assert cache.main([]) == 0

    assert 'release create' not in gh_log(scratch)


def test_an_index_signed_by_another_key_publishes_nothing(
    ppa: FakePpa, scratch: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    other = scratch / 'other-gnupg'
    new_key(other, 'other')
    ppa.sign(other)
    subprocess.run(['gpgconf', '--homedir', str(other), '--kill', 'all'], check=False)

    assert cache.main([]) == 1

    assert 'lacks a valid signature' in capsys.readouterr().err
    assert gh_log(scratch) == ''


def test_an_index_that_breaks_the_hash_chain_publishes_nothing(
    ppa: FakePpa, scratch: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ppa.urls[f'{cache.PPA}/dists/{cache.SERIES}/main/binary-arm64/Packages.gz'] = gzip.compress(
        b'Package: git\n'
    )

    assert cache.main([]) == 1

    assert 'binary-arm64/Packages.gz hashes to' in capsys.readouterr().err
    assert gh_log(scratch) == ''


def test_a_package_that_breaks_the_hash_chain_publishes_nothing(
    ppa: FakePpa, scratch: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    ppa.urls[f'{cache.PPA}/pool/main/g/git/git_amd64.deb'] = b'tampered'

    assert cache.main([]) == 1

    assert 'git_amd64.deb hashes to' in capsys.readouterr().err
    assert 'release create' not in gh_log(scratch)
