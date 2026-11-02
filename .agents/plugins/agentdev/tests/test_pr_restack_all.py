#!/usr/bin/env python3

"""Behavior tests for bin/pr_restack_all.py against real git repositories."""

from __future__ import annotations

import dataclasses
import importlib.util
from pathlib import Path
import subprocess
import sys
from types import ModuleType

from git_fixtures import FIXTURE_ENV, git
import pytest


@pytest.fixture
def restack(plugin_root: Path, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Load the script as a module, with the fixture identity in the environment."""
    for key, value in FIXTURE_ENV.items():
        monkeypatch.setenv(key, value)
    spec = importlib.util.spec_from_file_location(
        'pr_restack_all', plugin_root / 'bin/pr_restack_all.py'
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, 'pr_restack_all', module)
    spec.loader.exec_module(module)
    return module


class Hub:
    """
    A bare remote standing in for GitHub, with its pull requests kept in memory.

    `publisher` acts for the pull request owners and for GitHub's squash merge;
    `work` is the checkout pr-restack-all runs in.
    """

    def __init__(self, root: Path, module: ModuleType) -> None:
        self.module = module
        self.pulls: dict[int, object] = {}
        self.remote = root / 'remote.git'
        seed = root / 'seed'
        seed.mkdir()
        git(seed, 'init', '--quiet', '--initial-branch=main')
        for name in ('a.txt', 'b.txt', 'c.txt', 'main.txt'):
            (seed / name).write_text('one\ntwo\nthree\n')
        git(seed, 'add', '.')
        git(seed, 'commit', '--quiet', '-m', 'm0')
        git(root, 'clone', '--quiet', '--bare', str(seed), str(self.remote))
        self.publisher = root / 'publisher'
        git(root, 'clone', '--quiet', str(self.remote), str(self.publisher))
        self.work = root / 'work'
        git(root, 'clone', '--quiet', str(self.remote), str(self.work))

    # --- the PullRequests protocol -------------------------------------------------

    def view(self, number: int):
        """Return pull request `number`, its open head read from the remote."""
        pull = self.pulls[number]
        if pull.state == 'OPEN':
            pull = dataclasses.replace(pull, head_oid=self.remote_sha(pull.head_branch))
        return pull

    def open_with_head(self, branch: str):
        """Return the open pull request whose head is `branch`."""
        for number, pull in self.pulls.items():
            if pull.state == 'OPEN' and pull.head_branch == branch:
                return self.view(number)
        return None

    def edit_body(self, number: int, body: str) -> None:
        """Replace a body."""
        self.pulls[number] = dataclasses.replace(self.pulls[number], body=body)

    # --- the owners and GitHub ---------------------------------------------------

    def remote_sha(self, ref: str) -> str:
        """Return the remote's commit for `ref`."""
        return git(self.remote, 'rev-parse', ref)

    def commit(self, branch: str, name: str, line: str) -> str:
        """Append `line` to `name` on `branch` as an owner, push, and return the head."""
        git(self.publisher, 'fetch', '--quiet', 'origin')
        git(self.publisher, 'checkout', '--quiet', '-B', branch, f'origin/{branch}')
        path = self.publisher / name
        path.write_text((path.read_text() if path.exists() else '') + f'{line}\n')
        git(self.publisher, 'add', name)
        git(self.publisher, 'commit', '--quiet', '-m', f'{branch}: {line}')
        git(self.publisher, 'push', '--quiet', 'origin', f'{branch}:{branch}')
        self.sync_pull_refs()
        return git(self.publisher, 'rev-parse', 'HEAD')

    def sync_pull_refs(self) -> None:
        """Point each open pull request's refs/pull/<n>/head at its branch, as GitHub does."""
        for number, pull in self.pulls.items():
            if pull.state == 'OPEN':
                sha = self.remote_sha(pull.head_branch)
                git(self.remote, 'update-ref', f'refs/pull/{number}/head', sha)

    def open(self, number: int, branch: str, base: str, *depends: int) -> None:
        """Cut `branch` from `base`, commit on it, and open its pull request."""
        git(self.publisher, 'fetch', '--quiet', 'origin')
        git(self.publisher, 'checkout', '--quiet', '-B', branch, f'origin/{base}')
        git(self.publisher, 'push', '--quiet', 'origin', f'{branch}:{branch}')
        self.commit(branch, f'{branch}.txt', branch)
        body = '## Summary\n\nWork.\n'
        if depends:
            body += '\n## Depends on\n\n' + ''.join(f'- #{p}\n' for p in depends)
        self.pulls[number] = self.module.PullRequest(number, 'OPEN', branch, base, '', None, body)
        self.sync_pull_refs()

    def squash_merge(self, number: int) -> str:
        """Squash-merge into main as GitHub does, retarget successors, delete the branch."""
        pull = self.pulls[number]
        self.sync_pull_refs()
        head = self.remote_sha(pull.head_branch)
        git(self.publisher, 'fetch', '--quiet', 'origin')
        git(self.publisher, 'checkout', '--quiet', '-B', 'main', 'origin/main')
        git(self.publisher, 'merge', '--quiet', '--squash', head)
        git(self.publisher, 'commit', '--quiet', '-m', f'Squash #{number}')
        git(self.publisher, 'push', '--quiet', 'origin', 'main')
        merge = git(self.publisher, 'rev-parse', 'HEAD')
        git(self.publisher, 'push', '--quiet', 'origin', '--delete', pull.head_branch)
        self.pulls[number] = dataclasses.replace(
            pull, state='MERGED', head_oid=head, merge_oid=merge
        )
        for other, successor in self.pulls.items():
            if successor.state == 'OPEN' and successor.base_branch == pull.head_branch:
                self.pulls[other] = dataclasses.replace(successor, base_branch='main')
        return merge

    def advance_main(self, line: str) -> str:
        """Commit on main as someone else."""
        return self.commit('main', 'main.txt', line)

    def contains(self, branch: str, commit: str) -> bool:
        """Return whether the remote branch contains `commit`."""
        completed = subprocess.run(
            ['git', 'merge-base', '--is-ancestor', commit, branch], cwd=self.remote, check=False
        )
        return completed.returncode == 0


@pytest.fixture
def hub(plugin_tmp_path: Path, restack: ModuleType, monkeypatch: pytest.MonkeyPatch) -> Hub:
    """Build the hub and run from its working checkout."""
    built = Hub(plugin_tmp_path, restack)
    monkeypatch.chdir(built.work)
    return built


def run(restack: ModuleType, hub: Hub, *arguments: str) -> int:
    """Run the script in-process against the hub's pull requests."""
    try:
        return restack.run([*arguments, '--trunk', 'main'], prs=hub)
    except restack.Stop as stop:
        return stop.code


def keys(output: str, key: str) -> list[str]:
    """Return every value printed for `key`."""
    prefix = f'{key}='
    return [line[len(prefix) :] for line in output.splitlines() if line.startswith(prefix)]


def test_restack_onto_an_open_predecessor_merges_its_head(
    restack: ModuleType, hub: Hub, capsys: pytest.CaptureFixture[str]
) -> None:
    hub.open(1, 'x', 'main')
    hub.open(2, 'y', 'x', 1)
    old_y = hub.remote_sha('y')
    new_x = hub.commit('x', 'a.txt', 'x2')
    assert run(restack, hub, '#2') == 0
    output = capsys.readouterr().out
    assert keys(output, 'CHAIN') == ['#1,#2']
    assert keys(output, 'RECONNECTED') == []
    assert hub.contains('y', new_x)
    assert hub.contains('y', old_y)
    assert hub.pulls[2].body.endswith('- #1\n')


def test_restack_onto_a_merged_predecessor_reconnects_and_records(
    restack: ModuleType, hub: Hub, capsys: pytest.CaptureFixture[str]
) -> None:
    hub.open(1, 'x', 'main')
    hub.open(2, 'y', 'x', 1)
    hub.advance_main('o')
    old_y = hub.remote_sha('y')
    head_x = hub.remote_sha('x')
    merge_x = hub.squash_merge(1)
    assert run(restack, hub, '2') == 0
    output = capsys.readouterr().out
    assert keys(output, 'RECONNECTED') == [f'#1 HEAD={head_x} MERGE={merge_x}']
    assert hub.contains('y', merge_x)
    assert hub.contains('y', old_y)
    diff = git(hub.remote, 'diff', '--name-only', merge_x, 'y')
    assert diff.splitlines() == ['y.txt']
    assert hub.pulls[2].body.endswith(
        f'- #1 — merged as {merge_x[:8]} (head {head_x[:8]}), reconnected\n'
    )


def test_x_plus_two_takes_main_only_up_to_x_plus_one_merge(
    restack: ModuleType, hub: Hub, capsys: pytest.CaptureFixture[str]
) -> None:
    hub.open(1, 'x', 'main')
    hub.open(2, 'y', 'x', 1)
    hub.open(3, 'z', 'y', 2)
    hub.advance_main('o')
    hub.squash_merge(1)
    assert run(restack, hub, '3') == 0
    assert keys(capsys.readouterr().out, 'CHAIN') == ['#2,#3']
    hub.advance_main('q')
    merge_y = hub.squash_merge(2)
    later = hub.advance_main('r')
    assert run(restack, hub, '3') == 0
    output = capsys.readouterr().out
    assert keys(output, 'CHAIN') == ['#3']
    assert [line.split()[0] for line in keys(output, 'RECONNECTED')] == ['#2']
    assert hub.contains('z', merge_y)
    assert not hub.contains('z', later)


def test_rerun_after_a_conflict_skips_what_was_restacked(
    restack: ModuleType, hub: Hub, capsys: pytest.CaptureFixture[str]
) -> None:
    hub.open(1, 'x', 'main')
    hub.open(2, 'y', 'x', 1)
    hub.open(3, 'z', 'y', 2)
    hub.commit('y', 'a.txt', 'from y')
    hub.commit('x', 'a.txt', 'from x')
    assert run(restack, hub, '3') == restack.MERGE_CONFLICT
    worktree = Path(keys(capsys.readouterr().out, 'WORKTREE')[0])
    (worktree / 'a.txt').write_text('one\ntwo\nthree\nfrom x\nfrom y\n')
    git(worktree, 'commit', '--quiet', '-am', 'Resolve')
    git(worktree, 'push', '--quiet', 'origin', 'HEAD:refs/heads/y')
    resolved = hub.remote_sha('y')
    assert run(restack, hub, '3') == 0
    output = capsys.readouterr().out
    pushed = [line.split()[0] for line in keys(output, 'PUSHED')]
    assert pushed == ['z']
    assert hub.remote_sha('y') == resolved
    assert hub.contains('z', resolved)


def test_a_branch_with_two_dependencies_reconnects_the_merged_one(
    restack: ModuleType, hub: Hub, capsys: pytest.CaptureFixture[str]
) -> None:
    hub.open(1, 'x', 'main')
    hub.open(5, 'w', 'main')
    git(hub.publisher, 'fetch', '--quiet', 'origin')
    git(hub.publisher, 'checkout', '--quiet', '-B', 'b', 'origin/x')
    git(hub.publisher, 'commit', '--quiet', '--allow-empty', '-m', 'Depend\n\nDepends-on: #1')
    git(hub.publisher, 'commit', '--quiet', '--allow-empty', '-m', 'Depend\n\nDepends-on: #5')
    git(hub.publisher, 'merge', '--quiet', '--no-edit', 'origin/w')
    git(hub.publisher, 'push', '--quiet', 'origin', 'b:b')
    hub.advance_main('o')
    merge_x = hub.squash_merge(1)
    assert run(restack, hub, 'b', '--list') == 0
    assert keys(capsys.readouterr().out, 'DEPENDENCY') == ['#1 MERGED x', '#5 OPEN w']
    assert run(restack, hub, 'b') == 0
    output = capsys.readouterr().out
    assert [line.split()[0] for line in keys(output, 'RECONNECTED')] == ['#1']
    assert hub.contains('b', merge_x)


def test_trailers_carried_from_a_predecessor_are_not_own_dependencies(
    restack: ModuleType, hub: Hub, capsys: pytest.CaptureFixture[str]
) -> None:
    hub.open(1, 'x', 'main')
    git(hub.publisher, 'fetch', '--quiet', 'origin')
    git(hub.publisher, 'checkout', '--quiet', '-B', 'y', 'origin/x')
    git(hub.publisher, 'commit', '--quiet', '--allow-empty', '-m', 'Depend\n\nDepends-on: #1')
    git(hub.publisher, 'push', '--quiet', 'origin', 'y:y')
    hub.pulls[2] = restack.PullRequest(2, 'OPEN', 'y', 'x', '', None, '## Depends on\n\n- #1\n')
    hub.sync_pull_refs()
    git(hub.publisher, 'checkout', '--quiet', '-B', 'z', 'origin/y')
    git(hub.publisher, 'commit', '--quiet', '--allow-empty', '-m', 'Depend\n\nDepends-on: #2')
    git(hub.publisher, 'push', '--quiet', 'origin', 'z:z')
    assert run(restack, hub, 'z', '--list') == 0
    assert keys(capsys.readouterr().out, 'DEPENDENCY') == ['#2 OPEN y']


def test_no_local_branch_or_other_worktree_changes(
    restack: ModuleType, hub: Hub, capsys: pytest.CaptureFixture[str]
) -> None:
    hub.open(1, 'x', 'main')
    hub.open(2, 'y', 'x', 1)
    git(hub.work, 'fetch', '--quiet', 'origin')
    other = hub.work.parent / 'other'
    git(hub.work, 'worktree', 'add', '--quiet', '-b', 'y', str(other), 'origin/y')
    before_refs = git(hub.work, 'for-each-ref', 'refs/heads')
    before_other = git(other, 'rev-parse', 'HEAD')
    hub.advance_main('o')
    hub.squash_merge(1)
    assert run(restack, hub, '2') == 0
    assert keys(capsys.readouterr().out, 'PUSHED')
    assert git(hub.work, 'for-each-ref', 'refs/heads') == before_refs
    assert git(other, 'rev-parse', 'HEAD') == before_other
    assert git(hub.work, 'branch', '--show-current') == 'main'
    worktrees = git(hub.work, 'worktree', 'list', '--porcelain')
    assert '.tmp/pr-restack-all-' not in worktrees


def test_a_predecessor_closed_unmerged_stops(restack: ModuleType, hub: Hub) -> None:
    hub.open(1, 'x', 'main')
    hub.open(2, 'y', 'main', 1)
    hub.pulls[1] = dataclasses.replace(hub.pulls[1], state='CLOSED')
    assert run(restack, hub, '2') == restack.PREDECESSOR_CLOSED


def test_a_last_entry_that_is_not_the_pull_request_below_stops(
    restack: ModuleType, hub: Hub
) -> None:
    hub.open(1, 'x', 'main')
    hub.open(2, 'y', 'x', 7)
    assert run(restack, hub, '2') == restack.CHAIN_BROKEN


def test_a_final_head_that_moved_stops(restack: ModuleType, hub: Hub) -> None:
    hub.open(1, 'x', 'main')
    hub.open(2, 'y', 'x', 1)
    hub.squash_merge(1)
    hub.pulls[1] = dataclasses.replace(hub.pulls[1], head_oid='0' * 40)
    assert run(restack, hub, '2') == restack.HEAD_MISMATCH


def test_the_command_line_names_its_result(plugin_root: Path, plugin_tmp_path: Path) -> None:
    completed = subprocess.run(
        [str(plugin_root / 'bin/pr_restack_all.py')],
        cwd=plugin_tmp_path, check=False, capture_output=True, text=True,
    )  # fmt: skip
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        2,
        'RESULT=PREFLIGHT_ERROR',
    )


@pytest.mark.parametrize('fork', [1, 2])
def test_a_link_whose_head_is_in_a_fork_stops_before_any_push(
    restack: ModuleType, hub: Hub, fork: int
) -> None:
    hub.open(1, 'x', 'main')
    hub.open(2, 'y', 'x', 1)
    hub.commit('x', 'a.txt', 'x2')
    before = hub.remote_sha('y')
    hub.pulls[fork] = dataclasses.replace(hub.pulls[fork], cross_repository=True)
    assert run(restack, hub, '2') == restack.CHAIN_BROKEN
    assert hub.remote_sha('y') == before
