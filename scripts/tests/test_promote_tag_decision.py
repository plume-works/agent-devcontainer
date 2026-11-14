"""These tests make sure that the promote action moves a tag only when it is not on a newer commit."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / '.github/actions/docker/promote/tag-decision.sh'


def _git(repo: Path, *args: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    return subprocess.run(
        ['git', '-C', str(repo), *args], env=env, check=True, text=True, capture_output=True
    ).stdout.strip()


@pytest.fixture
def history(tmp_path: Path) -> tuple[Path, list[str]]:
    """Return a repository with three commits, oldest first."""
    _git(tmp_path, 'init', '-q')
    shas = []
    for n in range(3):
        _git(
            tmp_path,
            '-c',
            'user.name=t',
            '-c',
            'user.email=t@example.invalid',
            'commit',
            '-q',
            '--allow-empty',
            '-m',
            str(n),
        )
        shas.append(_git(tmp_path, 'rev-parse', 'HEAD'))
    return tmp_path, shas


def _decide(repo: Path, sha: str, current: str) -> str:
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env['GITHUB_SHA'] = sha
    return subprocess.run(
        [str(SCRIPT), current], cwd=repo, env=env, check=True, text=True, capture_output=True
    ).stdout.strip()


def test_a_tag_on_a_descendant_commit_stays(history):
    repo, shas = history
    assert _decide(repo, shas[1], shas[2]) == 'keep'


@pytest.mark.parametrize(
    'current',
    [lambda shas: shas[0], lambda shas: shas[1], lambda shas: 'f' * 40, lambda shas: ''],
    ids=['ancestor', 'same-commit', 'unknown-commit', 'no-label'],
)
def test_any_other_tag_moves_to_the_tested_image(history, current):
    repo, shas = history
    assert _decide(repo, shas[1], current(shas)) == 'move'
