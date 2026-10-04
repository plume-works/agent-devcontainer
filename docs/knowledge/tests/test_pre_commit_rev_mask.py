"""Repository-level behavior tests for the pre-commit hook revision mask."""

from __future__ import annotations

from collections.abc import Callable, Iterator
import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from types import ModuleType
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / '.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py'
PLUGIN_BIN = REPO_ROOT / '.agents/plugins/agentdev/bin'
TMP_ROOT = REPO_ROOT / '.tmp'
CONFIG = '.pre-commit-config.yaml'
REV = re.compile(r'(?m)^(\s+rev: )(\S+)$')


def _load_stale_map_docs() -> ModuleType:
    """Load the production script so fixture digests use its implementation."""
    sys.path.insert(0, str(PLUGIN_BIN))
    spec = importlib.util.spec_from_file_location('rev_mask_stale_map_docs', SCRIPT)
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


def _digest(repository: Path) -> str:
    """Compute the masked digest a map doc sourcing the hook config records."""
    previous = Path.cwd()
    os.chdir(repository)
    try:
        applied: list = []
        resolver = stale_map_docs.MetadataResolver()
        digest = stale_map_docs.source_digest_for_paths([CONFIG], resolver, applied)
        return stale_map_docs.fold_in_masks(digest, applied)
    finally:
        os.chdir(previous)


@pytest.fixture
def workspace(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Build a repository from the checked-in mask and hook config, with a fresh map doc."""
    # A hook under `git commit -a` exports an absolute GIT_INDEX_FILE.
    # See bugs/fixture-git-inherits-commit-index.
    for name in [name for name in os.environ if name.startswith('GIT_')]:
        monkeypatch.delenv(name)
    TMP_ROOT.mkdir(exist_ok=True)
    repository = TMP_ROOT / f'rev-mask-{uuid4().hex}'
    try:
        repository.mkdir()
        for path in ('.agent.metadata.json', CONFIG):
            shutil.copy(REPO_ROOT / path, repository / path)
        (repository / '.iwe').mkdir()
        (repository / '.iwe/config.toml').write_text(
            'version = 3\n\n[library]\npath = "docs/knowledge"\n'
        )
        _git(repository, 'init', '--quiet', '--initial-branch=main')
        _git(repository, 'add', '-A')
        _git(repository, 'commit', '--quiet', '-m', 'fixture')
        doc = repository / 'docs/knowledge/data/codebase/checks.md'
        doc.parent.mkdir(parents=True)
        doc.write_text(
            f'---\ntype: codebase\nsource:\n- {CONFIG}\n'
            f"source_digest: '{_digest(repository)}'\n---\n\n# checks\n"
        )
        yield repository
    finally:
        shutil.rmtree(repository, ignore_errors=True)


def _verdicts(repository: Path, edit: Callable[[str], str]) -> list[str]:
    """Edit the hook config, run the production staleness check, and return its output."""
    config = repository / CONFIG
    config.write_text(edit(config.read_text()))
    completed = subprocess.run(
        [str(SCRIPT)], cwd=repository, check=False, capture_output=True, text=True
    )
    return completed.stdout.splitlines()


def test_hook_rev_bumps_keep_the_map_fresh(workspace: Path) -> None:
    """Every hook `rev` moving at once, as Renovate's pre-commit bumps do, is masked."""
    verdicts = _verdicts(workspace, lambda text: REV.sub(r'\g<1>\g<2>.9', text))

    assert 'FRESH data/codebase/checks' in verdicts


@pytest.mark.parametrize(
    'edit',
    [
        lambda text: text.replace('id: end-of-file-fixer', 'id: trailing-whitespace', 1),
        lambda text: text.replace('https://github.com/', 'https://gitlab.com/', 1),
    ],
    ids=['hook-id', 'hook-repository'],
)
def test_hook_changes_beyond_rev_stay_watched(workspace: Path, edit: Callable[[str], str]) -> None:
    """Changing which hook runs, or where it comes from, still invalidates the map."""
    verdicts = _verdicts(workspace, edit)

    assert any(line.startswith('STALE data/codebase/checks ') for line in verdicts)
