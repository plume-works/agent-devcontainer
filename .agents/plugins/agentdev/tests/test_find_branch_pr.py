#!/usr/bin/env python3

"""Behavior tests for the pr-open find-branch-pr script."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from git_fixtures import FIXTURE_ENV, git, outcome
import pytest
from test_update_branch import initialize_repository

SCRIPT_PATH = 'skills/pr-open/agent-code/find-branch-pr.py'
TOOLS = ('git', 'python3')

GH_STUB = """
import json
import os
import sys

fixture = json.loads(open(os.environ['GH_STUB_FIXTURE']).read())
arguments = sys.argv[1:]
open(os.environ['GH_STUB_FIXTURE'] + '.args', 'a').write(json.dumps(arguments) + '\\n')
if arguments[:2] == ['auth', 'status']:
    sys.exit(fixture.get('auth', 0))
if arguments[:2] == ['pr', 'list']:
    if fixture.get('list_fails'):
        print('HTTP 502: bad gateway', file=sys.stderr)
        sys.exit(1)
    for pr in fixture['prs']:
        print('PR_RECORD')
        for key, value in pr.items():
            print(f'{key}={value}')
    sys.exit(0)
sys.exit(1)
"""


def pull_request(number: int, head: str = 'fixture-feature') -> dict[str, Any]:
    """Build the key lines the PR template renders for one pull request."""
    return {
        'PR_NUMBER': number,
        'PR_URL': f'https://github.com/octo/repo/pull/{number}',
        'PR_STATE': 'OPEN',
        'PR_IS_DRAFT': 'false',
        'PR_BASE': 'main',
        'PR_HEAD': head,
        'PR_TITLE': f'Fixture change {number}',
    }


@pytest.fixture
def repository(plugin_tmp_path: Path) -> Path:
    """Create a repository on fixture-feature."""
    path = plugin_tmp_path / 'repository'
    initialize_repository(path)
    return path


def run_script(
    plugin_root: Path,
    repository: Path,
    fixture: dict[str, Any] | None,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    """Run the script with PATH limited to the tools it needs and, unless None, a gh stub."""
    stubs = repository.parent / 'stub-bin'
    stubs.mkdir(exist_ok=True)
    for tool in TOOLS:
        if not (stubs / tool).exists():
            found = shutil.which(tool)
            assert found is not None
            (stubs / tool).symlink_to(found)
    environment = {**os.environ, **FIXTURE_ENV, 'PATH': str(stubs)}
    if fixture is not None:
        fixture_file = repository.parent / 'gh-fixture.json'
        fixture_file.write_text(json.dumps(fixture))
        gh = stubs / 'gh'
        gh.write_text(f'#!{sys.executable}\n{GH_STUB}')
        gh.chmod(0o755)
        environment['GH_STUB_FIXTURE'] = str(fixture_file)
    return subprocess.run(
        [str(plugin_root / SCRIPT_PATH), *arguments],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def test_single_match_prints_the_pull_request(plugin_root: Path, repository: Path) -> None:
    """One open pull request for the head prints its keys without the record marker."""
    completed = run_script(plugin_root, repository, {'prs': [pull_request(7)]})

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert completed.stdout.splitlines()[:-1] == [
        'HEAD_BRANCH=fixture-feature',
        'PR_FOUND=true',
        *(f'{key}={value}' for key, value in pull_request(7).items()),
    ]
    arguments = json.loads(
        (repository.parent / 'gh-fixture.json.args').read_text().splitlines()[-1]
    )
    assert arguments[arguments.index('--head') + 1] == 'fixture-feature'
    assert arguments[arguments.index('--state') + 1] == 'open'


def test_no_match_needs_a_new_pull_request(plugin_root: Path, repository: Path) -> None:
    """No pull request for the head reports NO_PR_FOUND with PR_FOUND=false."""
    completed = run_script(plugin_root, repository, {'prs': []}, '--state', 'all')

    assert outcome(completed) == (3, 'RESULT=NO_PR_FOUND')
    assert 'PR_FOUND=false' in completed.stdout.splitlines()
    assert 'No all pull request found with head branch fixture-feature' in completed.stderr


def test_several_matches_refuse_to_guess(plugin_root: Path, repository: Path) -> None:
    """Two pull requests for one head report MULTIPLE_PRS and list them on stderr."""
    completed = run_script(plugin_root, repository, {'prs': [pull_request(7), pull_request(8)]})

    assert outcome(completed) == (4, 'RESULT=MULTIPLE_PRS')
    assert "Found 2 pull requests with head branch 'fixture-feature'" in completed.stderr
    assert 'PR_NUMBER=8' in completed.stderr


def test_upstream_with_another_name_is_the_head(plugin_root: Path, repository: Path) -> None:
    """A local branch tracking a differently named ref looks up that ref's name."""
    remote = repository.parent / 'remote.git'
    git(repository.parent, 'init', '--quiet', '--bare', str(remote))
    git(repository, 'remote', 'add', 'fork', str(remote))
    git(repository, 'push', '--quiet', 'fork', 'fixture-feature:feature')
    git(repository, 'checkout', '--quiet', '-b', 'review-31', '--track', 'fork/feature')

    completed = run_script(plugin_root, repository, {'prs': [pull_request(9, 'feature')]})

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert completed.stdout.splitlines()[0] == 'HEAD_BRANCH=feature'


def test_default_branch_is_protected(plugin_root: Path, repository: Path) -> None:
    """Main is never a pull request head."""
    git(repository, 'checkout', '--quiet', '-b', 'main')

    completed = run_script(plugin_root, repository, {'prs': []})

    assert outcome(completed) == (5, 'RESULT=PROTECTED_BRANCH')


def test_tracking_a_default_branch_is_protected(plugin_root: Path, repository: Path) -> None:
    """A feature branch whose upstream is a remote main is refused too."""
    remote = repository.parent / 'remote.git'
    git(repository.parent, 'init', '--quiet', '--bare', str(remote))
    git(repository, 'remote', 'add', 'origin', str(remote))
    git(repository, 'push', '--quiet', 'origin', 'fixture-feature:main')
    git(repository, 'branch', '--quiet', '--set-upstream-to', 'origin/main')

    completed = run_script(plugin_root, repository, {'prs': []})

    assert outcome(completed) == (5, 'RESULT=PROTECTED_BRANCH')
    assert 'tracks origin/main' in completed.stderr


@pytest.mark.parametrize(
    ('fixture', 'message'),
    [
        (None, 'GitHub CLI (gh) is not installed.'),
        ({'prs': [], 'auth': 1}, 'GitHub CLI is not authenticated.'),
        ({'prs': [], 'list_fails': True}, 'gh pr list failed for head branch fixture-feature.'),
    ],
)
def test_unusable_gh_reports_gh_unavailable_after_the_head(
    plugin_root: Path, repository: Path, fixture: dict[str, Any] | None, message: str
) -> None:
    """Every gh failure is GH_UNAVAILABLE, with HEAD_BRANCH already printed for a fallback."""
    completed = run_script(plugin_root, repository, fixture)

    assert outcome(completed) == (6, 'RESULT=GH_UNAVAILABLE')
    assert completed.stdout.splitlines()[0] == 'HEAD_BRANCH=fixture-feature'
    assert f'ERROR: {message}' in completed.stderr


@pytest.mark.parametrize(
    ('arguments', 'detach', 'message'),
    [
        (['--state', 'closed'], False, 'Unsupported --state value: closed (use open or all)'),
        (['--bogus'], False, 'Unknown argument: --bogus'),
        (['--branch'], False, 'Missing value for --branch'),
        ([], True, 'Detached HEAD'),
    ],
)
def test_preflight_errors(
    plugin_root: Path, repository: Path, arguments: list[str], detach: bool, message: str
) -> None:
    """Usage errors and a detached HEAD stop before gh is consulted."""
    if detach:
        git(repository, 'checkout', '--quiet', '--detach')

    completed = run_script(plugin_root, repository, {'prs': []}, *arguments)

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert f'ERROR: {message}' in completed.stderr
