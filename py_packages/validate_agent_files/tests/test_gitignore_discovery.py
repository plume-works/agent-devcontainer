#!/usr/bin/env python3

"""Tests for gitignore-aware file discovery in the walk-based loaders."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from validate_agent_files.loaders import (
    DEFAULT_EXCLUDED_DIRS,
    find_agent_files,
    find_prompt_files,
    find_skill_files,
)

SKILL_BODY = '---\nname: sample-skill\ndescription: An invented sample skill.\n---\n# Sample\n'
AGENT_BODY = '---\nname: Sample\ndescription: An invented sample agent.\n---\n# Sample\n'
PROMPT_BODY = '---\nagent: sample\n---\n# Sample\n'


def _git(repo: Path, *args: str) -> None:
    """Run a git command in ``repo`` with a fixed, repo-local identity."""
    subprocess.run(
        ['git', '-C', str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(root: Path) -> None:
    """Initialise an isolated git repository with a repo-local commit identity."""
    _git(root, 'init')
    _git(root, 'config', 'user.email', 'discovery@example.invalid')
    _git(root, 'config', 'user.name', 'Discovery Fixture')


def _write(path: Path, body: str) -> Path:
    """Create ``path`` (and parents) with ``body`` and return it."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)
    return path


@pytest.fixture
def matcher_case(request):
    """Provide a discovery function, a matching filename, and its body per suffix."""
    return request.param


MATCHER_CASES = [
    pytest.param((find_skill_files, 'SKILL.md', SKILL_BODY), id='skill'),
    pytest.param((find_agent_files, 'sample.agent.md', AGENT_BODY), id='agent'),
    pytest.param((find_prompt_files, 'sample.prompt.md', PROMPT_BODY), id='prompt'),
]


@pytest.mark.parametrize('matcher_case', MATCHER_CASES, indirect=True)
def test_repo_prunes_ignored_dir_and_file_but_keeps_tracked(tmp_path: Path, matcher_case) -> None:
    """In a repo, an ignored dir and an ignored sibling file drop; tracked files stay."""
    find_files, filename, body = matcher_case
    repo = tmp_path / 'workspace'
    repo.mkdir()
    _init_repo(repo)
    (repo / '.gitignore').write_text('vendored/\ngenerated-*\n')

    tracked = _write(repo / 'kept' / filename, body)
    _write(repo / 'vendored' / filename, body)
    ignored_sibling = _write(repo / 'kept' / f'generated-{filename}', body)

    found = find_files(str(repo))

    assert str(tracked) in found
    assert str(repo / 'vendored' / filename) not in found
    assert str(ignored_sibling) not in found


@pytest.mark.parametrize('matcher_case', MATCHER_CASES, indirect=True)
def test_repo_prunes_git_directory(tmp_path: Path, matcher_case) -> None:
    """A matching file that happens to live under ``.git/`` is never discovered."""
    find_files, filename, body = matcher_case
    repo = tmp_path / 'workspace'
    repo.mkdir()
    _init_repo(repo)
    _write(repo / '.git' / filename, body)
    tracked = _write(repo / filename, body)

    found = find_files(str(repo))

    assert str(tracked) in found
    assert not any('.git' in Path(match).parts for match in found)


@pytest.mark.parametrize('matcher_case', MATCHER_CASES, indirect=True)
def test_non_repo_uses_excluded_dirs_not_git(tmp_path: Path, matcher_case) -> None:
    """Outside a repo, dir pruning follows ``excluded_dirs``; git rules do not apply."""
    find_files, filename, body = matcher_case
    tree = tmp_path / 'plain'
    tree.mkdir()

    default_excluded = next(name for name in sorted(DEFAULT_EXCLUDED_DIRS) if name != '.git')
    in_default_excluded = _write(tree / default_excluded / filename, body)
    walked = _write(tree / 'ordinary' / filename, body)

    found_default = find_files(str(tree))
    assert str(in_default_excluded) not in found_default
    assert str(walked) in found_default


@pytest.mark.parametrize('matcher_case', MATCHER_CASES, indirect=True)
def test_non_repo_custom_excluded_dirs_override_default(tmp_path: Path, matcher_case) -> None:
    """A custom ``excluded_dirs`` replaces the default set outside a repo."""
    find_files, filename, body = matcher_case
    tree = tmp_path / 'plain'
    tree.mkdir()

    default_excluded = next(name for name in sorted(DEFAULT_EXCLUDED_DIRS) if name != '.git')
    now_walked = _write(tree / default_excluded / filename, body)
    now_pruned = _write(tree / 'skipme' / filename, body)

    found = find_files(str(tree), excluded_dirs={'skipme'})

    assert str(now_walked) in found
    assert str(now_pruned) not in found


@pytest.mark.parametrize('matcher_case', MATCHER_CASES, indirect=True)
def test_non_repo_prunes_git_directory(tmp_path: Path, matcher_case) -> None:
    """``.git/`` is pruned even outside a repo and even when not in ``excluded_dirs``."""
    find_files, filename, body = matcher_case
    tree = tmp_path / 'plain'
    tree.mkdir()
    _write(tree / '.git' / filename, body)
    kept = _write(tree / filename, body)

    found = find_files(str(tree), excluded_dirs=set())

    assert str(kept) in found
    assert not any('.git' in Path(match).parts for match in found)
