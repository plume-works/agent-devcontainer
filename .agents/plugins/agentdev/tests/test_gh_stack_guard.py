#!/usr/bin/env python3

"""Behavior tests for the gh-stack skill's stack-guard.sh."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess

from git_fixtures import FIXTURE_ENV, git, outcome
import pytest

# Pushes the way gh-stack v0.2.1 does: fetch every layer, then lease against the
# just-fetched tracking ref, so the lease never protects remote-only commits.
STUB_GH = r"""#!/usr/bin/env bash
set -euo pipefail
stub_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
stack="${stub_dir}/stack.json"
if [[ "$1 $2" == "stack view" ]]; then cat "${stack}"; exit 0; fi
if [[ "$1 $2" == "stack push" || "$1 $2" == "stack submit" ]]; then
  printf '%s\n' "$*" >> "${stub_dir}/pushes"
  if [[ -f "${stub_dir}/before-fetch" ]]; then bash "${stub_dir}/before-fetch"; fi
  mode="$(cat "${stub_dir}/push-mode" 2>/dev/null || echo real)"
  [[ "${mode}" == fail ]] && exit 1
  [[ "${mode}" == noop ]] && exit 0
  mapfile -t layers < <(jq -r '.branches[] | select(.isMerged | not) | .name' "${stack}")
  [[ "${mode}" == partial ]] && layers=("${layers[0]}")
  for b in "${layers[@]}"; do
    git fetch -q origin "+refs/heads/${b}:refs/remotes/origin/${b}" 2>/dev/null || true
  done
  args=()
  for b in "${layers[@]}"; do
    sha="$(git rev-parse -q --verify "refs/remotes/origin/${b}" || true)"
    args+=("--force-with-lease=refs/heads/${b}:${sha}")
  done
  for b in "${layers[@]}"; do args+=("refs/heads/${b}:refs/heads/${b}"); done
  git push -q origin "${args[@]}"
  [[ "${mode}" == partial ]] && exit 1
  exit 0
fi
echo "unexpected gh call: $*" >&2
exit 99
"""

# Runs the before-push hook once, on the first git push, then hands over to the real git.
STUB_GIT = r"""#!/usr/bin/env bash
set -euo pipefail
hook="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)/before-push"
if [[ "${1:-}" == push && -f "${hook}" ]]; then mv "${hook}" "${hook}.ran"; bash "${hook}.ran"; fi
exec REAL_GIT "$@"
"""


def commit_file(repository: Path, name: str, content: str) -> str:
    """Write `name` in `repository`, commit it with `name` as message, return the SHA."""
    (repository / name).write_text(content)
    git(repository, 'add', name)
    git(repository, 'commit', '-m', name)
    return git(repository, 'rev-parse', 'HEAD')


class Stack:
    """A stack main <- layer-a <- layer-b on a bare remote, a working clone, and a peer."""

    def __init__(self, root: Path) -> None:
        self.root = root
        seed = root / 'seed'
        seed.mkdir()
        git(seed, 'init', '--initial-branch=main')
        (seed / 'f.txt').write_text(''.join(f'{n}\n' for n in range(1, 31)))
        git(seed, 'add', 'f.txt')
        git(seed, 'commit', '-m', 'base')
        git(seed, 'switch', '-c', 'layer-a')
        commit_file(seed, 'a.txt', 'a1\n')
        self.edit_line(seed, '5', '5-A', 'A2')
        git(seed, 'switch', '-c', 'layer-b')
        self.edit_line(seed, '25', '25-B', 'B2')
        git(seed, 'switch', '-q', 'main')
        self.remote = root / 'remote.git'
        git(root, 'clone', '--bare', str(seed), str(self.remote))
        self.work = self.clone('work')
        self.peer = self.clone('peer')
        self.stub = root / 'stub'
        self.stub.mkdir()
        (self.stub / 'gh').write_text(STUB_GH)
        (self.stub / 'gh').chmod(0o755)
        real_git = shutil.which('git')
        assert real_git
        (self.stub / 'git').write_text(STUB_GIT.replace('REAL_GIT', real_git))
        (self.stub / 'git').chmod(0o755)
        self.merged: set[str] = set()
        self.write_stack()

    def clone(self, name: str) -> Path:
        """Clone the remote with local layer branches checked out at their remote tips."""
        path = self.root / name
        git(self.root, 'clone', '-q', str(self.remote), str(path))
        git(path, 'branch', 'layer-a', 'origin/layer-a')
        git(path, 'switch', '-q', '-c', 'layer-b', 'origin/layer-b')
        return path

    @staticmethod
    def edit_line(repository: Path, old: str, new: str, message: str) -> str:
        """Replace line `old` of f.txt with `new` and commit it as `message`."""
        path = repository / 'f.txt'
        lines = path.read_text().splitlines()
        path.write_text(''.join(f'{new if line == old else line}\n' for line in lines))
        git(repository, 'commit', '-am', message)
        return git(repository, 'rev-parse', 'HEAD')

    def write_stack(self) -> None:
        """Describe the stack the way gh stack view --json does."""
        branches = [
            {'name': name, 'isMerged': name in self.merged, 'isQueued': False}
            for name in ('layer-a', 'layer-b')
        ]
        (self.stub / 'stack.json').write_text(json.dumps({'trunk': 'main', 'branches': branches}))

    def peer_commit(self, branch: str, name: str) -> str:
        """Push a new commit to `branch` from the peer clone."""
        git(self.peer, 'fetch', '-q', 'origin')
        git(self.peer, 'switch', '-q', branch)
        git(self.peer, 'reset', '-q', '--hard', f'origin/{branch}')
        sha = commit_file(self.peer, name, f'{name}\n')
        git(self.peer, 'push', '-q', 'origin', branch)
        return sha

    def squash_merge_layer_a(self) -> None:
        """Squash-merge layer-a into main and rebase layer-b onto it, as GitHub does."""
        git(self.peer, 'fetch', '-q', 'origin')
        git(self.peer, 'switch', '-q', 'main')
        git(self.peer, 'merge', '-q', '--squash', 'origin/layer-a')
        git(self.peer, 'commit', '-q', '-m', 'layer-a (#1)')
        git(self.peer, 'switch', '-q', 'layer-b')
        git(self.peer, 'reset', '-q', '--hard', 'origin/layer-b')
        git(self.peer, 'rebase', '-q', '--onto', 'main', 'origin/layer-a', 'layer-b')
        git(self.peer, 'push', '-q', 'origin', 'main')
        git(self.peer, 'push', '-q', '--force', 'origin', 'layer-b')
        self.merged.add('layer-a')
        self.write_stack()

    def peer_merge_trunk(self, branch: str) -> str:
        """Advance main, then push a merge of main into `branch` from the peer clone."""
        git(self.peer, 'fetch', '-q', 'origin')
        git(self.peer, 'switch', '-q', 'main')
        git(self.peer, 'reset', '-q', '--hard', 'origin/main')
        commit_file(self.peer, 'm.txt', 'trunk\n')
        git(self.peer, 'push', '-q', 'origin', 'main')
        git(self.peer, 'switch', '-q', branch)
        git(self.peer, 'reset', '-q', '--hard', f'origin/{branch}')
        git(self.peer, 'merge', '-q', '--no-ff', '-m', 'R-merge', 'main')
        git(self.peer, 'push', '-q', 'origin', branch)
        return git(self.peer, 'rev-parse', 'HEAD')

    def race_peer_push(self, branch: str, name: str, hook: str) -> None:
        """Make hook `hook` (before-fetch or before-push) push a peer commit `name`."""
        peer = shlex.quote(str(self.peer))
        script = (
            f'git -C {peer} fetch -q origin\n'
            f'git -C {peer} switch -q {branch}\n'
            f'git -C {peer} reset -q --hard origin/{branch}\n'
            f'echo {name} > {peer}/{name}\n'
            f'git -C {peer} add {name}\n'
            f'git -C {peer} commit -q -m {name}\n'
            f'git -C {peer} push -q origin {branch}\n'
        )
        (self.stub / hook).write_text(script)

    def remote_tip(self, branch: str) -> str:
        """Read a branch tip from the bare remote."""
        return git(self.remote, 'rev-parse', f'refs/heads/{branch}')

    def remote_log(self, branch: str) -> list[str]:
        """List the commit subjects on a remote branch, newest first."""
        return git(self.remote, 'log', '--format=%s', f'refs/heads/{branch}').splitlines()

    def set_push_mode(self, mode: str) -> None:
        """Set the stub push to real, fail, noop, or partial (push the lowest layer, then fail)."""
        (self.stub / 'push-mode').write_text(mode)

    def pushes(self) -> list[str]:
        """Return the gh stack push/submit invocations the stub recorded."""
        path = self.stub / 'pushes'
        return path.read_text().splitlines() if path.exists() else []


def guard(
    plugin_root: Path, stack: Stack, *args: str
) -> tuple[subprocess.CompletedProcess[str], dict[str, list[str]]]:
    """Run stack-guard.sh in the working clone and collect its key=value stdout."""
    script = plugin_root / 'skills/gh-stack/agent-code/stack-guard.sh'
    env = {**os.environ, **FIXTURE_ENV, 'PATH': f'{stack.stub}{os.pathsep}{os.environ["PATH"]}'}
    completed = subprocess.run(
        [str(script), *args], cwd=stack.work, check=False, capture_output=True, text=True, env=env
    )
    keys: dict[str, list[str]] = {}
    for line in completed.stdout.splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            keys.setdefault(key, []).append(value)
    return completed, keys


@pytest.fixture
def stack(plugin_tmp_path: Path) -> Stack:
    """Provide a two-layer stack whose working clone matches the remote."""
    return Stack(plugin_tmp_path)


def test_begin_fast_forwards_a_layer_its_remote_is_ahead_of(
    plugin_root: Path, stack: Stack
) -> None:
    """A remote-ahead layer is fast-forwarded, so the publish keeps the remote commit."""
    remote_sha = stack.peer_commit('layer-b', 'R-fix')

    completed, keys = guard(plugin_root, stack, 'begin')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert keys['FAST_FORWARDED'] == ['layer-b']
    assert git(stack.work, 'rev-parse', 'layer-b') == remote_sha
    published, _ = guard(plugin_root, stack, 'publish')
    assert outcome(published) == (0, 'RESULT=SUCCESS')
    assert stack.remote_tip('layer-b') == remote_sha


def test_begin_stops_when_local_and_remote_each_gained_a_commit(
    plugin_root: Path, stack: Stack
) -> None:
    """A truly diverged layer stops begin and names the remote commit."""
    stack.peer_commit('layer-b', 'R-fix')
    local_before = commit_file(stack.work, 'l.txt', 'local\n')

    completed, _ = guard(plugin_root, stack, 'begin')

    assert outcome(completed) == (3, 'RESULT=REMOTE_ONLY_COMMITS')
    assert 'R-fix' in completed.stderr
    assert git(stack.work, 'rev-parse', 'layer-b') == local_before


def test_begin_stops_on_a_remote_only_merge_of_trunk(plugin_root: Path, stack: Stack) -> None:
    """A merge of trunk on the remote, e.g. from GitHub's conflict editor, is remote work."""
    merge_sha = stack.peer_merge_trunk('layer-b')
    commit_file(stack.work, 'l.txt', 'local\n')

    completed, _ = guard(plugin_root, stack, 'begin')

    assert outcome(completed) == (3, 'RESULT=REMOTE_ONLY_COMMITS')
    assert 'R-merge' in completed.stderr
    assert stack.remote_tip('layer-b') == merge_sha


def test_publish_without_begin_stops_on_a_remote_only_merge_of_trunk(
    plugin_root: Path, stack: Stack
) -> None:
    """The no-record fallback refuses to overwrite a remote-only merge."""
    merge_sha = stack.peer_merge_trunk('layer-b')
    commit_file(stack.work, 'l.txt', 'local\n')

    completed, _ = guard(plugin_root, stack, 'publish')

    assert outcome(completed) == (3, 'RESULT=REMOTE_ONLY_COMMITS')
    assert 'R-merge' in completed.stderr
    assert stack.pushes() == []
    assert stack.remote_tip('layer-b') == merge_sha


def test_begin_stops_on_a_whitespace_only_remote_rewrite(plugin_root: Path, stack: Stack) -> None:
    """A remote commit differing from the local one only in whitespace is remote work."""
    git(stack.peer, 'switch', '-q', 'layer-b')
    git(stack.peer, 'reset', '-q', '--hard', 'origin/layer-b~1')
    Stack.edit_line(stack.peer, '25', '25-B ', 'B2')
    git(stack.peer, 'push', '-q', '--force', 'origin', 'layer-b')
    remote_sha = stack.remote_tip('layer-b')

    completed, _ = guard(plugin_root, stack, 'begin')

    assert outcome(completed) == (3, 'RESULT=REMOTE_ONLY_COMMITS')
    assert 'B2' in completed.stderr
    assert stack.remote_tip('layer-b') == remote_sha


def test_begin_accepts_the_rebase_github_makes_after_a_lower_layer_merges(
    plugin_root: Path, stack: Stack
) -> None:
    """A layer GitHub rebased onto the squash commit holds nothing to lose."""
    stack.squash_merge_layer_a()

    completed, _ = guard(plugin_root, stack, 'begin')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')


def test_begin_names_only_the_new_commit_on_a_rebased_layer(
    plugin_root: Path, stack: Stack
) -> None:
    """After GitHub's rebase, only a genuinely new remote commit stops begin."""
    stack.squash_merge_layer_a()
    stack.peer_commit('layer-b', 'R-fix')

    completed, _ = guard(plugin_root, stack, 'begin')

    assert outcome(completed) == (3, 'RESULT=REMOTE_ONLY_COMMITS')
    assert 'R-fix' in completed.stderr
    assert 'B2' not in completed.stderr
    assert 'layer-b (#1)' not in completed.stderr


def test_begin_accepts_a_local_commit_on_a_rebased_layer(plugin_root: Path, stack: Stack) -> None:
    """A local commit on top of the pre-rebase layer loses nothing on the remote."""
    stack.squash_merge_layer_a()
    commit_file(stack.work, 'l.txt', 'local\n')

    completed, _ = guard(plugin_root, stack, 'begin')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')


def test_publish_after_a_clean_restack_pushes_every_layer(plugin_root: Path, stack: Stack) -> None:
    """An edit to the lower layer, replayed upstack, publishes and verifies both tips."""
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    git(stack.work, 'switch', '-q', 'layer-a')
    commit_file(stack.work, 'a2.txt', 'a2\n')
    git(stack.work, 'rebase', '-q', 'layer-a', 'layer-b')

    completed, _ = guard(plugin_root, stack, 'publish')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    for layer in ('layer-a', 'layer-b'):
        assert stack.remote_tip(layer) == git(stack.work, 'rev-parse', layer)


def resolve_conflicting_restack(stack: Stack) -> None:
    """Change layer-a on B2's line and replay layer-b with a resolution of the conflict."""
    git(stack.work, 'switch', '-q', 'layer-a')
    Stack.edit_line(stack.work, '25', '25-A', 'A3')
    git(stack.work, 'switch', '-q', 'layer-b')
    git(stack.work, 'reset', '-q', '--hard', 'layer-a')
    Stack.edit_line(stack.work, '25-A', '25-AB', 'B2')


def test_publish_after_begin_accepts_a_resolved_conflict(plugin_root: Path, stack: Stack) -> None:
    """The begin record proves nothing moved, so a changed patch is not a loss."""
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    resolve_conflicting_restack(stack)

    completed, _ = guard(plugin_root, stack, 'publish')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert stack.remote_tip('layer-b') == git(stack.work, 'rev-parse', 'layer-b')


def test_publish_without_begin_stops_on_a_resolved_conflict(
    plugin_root: Path, stack: Stack
) -> None:
    """Without a record, publish errs toward stopping rather than risking a loss."""
    resolve_conflicting_restack(stack)
    remote_before = stack.remote_tip('layer-b')

    completed, _ = guard(plugin_root, stack, 'publish')

    assert outcome(completed) == (3, 'RESULT=REMOTE_ONLY_COMMITS')
    assert stack.pushes() == []
    assert stack.remote_tip('layer-b') == remote_before


def test_publish_stops_when_a_remote_moved_after_begin(plugin_root: Path, stack: Stack) -> None:
    """A push to a layer during the edit stops publish before anything is pushed."""
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    commit_file(stack.work, 'l.txt', 'local\n')
    remote_sha = stack.peer_commit('layer-b', 'R-fix')

    completed, _ = guard(plugin_root, stack, 'publish')

    assert outcome(completed) == (4, 'RESULT=REMOTE_MOVED')
    assert 'layer-b' in completed.stderr
    assert stack.pushes() == []
    assert stack.remote_tip('layer-b') == remote_sha


def test_publish_reports_a_push_that_left_a_layer_behind(plugin_root: Path, stack: Stack) -> None:
    """A remote tip that differs from the local one after the push is not published."""
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    commit_file(stack.work, 'l.txt', 'local\n')
    stack.race_peer_push('layer-b', 'R-late', 'before-fetch')
    stack.set_push_mode('noop')

    completed, _ = guard(plugin_root, stack, 'publish')

    assert outcome(completed) == (6, 'RESULT=PUSH_INCOMPLETE')
    assert 'layer-b' in completed.stderr


def test_publish_reports_a_failed_push(plugin_root: Path, stack: Stack) -> None:
    """A failing gh stack push surfaces as PUSH_FAILED."""
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    stack.set_push_mode('fail')

    completed, _ = guard(plugin_root, stack, 'publish')

    assert outcome(completed) == (5, 'RESULT=PUSH_FAILED')


def test_publish_rerun_after_a_partial_push_completes(plugin_root: Path, stack: Stack) -> None:
    """A layer the failed publish already pushed is not mistaken for a foreign move."""
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    git(stack.work, 'switch', '-q', 'layer-a')
    commit_file(stack.work, 'a2.txt', 'a2\n')
    git(stack.work, 'rebase', '-q', 'layer-a', 'layer-b')
    stack.set_push_mode('partial')
    assert outcome(guard(plugin_root, stack, 'publish')[0]) == (5, 'RESULT=PUSH_FAILED')
    assert stack.remote_tip('layer-a') == git(stack.work, 'rev-parse', 'layer-a')
    stack.set_push_mode('real')

    completed, _ = guard(plugin_root, stack, 'publish')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    for layer in ('layer-a', 'layer-b'):
        assert stack.remote_tip(layer) == git(stack.work, 'rev-parse', layer)


@pytest.mark.parametrize('log_ref_updates', ['true', 'false'])
def test_publish_reports_a_peer_push_the_push_overwrote(
    plugin_root: Path, stack: Stack, log_ref_updates: str
) -> None:
    """A peer push landing between publish's check and gh stack's lease is reported lost."""
    git(stack.work, 'config', 'core.logAllRefUpdates', log_ref_updates)
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    commit_file(stack.work, 'l.txt', 'local\n')
    stack.race_peer_push('layer-b', 'R-race', 'before-fetch')

    completed, _ = guard(plugin_root, stack, 'publish')

    assert outcome(completed) == (7, 'RESULT=REMOTE_OVERWRITTEN')
    assert 'layer-b' in completed.stderr
    assert 'R-race' in completed.stderr
    assert git(stack.peer, 'rev-parse', 'HEAD')[:7] in completed.stderr


def test_publish_leases_on_the_tip_it_checked(plugin_root: Path, stack: Stack) -> None:
    """A peer push landing after publish's check survives, and publish stops."""
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    commit_file(stack.work, 'l.txt', 'local\n')
    stack.race_peer_push('layer-b', 'R-race', 'before-push')

    completed, _ = guard(plugin_root, stack, 'publish')

    assert outcome(completed) == (4, 'RESULT=REMOTE_MOVED')
    assert 'layer-b' in completed.stderr
    assert stack.remote_tip('layer-b') == git(stack.peer, 'rev-parse', 'HEAD')
    assert 'R-race' in stack.remote_log('layer-b')
    assert stack.pushes() == []


def test_publish_submit_runs_gh_stack_submit(plugin_root: Path, stack: Stack) -> None:
    """--submit publishes through gh stack submit --auto."""
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    commit_file(stack.work, 'l.txt', 'local\n')

    completed, _ = guard(plugin_root, stack, 'publish', '--submit')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert stack.pushes() == ['stack submit --auto --remote origin']


def test_begin_moves_a_layer_created_at_trunk_onto_its_remote(
    plugin_root: Path, stack: Stack
) -> None:
    """A layer adopted at the trunk tip is fast-forwarded to the real remote branch."""
    git(stack.work, 'switch', '-q', 'layer-b')
    git(stack.work, 'branch', '-f', 'layer-a', 'origin/main')
    remote_sha = stack.remote_tip('layer-a')

    completed, keys = guard(plugin_root, stack, 'begin')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert keys['FAST_FORWARDED'] == ['layer-a']
    assert git(stack.work, 'rev-parse', 'layer-a') == remote_sha


def test_unguarded_stub_push_drops_the_remote_commit(stack: Stack) -> None:
    """The stub reproduces the defect the guard exists for."""
    stack.peer_commit('layer-b', 'R-fix')
    env = {**os.environ, **FIXTURE_ENV}
    subprocess.run([str(stack.stub / 'gh'), 'stack', 'push'], cwd=stack.work, check=True, env=env)

    assert 'R-fix' not in stack.remote_log('layer-b')


def test_begin_adds_the_exclude_on_its_own_line(plugin_root: Path, stack: Stack) -> None:
    """An exclude file without a final newline keeps its last pattern intact."""
    exclude = stack.work / git(stack.work, 'rev-parse', '--git-path', 'info/exclude')
    exclude.write_text('*.log')

    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')

    assert exclude.read_text().splitlines() == ['*.log', '.tmp/']


def test_begin_keeps_the_worktree_clean_where_tmp_is_not_ignored(
    plugin_root: Path, stack: Stack
) -> None:
    """The state file is excluded once, so gh stack rebase never sees a dirty tree."""
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')

    assert git(stack.work, 'status', '--porcelain') == ''
    exclude = Path(git(stack.work, 'rev-parse', '--git-path', 'info/exclude'))
    assert (stack.work / exclude).read_text().splitlines().count('.tmp/') == 1
