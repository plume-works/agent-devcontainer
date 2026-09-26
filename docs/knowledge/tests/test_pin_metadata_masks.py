"""Repository-level behavior tests for the role-pin and workflow-digest masks."""

from __future__ import annotations

from collections.abc import Callable, Iterator
import hashlib
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / '.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py'
PLUGIN_BIN = REPO_ROOT / '.agents/plugins/agentdev/bin'
TMP_ROOT = REPO_ROOT / '.tmp'
ROLE_FILES = [
    'ansible/roles/.agent.metadata.json',
    'ansible/roles/dev_tools/defaults/main.yml',
    'ansible/roles/agentic_tools/defaults/main.yml',
    'ansible/roles/xpra_setup/defaults/main.yml',
]
WORKFLOW = '.github/workflows/job.yml'
IMAGE = 'ghcr.io/plume-works/agent-desktop:edge'
RENOVATE_PIN = re.compile(r'(# renovate:[^\n]*\n\s*[a-z_]+: "?)([^"\s]+)')
SHA256 = re.compile(r'\b[0-9a-f]{64}\b')


def _load_stale_map_docs():
    """Load the production script so fixture digests use its implementation."""
    sys.path.insert(0, str(PLUGIN_BIN))
    spec = importlib.util.spec_from_file_location('pin_mask_stale_map_docs', SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stale_map_docs = _load_stale_map_docs()


def _git(repository: Path, *arguments: str) -> None:
    """Run Git in the fixture repository, isolated from any outer Git environment."""
    identity = ['-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid']
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    subprocess.run(['git', *identity, *arguments], cwd=repository, check=True, env=env)


def _digest(repository: Path, source: str) -> str:
    """Compute the masked digest a map doc sourcing `source` records."""
    previous = Path.cwd()
    os.chdir(repository)
    try:
        applied: list = []
        resolver = stale_map_docs.MetadataResolver()
        digest = stale_map_docs.source_digest_for_paths([source], resolver, applied)
        return stale_map_docs.fold_in_masks(digest, applied)
    finally:
        os.chdir(previous)


def _workflow(digest: str, image: str = IMAGE) -> str:
    """Return a workflow whose job runs in a digest-pinned container."""
    return f'jobs:\n  job:\n    container:\n      image: {image}@sha256:{digest}\n'


@pytest.fixture
def workspace() -> Iterator[Path]:
    """Build a repository from the checked-in masks and pin files, with fresh map docs."""
    TMP_ROOT.mkdir(exist_ok=True)
    repository = TMP_ROOT / f'pin-masks-{uuid4().hex}'
    try:
        for path in ROLE_FILES + ['.github/.agent.metadata.json']:
            (repository / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(REPO_ROOT / path, repository / path)
        (repository / WORKFLOW).parent.mkdir(parents=True)
        (repository / WORKFLOW).write_text(_workflow('a' * 64))
        (repository / '.iwe').mkdir()
        (repository / '.iwe/config.toml').write_text(
            'version = 3\n\n[library]\npath = "docs/knowledge"\n'
        )
        _git(repository, 'init', '--quiet', '--initial-branch=main')
        _git(repository, 'add', '-A')
        _git(repository, 'commit', '--quiet', '-m', 'fixture')
        for name, source in (('ansible', 'ansible'), ('github', '.github')):
            doc = repository / f'docs/knowledge/data/codebase/{name}.md'
            doc.parent.mkdir(parents=True, exist_ok=True)
            doc.write_text(
                f'---\ntype: codebase\nsource: {source}\n'
                f"source_digest: '{_digest(repository, source)}'\n---\n\n# {name}\n"
            )
        yield repository
    finally:
        shutil.rmtree(repository, ignore_errors=True)


def _verdicts(repository: Path) -> list[str]:
    """Run the production staleness check and return its output lines."""
    completed = subprocess.run(
        [str(SCRIPT)], cwd=repository, check=False, capture_output=True, text=True
    )
    return completed.stdout.splitlines()


def _edit_roles(repository: Path, edit: Callable[[str], str]) -> None:
    """Apply one text edit to every role pin file."""
    for path in ROLE_FILES[1:]:
        target = repository / path
        target.write_text(edit(target.read_text()))


def _bump_pins(text: str) -> str:
    """Move every Renovate-managed version and every checksum, as automerged bumps do."""
    text = RENOVATE_PIN.sub(lambda match: f'{match[1]}{match[2]}9', text)
    return SHA256.sub(lambda match: hashlib.sha256(match[0].encode()).hexdigest(), text)


def test_pin_and_checksum_bumps_keep_the_role_map_fresh(workspace: Path) -> None:
    """Version and checksum moves in every checksum-carrying pin file are masked."""
    _edit_roles(workspace, _bump_pins)

    assert 'FRESH data/codebase/ansible' in _verdicts(workspace)


@pytest.mark.parametrize(
    'edit',
    [
        lambda text: text.replace('version: v1.22.0', 'version: v1.23.0'),
        lambda text: text.replace('url_prefix: https://github.com/iwe-org/', 'url_prefix: x/'),
        lambda text: text.replace('depName=oven-sh/bun', 'depName=oven-sh/bunx'),
    ],
    ids=['unmanaged-zizmor-version', 'download-url', 'renovate-comment'],
)
def test_role_changes_beyond_pins_stay_watched(
    workspace: Path, edit: Callable[[str], str]
) -> None:
    """Zizmor's version, a download URL, and a Renovate comment still invalidate the map."""
    _edit_roles(workspace, edit)

    assert any(line.startswith('STALE data/codebase/ansible ') for line in _verdicts(workspace))


def test_container_digest_bump_keeps_the_workflow_map_fresh(workspace: Path) -> None:
    """A digest-only move of a workflow container image is masked."""
    (workspace / WORKFLOW).write_text(_workflow('b' * 64))

    assert 'FRESH data/codebase/github' in _verdicts(workspace)


def test_container_image_change_stays_watched(workspace: Path) -> None:
    """Changing the image itself, not only its digest, invalidates the workflow map."""
    (workspace / WORKFLOW).write_text(_workflow('a' * 64, image=f'{IMAGE}-other'))

    assert any(line.startswith('STALE data/codebase/github ') for line in _verdicts(workspace))
