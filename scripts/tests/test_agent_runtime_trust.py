"""Tests for the bootstrap's extra CA trust: the system store holds exactly the bundle's certs."""

from __future__ import annotations

from pathlib import Path

from agentdev_runtime import trust
import pytest


def pem(body: str) -> str:
    return f'-----BEGIN CERTIFICATE-----\n{body}\n-----END CERTIFICATE-----\n'


FIRST = pem('QUFBQQ==')
SECOND = pem('QkJCQg==')


class Store:
    """A certificate store directory and a count of the store updates it saw."""

    def __init__(self, root: Path) -> None:
        self.dir = root / 'ca-certificates'
        self.source = root / 'extra-ca.crt'
        self.updates = 0

    def update(self) -> None:
        self.updates += 1

    def install(self) -> int:
        return trust.install(self.source, self.dir, self.update)

    def installed(self) -> list[str]:
        return [path.read_text() for path in sorted(self.dir.glob(f'{trust.PREFIX}*.crt'))]


@pytest.fixture
def store(tmp_path: Path) -> Store:
    return Store(tmp_path)


def test_each_certificate_in_the_bundle_becomes_one_store_entry(store: Store):
    store.source.write_text(f'Proxy CA\n{FIRST}\r\n{SECOND.replace(chr(10), chr(13) + chr(10))}')

    assert store.install() == 2
    assert store.installed() == [FIRST, SECOND]
    assert store.updates == 1


def test_a_changed_bundle_replaces_the_previous_entries(store: Store):
    store.source.write_text(FIRST + SECOND)
    store.install()
    store.source.write_text(SECOND)

    assert store.install() == 1
    assert store.installed() == [SECOND]
    assert store.updates == 2


@pytest.mark.parametrize('content', [None, '', '\n  \n'])
def test_no_bundle_adds_nothing_and_leaves_the_store_alone(store: Store, content: str | None):
    if content is not None:
        store.source.write_text(content)

    assert store.install() == 0
    assert not store.dir.exists()
    assert store.updates == 0


def test_a_removed_bundle_withdraws_its_entries_and_keeps_others(store: Store):
    store.source.write_text(FIRST)
    store.install()
    other = store.dir / 'site.crt'
    other.write_text(SECOND)
    store.source.unlink()

    assert store.install() == 0
    assert store.installed() == []
    assert other.read_text() == SECOND
    assert store.updates == 2


def test_a_bundle_without_a_certificate_is_refused_and_changes_nothing(store: Store):
    store.source.write_text(FIRST)
    store.install()
    store.source.write_text('not a certificate\n')

    with pytest.raises(trust.TrustError):
        store.install()
    assert store.installed() == [FIRST]
    assert store.updates == 1
