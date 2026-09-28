"""Tests that the reformat workflow never pushes formatter fixes to a Renovate branch."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = yaml.safe_load((REPO_ROOT / '.github/workflows/reformat.yml').read_text())
REPOSITORY = 'owner/repo'


def _step(job: str, step_id: str) -> dict:
    """Return one step of a reformat.yml job by its id."""
    return next(step for step in WORKFLOW['jobs'][job]['steps'] if step.get('id') == step_id)


VERIFY = _step('commit-format-changes', 'verify')
GATE = _step('gate', 'compute')
RENOVATE_BOTS = VERIFY['env']['RENOVATE_BOT_ACTORS'].split(',')


def _run(step: dict, cwd: Path, env: dict[str, str]) -> dict[str, str]:
    """Run a step's script under bash with `env` and return what it wrote to GITHUB_OUTPUT."""
    output = cwd / 'github-output'
    output.write_text('')
    base = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    subprocess.run(
        ['bash', '--noprofile', '--norc', '-eo', 'pipefail', '-c', step['run']],
        cwd=cwd,
        check=True,
        env={**base, 'GITHUB_OUTPUT': str(output), 'GITHUB_REPOSITORY': REPOSITORY, **env},
    )
    return dict(line.split('=', 1) for line in output.read_text().splitlines())


@pytest.fixture
def head(tmp_path: Path) -> str:
    """Create a repository whose head commit is an ordinary change, and return its SHA."""
    identity = ['-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid']
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    for arguments in (['init', '--quiet'], ['commit', '--quiet', '--allow-empty', '-m', 'bump']):
        subprocess.run(['git', *identity, *arguments], cwd=tmp_path, check=True, env=env)
    return subprocess.run(
        ['git', 'rev-parse', 'HEAD'],
        cwd=tmp_path,
        check=True,
        env=env,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _verify(cwd: Path, head_sha: str, author: str) -> str:
    """Run the commit job's verify step for a same-repository pull request by `author`."""
    return _run(
        VERIFY,
        cwd,
        {
            'INPUTS_CALLER_EVENT_NAME': 'pull_request',
            'GITHUB_EVENT_PULL_REQUEST_HEAD_REPO_FULL_NAME': REPOSITORY,
            'GITHUB_EVENT_PULL_REQUEST_HEAD_SHA': head_sha,
            'INPUTS_CALLER_PR_AUTHOR': author,
            'INPUTS_SUPER_LINTER_COMMIT_MESSAGE': 'Apply super-linter fixes',
            'RENOVATE_BOT_ACTORS': VERIFY['env']['RENOVATE_BOT_ACTORS'],
        },
    )['skip_commit']


@pytest.mark.parametrize('author', RENOVATE_BOTS)
def test_renovate_pull_request_skips_the_commit(tmp_path: Path, head: str, author: str) -> None:
    """Both the hosted and the self-hosted Renovate bot get no formatter commit."""
    assert _verify(tmp_path, head, author) == 'true'


@pytest.mark.parametrize('author', ['octocat', 'renovate', 'plume-works-renovate'])
def test_other_authors_still_get_the_commit(tmp_path: Path, head: str, author: str) -> None:
    """A person, even one whose login resembles a bot's, keeps the formatter commit."""
    assert _verify(tmp_path, head, author) == 'false'


def test_skipped_commit_with_formatting_changes_fails_the_gate(tmp_path: Path) -> None:
    """With the push skipped, changed files hold back downstream checks, so the gate fails."""
    outputs = _run(
        GATE,
        tmp_path,
        {
            'NEEDS_SUPER_LINTER_RESULT': 'success',
            'NEEDS_SUPER_LINTER_OUTPUT_CHANGED': 'true',
            'NEEDS_COMMIT_FORMAT_CHANGES_RESULT': 'success',
        },
    )

    assert outputs['changed'] == 'true'
    assert outputs['run_downstream'] == 'false'
