"""
Extra trust anchors the root bootstrap adds to the system certificate store.

Spec and design: spec/agentdev-runtime-images.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import re
import subprocess

STORE_DIR = Path('/usr/local/share/ca-certificates')
PREFIX = 'agentdev-extra-'
PEM = re.compile(rb'-----BEGIN CERTIFICATE-----\r?\n[A-Za-z0-9+/=\r\n]+?-----END CERTIFICATE-----')


class TrustError(Exception):
    """The extra CA bundle is present but holds no certificate."""


def certificates(data: bytes) -> list[bytes]:
    """Return each PEM certificate in ``data``; text around them is ignored."""
    return [match.group(0).replace(b'\r\n', b'\n') + b'\n' for match in PEM.finditer(data)]


def update_store() -> None:
    subprocess.run(['update-ca-certificates'], check=True, stdout=subprocess.DEVNULL)


def install(
    source: Path,
    store_dir: Path = STORE_DIR,
    update: Callable[[], None] = update_store,
) -> int:
    """Make ``store_dir`` hold exactly the certificates in ``source``; return how many."""
    data = source.read_bytes() if source.exists() else b''
    found = certificates(data)
    if data.strip() and not found:
        raise TrustError('it holds no PEM certificate')
    stale = sorted(store_dir.glob(f'{PREFIX}*.crt')) if store_dir.is_dir() else []
    for path in stale:
        path.unlink()
    if found:
        store_dir.mkdir(parents=True, exist_ok=True)
    for index, certificate in enumerate(found, start=1):
        (store_dir / f'{PREFIX}{index:04d}.crt').write_bytes(certificate)
    if found or stale:
        update()
    return len(found)
