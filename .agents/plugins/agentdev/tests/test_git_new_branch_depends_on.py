#!/usr/bin/env python3

"""Behavior tests for git-new-branch --depends-on."""

from __future__ import annotations

from pathlib import Path

from git_fixtures import git, outcome, stub_gh
import pytest
from test_git_new_branch import commit_file, Fixture, run_script


def publish_branch(fixture: Fixture, branch: str, name: str) -> str:
    """Push a branch with one commit off the default branch; return its head."""
    git(fixture.publisher, 'switch', '--quiet', '-c', branch, f'origin/{fixture.default_branch}')
    commit_file(fixture.publisher, name, f'{branch}\n')
    git(fixture.publisher, 'push', 'origin', branch)
    return git(fixture.publisher, 'rev-parse', 'HEAD')


def pull_requests(directory: Path, states: dict[int, tuple[str, str]]) -> Path:
    """Install a gh stub answering `pr view <n>` with each pull request's state and head."""
    cases = '\n'.join(
        f'  {number}) echo "{state} {"true" if branch.startswith("fork:") else "false"} '
        f'{branch.removeprefix("fork:")}" ;;'
        for number, (state, branch) in states.items()
    )
    return stub_gh(directory, f'case "$3" in\n{cases}\n  *) exit 1 ;;\nesac')


def trailers(repository: Path, ref: str) -> list[str]:
    """Return the Depends-on trailer values of commits reachable from `ref`, oldest first."""
    output = git(
        repository, 'log', '--reverse', '--format=%(trailers:key=Depends-on,valueonly)', ref
    )
    return [line for line in output.splitlines() if line]


@pytest.fixture
def fixture(plugin_tmp_path: Path) -> Fixture:
    """Build a remote, a publisher, and a working clone."""
    return Fixture(plugin_tmp_path)


def test_one_open_predecessor_starts_at_its_head_with_a_trailer(
    plugin_root: Path, fixture: Fixture, plugin_tmp_path: Path
) -> None:
    head = publish_branch(fixture, 'feature-p', 'p.txt')
    stub = pull_requests(plugin_tmp_path / 'gh', {591: ('OPEN', 'feature-p')})
    completed, keys = run_script(
        plugin_root, fixture.work, 'next', '--depends-on', '591', path_prefix=stub
    )
    assert outcome(completed) == (0, 'RESULT=SUCCESS'), completed.stderr
    assert keys['BASE'] == 'origin/feature-p'
    assert keys['DEPENDS_ON'] == '591'
    assert git(fixture.work, 'rev-parse', 'HEAD~1') == head
    assert git(fixture.work, 'diff', '--name-only', 'HEAD~1', 'HEAD') == ''
    assert trailers(fixture.work, 'HEAD') == ['#591']
    assert git(fixture.work, 'rev-parse', 'origin/next') == git(fixture.work, 'rev-parse', 'HEAD')
    assert git(fixture.work, 'rev-parse', '--abbrev-ref', '@{u}') == 'origin/next'


def test_two_predecessors_contain_both_heads_and_a_trailer_each(
    plugin_root: Path, fixture: Fixture, plugin_tmp_path: Path
) -> None:
    first = publish_branch(fixture, 'feature-a', 'a.txt')
    second = publish_branch(fixture, 'feature-b', 'b.txt')
    stub = pull_requests(
        plugin_tmp_path / 'gh', {3: ('OPEN', 'feature-a'), 5: ('OPEN', 'feature-b')}
    )
    completed, _ = run_script(
        plugin_root,
        fixture.work,
        'next',
        '--depends-on',
        '3',
        '--depends-on',
        '#5',
        path_prefix=stub,
    )
    assert outcome(completed) == (0, 'RESULT=SUCCESS'), completed.stderr
    for head in (first, second):
        git(fixture.work, 'merge-base', '--is-ancestor', head, 'HEAD')
    assert trailers(fixture.work, 'HEAD') == ['#3', '#5']
    assert git(fixture.work, 'rev-parse', 'origin/next') == git(fixture.work, 'rev-parse', 'HEAD')


@pytest.mark.parametrize('state', ['MERGED', 'CLOSED'])
def test_a_predecessor_that_is_not_open_stops_before_anything_is_created(
    plugin_root: Path, fixture: Fixture, plugin_tmp_path: Path, state: str
) -> None:
    publish_branch(fixture, 'feature-a', 'a.txt')
    publish_branch(fixture, 'feature-b', 'b.txt')
    stub = pull_requests(
        plugin_tmp_path / 'gh', {3: ('OPEN', 'feature-a'), 5: (state, 'feature-b')}
    )
    before = git(fixture.work, 'rev-parse', 'HEAD')
    completed, _ = run_script(
        plugin_root, fixture.work, 'next', '--depends-on', '3', '--depends-on', '5',
        path_prefix=stub,
    )  # fmt: skip
    assert outcome(completed) == (9, 'RESULT=DEPENDENCY_NOT_OPEN')
    assert git(fixture.work, 'branch', '--list', 'next') == ''
    assert git(fixture.work, 'ls-remote', '--heads', 'origin', 'next') == ''
    assert git(fixture.work, 'rev-parse', 'HEAD') == before


def test_an_unreadable_predecessor_is_gh_failed(
    plugin_root: Path, fixture: Fixture, plugin_tmp_path: Path
) -> None:
    stub = pull_requests(plugin_tmp_path / 'gh', {})
    completed, _ = run_script(
        plugin_root, fixture.work, 'next', '--depends-on', '7', path_prefix=stub
    )
    assert outcome(completed) == (10, 'RESULT=GH_FAILED')
    assert git(fixture.work, 'branch', '--list', 'next') == ''


def test_depends_on_with_base_is_a_preflight_error(plugin_root: Path, fixture: Fixture) -> None:
    completed, _ = run_script(
        plugin_root, fixture.work, 'next', '--depends-on', '7', '--base', 'main'
    )
    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')


def test_conflicting_heads_keep_the_branch_local_and_unpushed(
    plugin_root: Path, fixture: Fixture, plugin_tmp_path: Path
) -> None:
    publish_branch(fixture, 'feature-a', 'same.txt')
    publish_branch(fixture, 'feature-b', 'same.txt')
    stub = pull_requests(
        plugin_tmp_path / 'gh', {3: ('OPEN', 'feature-a'), 5: ('OPEN', 'feature-b')}
    )
    completed, _ = run_script(
        plugin_root, fixture.work, 'next', '--depends-on', '3', '--depends-on', '5',
        path_prefix=stub,
    )  # fmt: skip
    assert outcome(completed) == (11, 'RESULT=MERGE_FAILED')
    assert git(fixture.work, 'branch', '--show-current') == 'next'
    assert trailers(fixture.work, 'HEAD') == ['#3', '#5']
    assert git(fixture.work, 'ls-remote', '--heads', 'origin', 'next') == ''


def test_carried_changes_stay_uncommitted(
    plugin_root: Path, fixture: Fixture, plugin_tmp_path: Path
) -> None:
    publish_branch(fixture, 'feature-p', 'p.txt')
    stub = pull_requests(plugin_tmp_path / 'gh', {591: ('OPEN', 'feature-p')})
    (fixture.work / 'draft.txt').write_text('draft\n')
    git(fixture.work, 'add', 'draft.txt')
    completed, _ = run_script(
        plugin_root, fixture.work, 'next', '--depends-on', '591', path_prefix=stub
    )
    assert outcome(completed) == (0, 'RESULT=SUCCESS'), completed.stderr
    assert git(fixture.work, 'diff', '--cached', '--name-only') == 'draft.txt'
    assert git(fixture.work, 'show', '--name-only', '--format=', 'HEAD') == ''


def test_worktree_mode_records_the_dependency(
    plugin_root: Path, fixture: Fixture, plugin_tmp_path: Path
) -> None:
    head = publish_branch(fixture, 'feature-p', 'p.txt')
    stub = pull_requests(plugin_tmp_path / 'gh', {591: ('OPEN', 'feature-p')})
    root = plugin_tmp_path / 'trees'
    completed, keys = run_script(
        plugin_root, fixture.work, 'next', '--depends-on', '591',
        '--worktree-root', str(root), path_prefix=stub,
    )  # fmt: skip
    assert outcome(completed) == (0, 'RESULT=SUCCESS'), completed.stderr
    worktree = Path(keys['WORKTREE'])
    assert git(worktree, 'rev-parse', 'HEAD~1') == head
    assert trailers(worktree, 'HEAD') == ['#591']
    assert git(fixture.work, 'branch', '--show-current') == fixture.default_branch


def test_a_predecessor_in_a_fork_is_a_preflight_error(
    plugin_root: Path, fixture: Fixture, plugin_tmp_path: Path
) -> None:
    publish_branch(fixture, 'feature-p', 'p.txt')
    stub = pull_requests(plugin_tmp_path / 'gh', {591: ('OPEN', 'fork:feature-p')})
    completed, _ = run_script(
        plugin_root, fixture.work, 'next', '--depends-on', '591', path_prefix=stub
    )
    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert git(fixture.work, 'branch', '--list', 'next') == ''


def test_changes_with_two_predecessors_stop_before_anything_is_created(
    plugin_root: Path, fixture: Fixture, plugin_tmp_path: Path
) -> None:
    publish_branch(fixture, 'feature-a', 'a.txt')
    publish_branch(fixture, 'feature-b', 'b.txt')
    stub = pull_requests(
        plugin_tmp_path / 'gh', {3: ('OPEN', 'feature-a'), 5: ('OPEN', 'feature-b')}
    )
    (fixture.work / 'draft.txt').write_text('draft\n')
    git(fixture.work, 'add', 'draft.txt')
    before = git(fixture.work, 'rev-parse', 'HEAD')
    completed, _ = run_script(
        plugin_root, fixture.work, 'next', '--depends-on', '3', '--depends-on', '5',
        path_prefix=stub,
    )  # fmt: skip
    assert outcome(completed) == (4, 'RESULT=CARRY_CONFLICT')
    assert git(fixture.work, 'branch', '--list', 'next') == ''
    assert git(fixture.work, 'rev-parse', 'HEAD') == before
    assert git(fixture.work, 'diff', '--cached', '--name-only') == 'draft.txt'
