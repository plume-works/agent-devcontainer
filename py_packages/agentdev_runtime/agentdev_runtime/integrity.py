"""
Refuse a runtime whose installed files differ from what the image installed.

A derived image that replaced, added, or removed a package file would run lifecycle code nobody
tested. The installed distribution's ``RECORD`` holds each file's hash. Spec:
agentdev-runtime-images.
"""

from __future__ import annotations

import base64
import csv
import hashlib
from importlib import metadata
from pathlib import Path

DISTRIBUTION = 'agentdev_runtime'
REMEDY = 'extend the runtime through /etc/agentdev/hooks and documented environment instead'
# Bytecode the interpreter writes at run time is never in RECORD.
GENERATED = ('__pycache__',)


class IntegrityError(Exception):
    """An installed file differs from the record, or the file set changed."""


def _digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1 << 16), b''):
            hasher.update(block)
    return base64.urlsafe_b64encode(hasher.digest()).rstrip(b'=').decode()


def _generated(path: Path) -> bool:
    return any(part in GENERATED for part in path.parts)


def _record(distribution: metadata.Distribution) -> list[tuple[str, str]]:
    """Return each ``RECORD`` path and hash; ``files`` would hide a missing file."""
    text = distribution.read_text('RECORD')
    if text is None:
        raise IntegrityError(f'the installed runtime has no RECORD; {REMEDY}')
    return [(row[0], row[1]) for row in csv.reader(text.splitlines()) if row]


def verify(distribution: metadata.Distribution | None = None) -> None:
    """Raise ``IntegrityError`` unless every recorded file matches and nothing was added."""
    if distribution is None:
        try:
            distribution = metadata.distribution(DISTRIBUTION)
        except metadata.PackageNotFoundError:
            return
    # A source checkout's egg-info records nothing; only an installed dist-info carries METADATA.
    if distribution.read_text('METADATA') is None:
        return
    root = Path(str(distribution.locate_file('')))
    rows = _record(distribution)
    recorded: set[Path] = set()
    for relative, hashed in rows:
        path = (root / relative).resolve()
        recorded.add(path)
        if not hashed:
            continue
        algorithm, _, value = hashed.partition('=')
        if not path.is_file() or _digest(path, algorithm) != value:
            raise IntegrityError(f"{path} differs from the image's; {REMEDY}")
    for top in _installed_roots(root, [relative for relative, _ in rows]):
        for path in top.rglob('*'):
            if path.is_dir() or _generated(path.relative_to(root)):
                continue
            if path.resolve() not in recorded:
                raise IntegrityError(f'{path} was added to the installed runtime; {REMEDY}')


def _installed_roots(root: Path, files: list[str]) -> set[Path]:
    """Return the top-level directories the distribution installed below ``root``."""
    roots = set()
    for entry in files:
        parts = Path(entry).parts
        if len(parts) > 1 and parts[0] != '..':
            roots.add(root / parts[0])
    return {path for path in roots if path.is_dir()}
