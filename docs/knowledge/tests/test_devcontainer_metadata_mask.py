"""Repository-level behavior tests for the Dev Container digest mask."""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Callable
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / '.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py'
PLUGIN_BIN = REPO_ROOT / '.agents/plugins/agentdev/bin'
METADATA = REPO_ROOT / '.devcontainer/.agent.metadata.json'
DEVCONTAINER = REPO_ROOT / '.devcontainer/devcontainer.json'
TMP_ROOT = REPO_ROOT / '.tmp'
FEATURE = 'ghcr.io/devcontainers/features/docker-in-docker'
FEATURE_ENTRY = re.compile(
    rf'(?m)^\s*"(?P<feature>{re.escape(FEATURE)}):(?P<version>\d+(?:\.\d+)*)": \{{\}},?$'
)
GIT_IDENTITY = ['-c', 'user.name=Fixture Author', '-c', 'user.email=fixture@example.invalid']


def _load_stale_map_docs():
    """Load the production script so the fixture digest uses its implementation."""
    sys.path.insert(0, str(PLUGIN_BIN))
    spec = importlib.util.spec_from_file_location('repo_stale_map_docs', SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


stale_map_docs = _load_stale_map_docs()


def _git(repository: Path, *arguments: str) -> None:
    """Run Git in the isolated repository."""
    subprocess.run(
        ['git', *GIT_IDENTITY, *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )


def _digest(repository: Path) -> str:
    """Compute the masked digest recorded by the fixture's map document."""
    previous = Path.cwd()
    os.chdir(repository)
    try:
        applied: list = []
        resolver = stale_map_docs.MetadataResolver()
        digest = stale_map_docs.source_digest_for_paths(['.devcontainer'], resolver, applied)
        return stale_map_docs.fold_in_masks(digest, applied)
    finally:
        os.chdir(previous)


@pytest.fixture
def production_mask_workspace() -> Path:
    """Build a repository using the checked-in mask and Dev Container file."""
    TMP_ROOT.mkdir(exist_ok=True)
    repository = TMP_ROOT / f'devcontainer-mask-{uuid4().hex}'
    try:
        (repository / '.devcontainer').mkdir(parents=True)
        (repository / '.iwe').mkdir()
        (repository / '.devcontainer/.agent.metadata.json').write_text(METADATA.read_text())
        (repository / '.devcontainer/devcontainer.json').write_text(DEVCONTAINER.read_text())
        (repository / '.iwe/config.toml').write_text(
            'version = 3\n\n[library]\npath = "docs/knowledge"\n'
        )
        _git(repository, 'init', '--initial-branch=main')
        _git(repository, 'add', '.devcontainer', '.iwe/config.toml')
        _git(repository, 'commit', '-m', 'add devcontainer')

        digest = _digest(repository)
        map_doc = repository / 'docs/knowledge/data/codebase/devcontainer.md'
        map_doc.parent.mkdir(parents=True)
        map_doc.write_text(
            '---\n'
            'type: codebase\n'
            'source: .devcontainer\n'
            f"source_digest: '{digest}'\n"
            '---\n\n'
            '# Dev Container\n'
        )
        yield repository
    finally:
        shutil.rmtree(repository, ignore_errors=True)


def _feature_match(content: str) -> re.Match[str]:
    """Find the production feature entry and require exactly one match."""
    matches = list(FEATURE_ENTRY.finditer(content))
    assert len(matches) == 1, f'expected one {FEATURE} entry, found {len(matches)}'
    return matches[0]


def _bump_feature_version(content: str) -> str:
    """Increment the final component of the checked-in feature version."""
    match = _feature_match(content)
    components = match.group('version').split('.')
    components[-1] = str(int(components[-1]) + 1)
    return (
        content[: match.start('version')] + '.'.join(components) + content[match.end('version') :]
    )


def _remove_feature(content: str) -> str:
    """Remove the complete checked-in feature entry."""
    match = _feature_match(content)
    newline = 1 if content[match.end() :].startswith('\n') else 0
    return content[: match.start()] + content[match.end() + newline :]


def _rename_feature(content: str) -> str:
    """Change the checked-in feature identity while retaining its version."""
    match = _feature_match(content)
    renamed = f'{FEATURE}-renamed'
    return content[: match.start('feature')] + renamed + content[match.end('feature') :]


def _write_devcontainer(repository: Path, content: str) -> None:
    """Replace the fixture's Dev Container definition."""
    (repository / '.devcontainer/devcontainer.json').write_text(content)


def _run_staleness_check(repository: Path) -> subprocess.CompletedProcess[str]:
    """Run the production stale-map command against the fixture."""
    return subprocess.run(
        [str(SCRIPT)],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )


def test_production_mask_keeps_a_feature_version_bump_fresh(
    production_mask_workspace: Path,
) -> None:
    """The checked-in mask ignores a version-only change to the real feature shape."""
    devcontainer = production_mask_workspace / '.devcontainer/devcontainer.json'
    _write_devcontainer(production_mask_workspace, _bump_feature_version(devcontainer.read_text()))

    completed = _run_staleness_check(production_mask_workspace)

    assert completed.returncode == 0, completed.stderr
    assert 'FRESH data/codebase/devcontainer' in completed.stdout.splitlines()
    assert completed.stdout.splitlines()[-1] == 'RESULT=SUCCESS'


@pytest.mark.parametrize(
    'mutation',
    [_remove_feature, _rename_feature],
    ids=['feature-removed', 'feature-renamed'],
)
def test_production_mask_keeps_feature_identity_under_surveillance(
    production_mask_workspace: Path,
    mutation: Callable[[str], str],
) -> None:
    """Removing or renaming the feature invalidates the checked-in map digest."""
    devcontainer = production_mask_workspace / '.devcontainer/devcontainer.json'
    _write_devcontainer(production_mask_workspace, mutation(devcontainer.read_text()))

    completed = _run_staleness_check(production_mask_workspace)

    assert completed.returncode == 3, completed.stderr
    assert any(
        line.startswith('STALE data/codebase/devcontainer source_digest ')
        for line in completed.stdout.splitlines()
    )
    assert completed.stdout.splitlines()[-1] == 'RESULT=STALE_FOUND'
