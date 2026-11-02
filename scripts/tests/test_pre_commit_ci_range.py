"""Tests for scripts/pre-commit-ci-range.py against event payloads and a scratch repository."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / 'scripts/pre-commit-ci-range.py'


def _load_script():
    """Load the hyphen-named script as a module."""
    spec = importlib.util.spec_from_file_location('pre_commit_ci_range', SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ci_range = _load_script()
ZERO = '0' * 40


@dataclass(frozen=True)
class Repo:
    """A scratch repository with a base commit and helpers to add more."""

    root: Path

    def git(self, *arguments: str) -> str:
        """Run Git with a fixed identity and return its stdout."""
        identity = ['-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid']
        return subprocess.run(
            ['git', *identity, *arguments],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def commit(self, path: str) -> str:
        """Commit a change to path and return the new commit's SHA."""
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(uuid4().hex)
        self.git('add', path)
        self.git('commit', '--quiet', '-m', path)
        return self.git('rev-parse', 'HEAD')

    def run(self, event_name: str, payload: dict[str, object]) -> dict[str, str]:
        """Run the script for an event and return what it wrote to GITHUB_OUTPUT."""
        event = self.root.parent / f'{self.root.name}-event.json'
        output = self.root.parent / f'{self.root.name}-output'
        event.write_text(json.dumps(payload))
        output.write_text('')
        env = {
            'GITHUB_EVENT_NAME': event_name,
            'GITHUB_EVENT_PATH': str(event),
            'GITHUB_OUTPUT': str(output),
        }
        assert ci_range.main(env=env, cwd=self.root) == 0
        return dict(line.split('=', 1) for line in output.read_text().splitlines())


@pytest.fixture
def repo(monkeypatch: pytest.MonkeyPatch) -> Iterator[Repo]:
    """Create a scratch repository holding one source file."""
    for name in ('GIT_DIR', 'GIT_INDEX_FILE', 'GIT_WORK_TREE'):
        monkeypatch.delenv(name, raising=False)
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'pre-commit-ci-range-{uuid4().hex}'
    root.mkdir()
    try:
        scratch = Repo(root)
        scratch.git('init', '--quiet', '--initial-branch=main')
        scratch.commit('src/app.py')
        yield scratch
    finally:
        for leftover in root.parent.glob(f'{root.name}*'):
            if leftover.is_dir():
                shutil.rmtree(leftover)
            else:
                leftover.unlink()


def ranged(base: str, head: str) -> dict[str, str]:
    """Return the outputs of a range that checks only its changed files."""
    return {
        'from_ref': base,
        'to_ref': head,
        'all_files': 'false',
        'gitleaks_log_opts': f'{base}..{head}',
    }


def test_pull_request_checks_base_to_head(repo: Repo) -> None:
    """A pull request is checked between its base and head commits."""
    base = repo.git('rev-parse', 'HEAD')
    head = repo.commit('src/feature.py')
    payload = {'pull_request': {'base': {'sha': base}, 'head': {'sha': head}}}

    assert repo.run('pull_request', payload) == ranged(base, head)


def test_merge_group_checks_base_to_head(repo: Repo) -> None:
    """A merge queue entry is checked between its base and head commits."""
    base = repo.git('rev-parse', 'HEAD')
    head = repo.commit('src/feature.py')
    payload = {'merge_group': {'base_sha': base, 'head_sha': head}}

    assert repo.run('merge_group', payload) == ranged(base, head)


def test_push_checks_before_to_after(repo: Repo) -> None:
    """A push is checked between its before and after commits."""
    before = repo.git('rev-parse', 'HEAD')
    after = repo.commit('src/feature.py')

    assert repo.run('push', {'before': before, 'after': after}) == ranged(before, after)


def test_push_creating_a_ref_checks_every_file(repo: Repo) -> None:
    """A push with an all-zero before checks every file and scans the pushed commit."""
    after = repo.git('rev-parse', 'HEAD')

    assert repo.run('push', {'before': ZERO, 'after': after}) == {
        'from_ref': '',
        'to_ref': '',
        'all_files': 'true',
        'gitleaks_log_opts': f'-1 {after}',
    }


def test_manual_run_checks_every_file_and_all_history(repo: Repo) -> None:
    """workflow_dispatch checks every file and scans every commit."""
    assert repo.run('workflow_dispatch', {}) == {
        'from_ref': '',
        'to_ref': '',
        'all_files': 'true',
        'gitleaks_log_opts': '--all',
    }


@pytest.mark.parametrize('owner', ci_range.TOOL_VERSION_OWNERS)
def test_tool_version_change_checks_every_file_with_the_range_scan(repo: Repo, owner: str) -> None:
    """A range touching a tool-version owner checks every file but still scans the range."""
    base = repo.git('rev-parse', 'HEAD')
    head = repo.commit(owner)
    payload = {'pull_request': {'base': {'sha': base}, 'head': {'sha': head}}}

    assert repo.run('pull_request', payload) == {
        **ranged(base, head),
        'all_files': 'true',
    }


def test_owner_change_on_the_base_side_does_not_widen_the_check(repo: Repo) -> None:
    """Only the range's own changes count: an owner edited on the base since the fork does not."""
    fork = repo.git('rev-parse', 'HEAD')
    repo.git('switch', '--quiet', '-c', 'feature')
    head = repo.commit('src/feature.py')
    repo.git('switch', '--quiet', 'main')
    base = repo.commit('uv.lock')
    payload = {'pull_request': {'base': {'sha': base}, 'head': {'sha': head}}}

    assert fork != base
    assert repo.run('pull_request', payload) == ranged(base, head)


def test_unknown_event_fails(repo: Repo, capsys: pytest.CaptureFixture[str]) -> None:
    """An event the job was not written for fails rather than checking nothing."""
    event = repo.root.parent / f'{repo.root.name}-event.json'
    event.write_text('{}')
    env = {
        'GITHUB_EVENT_NAME': 'schedule',
        'GITHUB_EVENT_PATH': str(event),
        'GITHUB_OUTPUT': str(repo.root.parent / f'{repo.root.name}-output'),
    }

    assert ci_range.main(env=env, cwd=repo.root) == 1
    assert 'schedule' in capsys.readouterr().err
