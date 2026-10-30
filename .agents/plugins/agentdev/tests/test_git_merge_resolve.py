#!/usr/bin/env python3

"""Behavior tests for the git-merge-resolve skill script."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

from git_fixtures import FIXTURE_ENV, git, outcome
import pytest
from test_update_branch import initialize_repository

SCRIPT_PATH = 'skills/git-merge-resolve/agent-code/git-merge-resolve.py'


def run_script(plugin_root: Path, cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run the merge script in `cwd`."""
    return subprocess.run(
        [str(plugin_root / SCRIPT_PATH), *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, **FIXTURE_ENV},
    )


def keys(completed: subprocess.CompletedProcess[str]) -> dict[str, str]:
    """Return the KEY=value lines of a run."""
    return dict(line.split('=', 1) for line in completed.stdout.splitlines() if '=' in line)


def commit_file(repository: Path, name: str, text: str, message: str) -> None:
    """Write `name` and commit it."""
    (repository / name).write_text(text)
    git(repository, 'add', name)
    git(repository, 'commit', '--quiet', '-m', message)


@pytest.fixture
def repository(plugin_tmp_path: Path) -> Path:
    """Create a repository on fixture-feature with a diverged fixture-topic branch."""
    path = plugin_tmp_path / 'repository'
    initialize_repository(path)
    git(path, 'branch', 'fixture-topic')
    commit_file(path, 'feature.txt', 'feature\n', 'feature change')
    git(path, 'checkout', '--quiet', 'fixture-topic')
    commit_file(path, 'topic.txt', 'topic\n', 'topic change')
    git(path, 'checkout', '--quiet', 'fixture-feature')
    return path


def test_merge_creates_a_merge_commit(plugin_root: Path, repository: Path) -> None:
    """A diverged source is merged with a non-fast-forward commit carrying the message."""
    completed = run_script(plugin_root, repository, '--message', 'Fixture merge', 'fixture-topic')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert keys(completed) | {'RESULT': ''} == {
        'DESTINATION': 'fixture-feature',
        'SOURCE': 'fixture-topic',
        'RESULT': '',
    }
    assert git(repository, 'log', '-1', '--format=%s%n%P').splitlines()[0] == 'Fixture merge'
    assert len(git(repository, 'log', '-1', '--format=%P').split()) == 2


def test_default_message_names_source_and_destination(plugin_root: Path, repository: Path) -> None:
    """Without --message the commit says which ref merged into which branch."""
    completed = run_script(plugin_root, repository, 'fixture-topic')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert git(repository, 'log', '-1', '--format=%s') == (
        'Merge fixture-topic into fixture-feature'
    )


def test_already_merged_source_is_up_to_date(plugin_root: Path, repository: Path) -> None:
    """A source HEAD already contains produces ALREADY_UP_TO_DATE and no commit."""
    head = git(repository, 'rev-parse', 'HEAD')

    completed = run_script(plugin_root, repository, 'HEAD~1')

    assert outcome(completed) == (3, 'RESULT=ALREADY_UP_TO_DATE')
    assert git(repository, 'rev-parse', 'HEAD') == head


def test_conflicts_are_listed(plugin_root: Path, repository: Path) -> None:
    """Both sides changing one file leaves the merge conflicted and names the file."""
    commit_file(repository, 'fixture.txt', 'feature side\n', 'feature edit')
    git(repository, 'checkout', '--quiet', 'fixture-topic')
    commit_file(repository, 'fixture.txt', 'topic side\n', 'topic edit')
    git(repository, 'checkout', '--quiet', 'fixture-feature')

    completed = run_script(plugin_root, repository, 'fixture-topic')

    assert outcome(completed) == (4, 'RESULT=MERGE_CONFLICTS')
    assert completed.stderr.endswith('\nConflicted files:\nfixture.txt\n')


@pytest.mark.parametrize(
    ('arrange', 'arguments', 'message'),
    [
        ('none', [], 'A source ref is required.'),
        ('none', ['--bogus'], 'Unknown option: --bogus'),
        ('none', ['a', 'b'], 'Only one source ref may be supplied.'),
        ('none', ['--message'], 'Missing value for --message'),
        ('none', ['fixture-absent'], 'Source ref does not resolve to a commit: fixture-absent'),
        ('dirty', ['fixture-topic'], 'Working tree is dirty.'),
        ('detached', ['fixture-topic'], 'Detached HEAD cannot receive this merge.'),
    ],
)
def test_preflight_failures(
    plugin_root: Path, repository: Path, arrange: str, arguments: list[str], message: str
) -> None:
    """Each preflight failure stops with PREFLIGHT_ERROR before merging."""
    if arrange == 'dirty':
        (repository / 'fixture.txt').write_text('uncommitted\n')
    elif arrange == 'detached':
        git(repository, 'checkout', '--quiet', '--detach')

    completed = run_script(plugin_root, repository, *arguments)

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert f'ERROR: {message}' in completed.stderr


def test_merge_in_progress_is_refused(plugin_root: Path, repository: Path) -> None:
    """A pending MERGE_HEAD blocks a second merge."""
    commit_file(repository, 'fixture.txt', 'feature side\n', 'feature edit')
    git(repository, 'checkout', '--quiet', 'fixture-topic')
    commit_file(repository, 'fixture.txt', 'topic side\n', 'topic edit')
    git(repository, 'checkout', '--quiet', 'fixture-feature')
    subprocess.run(['git', 'merge', 'fixture-topic'], cwd=repository, capture_output=True)

    completed = run_script(plugin_root, repository, 'fixture-topic')

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert 'ERROR: A merge is already in progress.' in completed.stderr


def test_help_prints_usage(plugin_root: Path, repository: Path) -> None:
    """--help prints the usage on stdout and succeeds."""
    completed = run_script(plugin_root, repository, '--help')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert completed.stdout.startswith('Merge a local Git ref into the current branch')
