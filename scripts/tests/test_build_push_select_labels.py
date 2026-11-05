"""Tests that the build action drops only the per-run labels when asked for stable labels."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / '.github/actions/docker/build-push-action/select-labels.sh'
STATIC_LABELS = [
    'org.opencontainers.image.title=demo-image',
    'org.opencontainers.image.source=https://example.invalid/acme/demo',
    'org.opencontainers.image.licenses=MIT',
]
PER_RUN_LABELS = [
    'org.opencontainers.image.created=2030-01-02T03:04:05.678Z',
    'org.opencontainers.image.revision=' + 'f' * 40,
    'org.opencontainers.image.version=pr-7',
]


def _select(tmp_path: Path, labels: list[str], stable: str | None) -> list[str]:
    """Run the script with the given labels; return the labels output as a list."""
    output = tmp_path / 'github-output'
    output.write_text('')
    env = dict(os.environ, LABELS='\n'.join(labels), GITHUB_OUTPUT=str(output))
    env.pop('STABLE_LABELS', None)
    if stable is not None:
        env['STABLE_LABELS'] = stable
    subprocess.run([str(SCRIPT)], env=env, check=True)
    lines = output.read_text().splitlines()
    head, delimiter = lines[0].split('<<', 1)
    assert head == 'labels'
    assert lines[-1] == delimiter
    return [line for line in lines[1:-1] if line]


def test_stable_labels_drop_only_per_run_labels(tmp_path: Path) -> None:
    """With stable labels, created, revision, and version go; the rest stay in order."""
    labels = PER_RUN_LABELS[:1] + STATIC_LABELS[:2] + PER_RUN_LABELS[1:] + STATIC_LABELS[2:]
    assert _select(tmp_path, labels, 'true') == STATIC_LABELS


@pytest.mark.parametrize('stable', [None, 'false'])
def test_default_keeps_every_label(tmp_path: Path, stable: str | None) -> None:
    """Without stable labels, every label passes through unchanged."""
    labels = STATIC_LABELS + PER_RUN_LABELS
    assert _select(tmp_path, labels, stable) == labels


def test_stable_labels_with_only_per_run_labels(tmp_path: Path) -> None:
    """Dropping every label still writes a well-formed, empty output."""
    assert _select(tmp_path, PER_RUN_LABELS, 'true') == []
