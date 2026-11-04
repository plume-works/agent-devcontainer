"""Tests that the build action resolves the built architecture's own manifest digest."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

SCRIPT = (
    Path(__file__).resolve().parents[2]
    / '.github/actions/docker/build-push-action/platform-digest.sh'
)
IMAGE = 'registry.example.invalid/acme/demo'
INDEX_DIGEST = 'sha256:' + '1' * 64
AMD64_DIGEST = 'sha256:' + 'a' * 64
ARM64_DIGEST = 'sha256:' + 'b' * 64
ATTESTATION_DIGEST = 'sha256:' + 'c' * 64


def _entry(digest: str, os_name: str, arch: str) -> dict[str, object]:
    """Build one index entry."""
    return {'digest': digest, 'platform': {'os': os_name, 'architecture': arch}}


def _resolve(
    tmp_path: Path, raw: dict[str, object], arch: str
) -> subprocess.CompletedProcess[str]:
    """Run the script against a stub docker that prints raw; return the result."""
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    (tmp_path / 'raw.json').write_text(json.dumps(raw))
    (bin_dir / 'docker').write_text(
        f'#!/usr/bin/env bash\necho "$*" > "{tmp_path}/docker-args"\ncat "{tmp_path}/raw.json"\n'
    )
    (bin_dir / 'docker').chmod(0o755)
    output = tmp_path / 'github-output'
    output.write_text('')
    env = dict(
        os.environ,
        PATH=f'{bin_dir}:{os.environ["PATH"]}',
        IMAGE=IMAGE,
        DIGEST=INDEX_DIGEST,
        ARCH=arch,
        GITHUB_OUTPUT=str(output),
    )
    return subprocess.run([str(SCRIPT)], env=env, capture_output=True, text=True, check=False)


def _output(tmp_path: Path) -> str:
    """Return the GitHub output file's contents."""
    return (tmp_path / 'github-output').read_text()


def test_index_resolves_the_architecture_manifest(tmp_path: Path) -> None:
    """An index with an attestation entry yields the matching linux manifest only."""
    raw = {
        'manifests': [
            _entry(AMD64_DIGEST, 'linux', 'amd64'),
            _entry(ATTESTATION_DIGEST, 'unknown', 'unknown'),
        ]
    }
    result = _resolve(tmp_path, raw, 'amd64')
    assert result.returncode == 0, result.stderr
    assert _output(tmp_path) == f'digest={AMD64_DIGEST}\n'
    args = (tmp_path / 'docker-args').read_text().split()
    assert args == ['buildx', 'imagetools', 'inspect', '--raw', f'{IMAGE}@{INDEX_DIGEST}']


def test_single_manifest_keeps_its_digest(tmp_path: Path) -> None:
    """A digest that names a manifest, not an index, is passed through."""
    result = _resolve(tmp_path, {'config': {'digest': ATTESTATION_DIGEST}, 'layers': []}, 'arm64')
    assert result.returncode == 0, result.stderr
    assert _output(tmp_path) == f'digest={INDEX_DIGEST}\n'


def test_missing_architecture_fails(tmp_path: Path) -> None:
    """An index without the architecture fails and writes no output."""
    raw = {'manifests': [_entry(AMD64_DIGEST, 'linux', 'amd64')]}
    result = _resolve(tmp_path, raw, 'arm64')
    assert result.returncode != 0
    assert 'expected one linux/arm64 manifest, found 0' in result.stderr
    assert _output(tmp_path) == ''


def test_ambiguous_architecture_fails(tmp_path: Path) -> None:
    """An index with two manifests for the architecture fails."""
    raw = {
        'manifests': [
            _entry(AMD64_DIGEST, 'linux', 'amd64'),
            _entry(ARM64_DIGEST, 'linux', 'amd64'),
        ]
    }
    result = _resolve(tmp_path, raw, 'amd64')
    assert result.returncode != 0
    assert _output(tmp_path) == ''
