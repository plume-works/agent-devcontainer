#!/usr/bin/env python3

"""Behavior tests for the git-new-branch skill script."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest

FIXTURE_ENV = {
    'GIT_AUTHOR_NAME': 'Fixture Author',
    'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
    'GIT_COMMITTER_NAME': 'Fixture Author',
    'GIT_COMMITTER_EMAIL': 'fixture@example.invalid',
}


def git(cwd: Path, *args: str) -> str:
    """Run a fixture git command and return its stripped stdout."""
    completed = subprocess.run(
        ['git', *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **FIXTURE_ENV},
    )
    return completed.stdout.strip()


def commit_file(repository: Path, name: str, content: str) -> None:
    """Write `name` in `repository` and commit it."""
    (repository / name).write_text(content)
    git(repository, 'add', name)
    git(repository, 'commit', '-m', f'write {name}')


class Fixture:
    """A bare remote, a publisher clone that advances it, and a working clone."""

    def __init__(self, root: Path, default_branch: str = 'main') -> None:
        self.root = root
        self.default_branch = default_branch
        seed = root / 'seed'
        seed.mkdir()
        git(seed, 'init', f'--initial-branch={default_branch}')
        commit_file(seed, 'fixture.txt', 'one\ntwo\nthree\nfour\nfive\n')
        commit_file(seed, 'other.txt', 'other\n')
        self.remote = root / 'remote.git'
        git(root, 'clone', '--bare', str(seed), str(self.remote))
        self.work = root / 'work'
        git(root, 'clone', str(self.remote), str(self.work))
        self.publisher = root / 'publisher'
        git(root, 'clone', str(self.remote), str(self.publisher))

    def advance_remote(self, name: str, content: str) -> str:
        """Commit on the remote default branch behind the working clone's back."""
        commit_file(self.publisher, name, content)
        git(self.publisher, 'push', 'origin', self.default_branch)
        return git(self.publisher, 'rev-parse', 'HEAD')


def run_script(
    plugin_root: Path,
    cwd: Path,
    *args: str,
    path_prefix: Path | None = None,
) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    """Run git-new-branch.sh and parse its key=value stdout."""
    script = plugin_root / 'skills/git-new-branch/scripts/git-new-branch.sh'
    env = {**os.environ, **FIXTURE_ENV}
    if path_prefix is not None:
        env['PATH'] = f'{path_prefix}{os.pathsep}{env["PATH"]}'
    completed = subprocess.run(
        [str(script), *args],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    keys = dict(line.split('=', 1) for line in completed.stdout.splitlines() if '=' in line)
    return completed, keys


def outcome(completed: subprocess.CompletedProcess[str]) -> tuple[int, str]:
    """Return the (exit code, last stdout line) contract pair."""
    return completed.returncode, completed.stdout.splitlines()[-1]


@pytest.fixture
def fixture(plugin_tmp_path: Path) -> Fixture:
    """Provide a remote whose main has moved ahead of the working clone."""
    return Fixture(plugin_tmp_path)


def test_branch_starts_at_fetched_base_and_tracks_its_own_upstream(
    plugin_root: Path,
    fixture: Fixture,
) -> None:
    """The branch sits at the just-fetched base and is pushed with its own upstream."""
    # Arrange
    fetched_sha = fixture.advance_remote('late.txt', 'late\n')

    # Act
    completed, keys = run_script(plugin_root, fixture.work, 'fixture-topic')

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert (keys['BRANCH'], keys['BASE'], keys['BASE_SHA']) == (
        'fixture-topic',
        'origin/main',
        fetched_sha,
    )
    assert git(fixture.work, 'rev-parse', '--abbrev-ref', 'HEAD') == 'fixture-topic'
    assert git(fixture.work, 'rev-parse', 'HEAD') == fetched_sha
    assert git(fixture.work, 'rev-parse', '--abbrev-ref', '@{u}') == 'origin/fixture-topic'
    assert git(fixture.remote, 'rev-parse', 'refs/heads/fixture-topic') == fetched_sha
    assert 'LOCAL_COMMITS' not in keys


def test_local_main_commits_move_to_the_new_branch(plugin_root: Path, fixture: Fixture) -> None:
    """Commits on main the base lacks move to the new branch; main is reset to the base."""
    # Arrange
    fetched_sha = fixture.advance_remote('late.txt', 'late\n')
    commit_file(fixture.work, 'local-one.txt', 'one\n')
    commit_file(fixture.work, 'local-two.txt', 'two\n')
    main_sha = git(fixture.work, 'rev-parse', 'main')

    # Act
    completed, keys = run_script(plugin_root, fixture.work, 'fixture-topic')

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert (keys['LOCAL_COMMITS'], keys['BASE_SHA']) == ('2', fetched_sha)
    assert git(fixture.work, 'rev-parse', 'fixture-topic') == main_sha
    assert git(fixture.work, 'rev-parse', 'main') == fetched_sha
    assert git(fixture.work, 'rev-parse', '--abbrev-ref', '@{u}') == 'origin/fixture-topic'
    assert git(fixture.remote, 'rev-parse', 'refs/heads/fixture-topic') == main_sha


def test_local_main_commits_move_to_the_new_worktree_branch(
    plugin_root: Path,
    fixture: Fixture,
) -> None:
    """Worktree mode starts the branch at main and leaves the checked-out main unmoved."""
    # Arrange
    fixture.advance_remote('late.txt', 'late\n')
    commit_file(fixture.work, 'local-one.txt', 'one\n')
    main_sha = git(fixture.work, 'rev-parse', 'main')

    # Act
    completed, keys = run_script(
        plugin_root, fixture.work, 'fixture-topic', '--worktree-root', str(fixture.root / 'trees')
    )

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert keys['LOCAL_COMMITS'] == '1'
    assert git(Path(keys['WORKTREE']), 'rev-parse', 'HEAD') == main_sha
    assert git(fixture.work, 'rev-parse', '--abbrev-ref', 'HEAD') == 'main'
    assert git(fixture.work, 'rev-parse', 'main') == main_sha


def test_update_branch_merges_the_base_into_moved_commits(
    plugin_root: Path,
    fixture: Fixture,
) -> None:
    """After LOCAL_COMMITS, update-branch brings the base into the branch holding them."""
    # Arrange
    fetched_sha = fixture.advance_remote('late.txt', 'late\n')
    commit_file(fixture.work, 'local-one.txt', 'one\n')
    main_sha = git(fixture.work, 'rev-parse', 'main')
    _, keys = run_script(plugin_root, fixture.work, 'fixture-topic')
    assert keys['LOCAL_COMMITS'] == '1'
    update_branch = plugin_root / 'skills/update-branch/scripts/update-branch.sh'

    # Act
    merged = subprocess.run(
        [str(update_branch)],
        cwd=fixture.work,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, **FIXTURE_ENV},
    )

    # Assert
    assert outcome(merged) == (0, 'RESULT=SUCCESS')
    for ancestor in (main_sha, fetched_sha):
        git(fixture.work, 'merge-base', '--is-ancestor', ancestor, 'fixture-topic')
    assert git(fixture.work, 'rev-parse', 'main') == fetched_sha


def test_missing_base_falls_back_to_remote_head(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """Without origin/main the branch starts where refs/remotes/origin/HEAD points."""
    # Arrange
    fixture = Fixture(plugin_tmp_path, default_branch='fixture-trunk')
    fetched_sha = fixture.advance_remote('late.txt', 'late\n')

    # Act
    completed, keys = run_script(plugin_root, fixture.work, 'fixture-topic')

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert (keys['BASE'], keys['BASE_SHA']) == ('origin/fixture-trunk', fetched_sha)
    assert git(fixture.work, 'rev-parse', 'HEAD') == fetched_sha


def stub_gh(directory: Path, script_body: str) -> Path:
    """Install a fake `gh` whose arguments are recorded next to it."""
    directory.mkdir()
    gh = directory / 'gh'
    gh.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{directory}/gh-args"\n{script_body}\n')
    gh.chmod(0o755)
    return directory


def test_unset_remote_head_asks_gh_for_the_default_branch(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """Without origin/main or origin/HEAD, gh names the default branch for the remote URL."""
    # Arrange
    fixture = Fixture(plugin_tmp_path, default_branch='fixture-trunk')
    git(fixture.work, 'remote', 'set-head', 'origin', '--delete')
    fetched_sha = fixture.advance_remote('late.txt', 'late\n')
    stub_dir = stub_gh(plugin_tmp_path / 'stub-bin', 'echo fixture-trunk')

    # Act
    completed, keys = run_script(plugin_root, fixture.work, 'fixture-topic', path_prefix=stub_dir)

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert (keys['BASE'], keys['BASE_SHA']) == ('origin/fixture-trunk', fetched_sha)
    assert str(fixture.remote) in (stub_dir / 'gh-args').read_text().splitlines()


def test_unset_remote_head_without_gh_answer_is_a_preflight_error(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """When gh cannot report the default branch, nothing is created."""
    # Arrange
    fixture = Fixture(plugin_tmp_path, default_branch='fixture-trunk')
    git(fixture.work, 'remote', 'set-head', 'origin', '--delete')
    stub_dir = stub_gh(plugin_tmp_path / 'stub-bin', 'exit 1')

    # Act
    completed, _ = run_script(plugin_root, fixture.work, 'fixture-topic', path_prefix=stub_dir)

    # Assert
    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert 'gh could not report the default branch' in completed.stderr
    assert git(fixture.work, 'branch', '--list', 'fixture-topic') == ''


def test_existing_local_branch_is_refused(plugin_root: Path, fixture: Fixture) -> None:
    """A local branch with the requested name is never reset or reused."""
    # Arrange
    git(fixture.work, 'branch', 'fixture-topic', 'HEAD~1')
    before = git(fixture.work, 'rev-parse', 'fixture-topic')

    # Act
    completed, _ = run_script(plugin_root, fixture.work, 'fixture-topic')

    # Assert
    assert outcome(completed) == (3, 'RESULT=BRANCH_EXISTS')
    assert git(fixture.work, 'rev-parse', 'fixture-topic') == before
    assert git(fixture.work, 'rev-parse', '--abbrev-ref', 'HEAD') == 'main'


def test_existing_remote_only_branch_is_refused(plugin_root: Path, fixture: Fixture) -> None:
    """A name that exists only on the remote creates nothing locally."""
    # Arrange
    git(fixture.publisher, 'push', 'origin', 'HEAD:refs/heads/fixture-topic')

    # Act
    completed, _ = run_script(plugin_root, fixture.work, 'fixture-topic')

    # Assert
    assert outcome(completed) == (3, 'RESULT=BRANCH_EXISTS')
    assert git(fixture.work, 'branch', '--list', 'fixture-topic') == ''


def test_uncommitted_and_untracked_changes_carry_over(
    plugin_root: Path,
    fixture: Fixture,
) -> None:
    """Changes to paths the base did not touch arrive on the new branch intact."""
    # Arrange
    fixture.advance_remote('late.txt', 'late\n')
    (fixture.work / 'fixture.txt').write_text('edited\n')
    (fixture.work / 'untracked.txt').write_text('new\n')

    # Act
    completed, _ = run_script(plugin_root, fixture.work, 'fixture-topic')

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert git(fixture.work, 'rev-parse', '--abbrev-ref', 'HEAD') == 'fixture-topic'
    assert (fixture.work / 'fixture.txt').read_text() == 'edited\n'
    assert (fixture.work / 'untracked.txt').read_text() == 'new\n'
    assert (fixture.work / 'late.txt').read_text() == 'late\n'


def test_changes_to_paths_the_base_moved_are_left_untouched(
    plugin_root: Path,
    fixture: Fixture,
) -> None:
    """CARRY_CONFLICT changes nothing: same branch, same HEAD, same edits, no new branch."""
    # Arrange
    fixture.advance_remote('fixture.txt', 'ONE\ntwo\nthree\nfour\nfive\n')
    head_before = git(fixture.work, 'rev-parse', 'HEAD')
    (fixture.work / 'fixture.txt').write_text('one\ntwo\nthree\nfour\nFIVE\n')

    # Act
    completed, _ = run_script(plugin_root, fixture.work, 'fixture-topic')

    # Assert
    assert outcome(completed) == (4, 'RESULT=CARRY_CONFLICT')
    assert 'fixture.txt' in completed.stderr
    assert git(fixture.work, 'rev-parse', '--abbrev-ref', 'HEAD') == 'main'
    assert git(fixture.work, 'rev-parse', 'HEAD') == head_before
    assert (fixture.work / 'fixture.txt').read_text() == 'one\ntwo\nthree\nfour\nFIVE\n'
    assert git(fixture.work, 'branch', '--list', 'fixture-topic') == ''
    assert git(fixture.work, 'stash', 'list') == ''


def test_stash_mode_carries_changes_the_base_moved(plugin_root: Path, fixture: Fixture) -> None:
    """--stash stashes, branches, pushes, and pops cleanly, leaving no stash entry."""
    # Arrange
    fetched_sha = fixture.advance_remote('fixture.txt', 'ONE\ntwo\nthree\nfour\nfive\n')
    (fixture.work / 'fixture.txt').write_text('one\ntwo\nthree\nfour\nFIVE\n')
    (fixture.work / 'untracked.txt').write_text('new\n')

    # Act
    completed, keys = run_script(plugin_root, fixture.work, 'fixture-topic', '--stash')

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert 'STASH_REF' not in keys
    assert git(fixture.work, 'rev-parse', 'HEAD') == fetched_sha
    assert (fixture.work / 'fixture.txt').read_text() == 'ONE\ntwo\nthree\nfour\nFIVE\n'
    assert (fixture.work / 'untracked.txt').read_text() == 'new\n'
    assert git(fixture.work, 'stash', 'list') == ''
    assert git(fixture.work, 'rev-parse', '--abbrev-ref', '@{u}') == 'origin/fixture-topic'


def test_stash_mode_keeps_stash_entry_when_pop_conflicts(
    plugin_root: Path,
    fixture: Fixture,
) -> None:
    """A conflicted pop reports STASH_CONFLICTS and keeps the stash entry to drop later."""
    # Arrange
    fixture.advance_remote('fixture.txt', 'base edit\ntwo\nthree\nfour\nfive\n')
    (fixture.work / 'fixture.txt').write_text('local edit\ntwo\nthree\nfour\nfive\n')

    # Act
    completed, keys = run_script(plugin_root, fixture.work, 'fixture-topic', '--stash')

    # Assert
    assert outcome(completed) == (7, 'RESULT=STASH_CONFLICTS')
    assert keys['STASH_REF'] == 'stash@{0}'
    assert git(fixture.work, 'rev-parse', '--abbrev-ref', 'HEAD') == 'fixture-topic'
    assert len(git(fixture.work, 'stash', 'list').splitlines()) == 1
    assert git(fixture.work, 'diff', '--name-only', '--diff-filter=U') == 'fixture.txt'


def test_stash_mode_restores_changes_when_the_branch_cannot_be_created(
    plugin_root: Path,
    fixture: Fixture,
) -> None:
    """A failed switch after stashing pops the changes back onto the untouched checkout."""
    # Arrange
    git(fixture.work, 'branch', 'fixture-topic/blocker')
    (fixture.work / 'fixture.txt').write_text('local edit\ntwo\nthree\nfour\nfive\n')
    (fixture.work / 'untracked.txt').write_text('new\n')

    # Act
    completed, keys = run_script(plugin_root, fixture.work, 'fixture-topic', '--stash')

    # Assert
    assert outcome(completed) == (1, 'RESULT=SCRIPT_FAILURE')
    assert 'STASH_REF' not in keys
    assert git(fixture.work, 'rev-parse', '--abbrev-ref', 'HEAD') == 'main'
    assert git(fixture.work, 'stash', 'list') == ''
    assert (fixture.work / 'fixture.txt').read_text() == 'local edit\ntwo\nthree\nfour\nfive\n'
    assert (fixture.work / 'untracked.txt').read_text() == 'new\n'


def test_conflicted_stash_resolution_ends_with_the_stash_dropped(
    plugin_root: Path,
    fixture: Fixture,
) -> None:
    """The SKILL.md Workflow 4 steps leave the resolution uncommitted and drop the stash."""
    # Arrange
    fixture.advance_remote('fixture.txt', 'base edit\ntwo\nthree\nfour\nfive\n')
    (fixture.work / 'fixture.txt').write_text('local edit\ntwo\nthree\nfour\nfive\n')
    _, keys = run_script(plugin_root, fixture.work, 'fixture-topic', '--stash')
    head = git(fixture.work, 'rev-parse', 'HEAD')

    # Act
    git(fixture.work, 'checkout', '--theirs', '--', 'fixture.txt')
    git(fixture.work, 'add', 'fixture.txt')
    git(fixture.work, 'restore', '--staged', 'fixture.txt')
    unresolved = git(fixture.work, 'diff', '--name-only', '--diff-filter=U')
    git(fixture.work, 'stash', 'drop', keys['STASH_REF'])

    # Assert
    assert unresolved == ''
    assert git(fixture.work, 'stash', 'list') == ''
    assert git(fixture.work, 'rev-parse', 'HEAD') == head
    assert git(fixture.work, 'status', '--porcelain') == 'M fixture.txt'
    assert (fixture.work / 'fixture.txt').read_text() == 'local edit\ntwo\nthree\nfour\nfive\n'


def test_worktree_mode_uses_the_given_root_and_leaves_checkout_alone(
    plugin_root: Path,
    fixture: Fixture,
) -> None:
    """--worktree-root places <repo>-<branch> there; the current checkout stays on main."""
    # Arrange
    fetched_sha = fixture.advance_remote('late.txt', 'late\n')
    worktree_root = fixture.root / 'trees'

    # Act
    completed, keys = run_script(
        plugin_root, fixture.work, 'fixture/topic', '--worktree-root', str(worktree_root)
    )

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    worktree = worktree_root / 'work-fixture-topic'
    assert keys['WORKTREE'] == str(worktree)
    assert git(worktree, 'rev-parse', '--abbrev-ref', 'HEAD') == 'fixture/topic'
    assert git(worktree, 'rev-parse', 'HEAD') == fetched_sha
    assert git(worktree, 'rev-parse', '--abbrev-ref', '@{u}') == 'origin/fixture/topic'
    assert git(fixture.work, 'rev-parse', '--abbrev-ref', 'HEAD') == 'main'


def test_worktree_mode_defaults_to_an_ignored_worktrees_directory(
    plugin_root: Path,
    fixture: Fixture,
) -> None:
    """Outside /workspaces the worktree lands in .worktrees/, which Git then ignores."""
    # Act
    completed, keys = run_script(plugin_root, fixture.work, 'fixture/topic', '--worktree')

    # Assert
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    worktree = fixture.work / '.worktrees' / 'work-fixture-topic'
    assert keys['WORKTREE'] == str(worktree)
    assert git(worktree, 'rev-parse', '--abbrev-ref', 'HEAD') == 'fixture/topic'
    exclude = (fixture.work / '.git' / 'info' / 'exclude').read_text()
    assert '.worktrees/' in exclude.splitlines()
    assert git(fixture.work, 'status', '--porcelain') == ''


WORKSPACES = Path('/workspaces')


@pytest.mark.skipif(
    not (WORKSPACES.is_dir() and os.access(WORKSPACES, os.W_OK)),
    reason='needs a writable /workspaces',
)
def test_worktree_mode_under_workspaces_defaults_to_a_sibling(
    plugin_root: Path,
    fixture: Fixture,
) -> None:
    """A main checkout directly under /workspaces gets its worktree beside it there."""
    # Arrange
    name = f'fixture-{uuid4().hex}'
    checkout = WORKSPACES / name
    worktree = WORKSPACES / f'{name}-fixture-topic'
    git(fixture.root, 'clone', str(fixture.remote), str(checkout))
    try:
        # Act
        completed, keys = run_script(plugin_root, checkout, 'fixture/topic', '--worktree')

        # Assert
        assert outcome(completed) == (0, 'RESULT=SUCCESS')
        assert keys['WORKTREE'] == str(worktree)
        assert git(worktree, 'rev-parse', '--abbrev-ref', 'HEAD') == 'fixture/topic'
        assert not (checkout / '.worktrees').exists()
    finally:
        shutil.rmtree(worktree, ignore_errors=True)
        shutil.rmtree(checkout)


def test_unreachable_remote_reports_fetch_failed(plugin_root: Path, fixture: Fixture) -> None:
    """A remote that cannot be fetched produces FETCH_FAILED and no branch."""
    # Arrange
    git(fixture.work, 'remote', 'add', 'fixture-missing', str(fixture.root / 'absent.git'))

    # Act
    completed, _ = run_script(
        plugin_root, fixture.work, 'fixture-topic', '--remote', 'fixture-missing'
    )

    # Assert
    assert outcome(completed) == (6, 'RESULT=FETCH_FAILED')
    assert git(fixture.work, 'branch', '--list', 'fixture-topic') == ''


def test_rejected_push_keeps_the_local_branch(plugin_root: Path, fixture: Fixture) -> None:
    """PUSH_FAILED leaves the new local branch at the base, without an upstream."""
    # Arrange
    hook = fixture.remote / 'hooks' / 'pre-receive'
    hook.write_text('#!/bin/sh\nexit 1\n')
    hook.chmod(0o755)

    # Act
    completed, keys = run_script(plugin_root, fixture.work, 'fixture-topic')

    # Assert
    assert outcome(completed) == (5, 'RESULT=PUSH_FAILED')
    assert git(fixture.work, 'rev-parse', 'fixture-topic') == keys['BASE_SHA']
    upstream = subprocess.run(
        ['git', 'rev-parse', '--abbrev-ref', 'fixture-topic@{u}'],
        cwd=fixture.work,
        check=False,
        capture_output=True,
        text=True,
    )
    assert upstream.returncode != 0


def test_invalid_branch_name_is_a_preflight_error(plugin_root: Path, fixture: Fixture) -> None:
    """A name Git rejects stops before fetching."""
    # Act
    completed, _ = run_script(plugin_root, fixture.work, 'fixture..topic')

    # Assert
    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert "'fixture..topic' is not a valid branch name" in completed.stderr
