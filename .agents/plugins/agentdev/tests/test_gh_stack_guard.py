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

# Models gh-stack v0.2.1: link pushes its branch arguments without force and records no local
# state; stack checkout records the linked PRs and moves HEAD; the PR API reports the
# stack number in stack-number, or null.
STUB_GH = r"""#!/usr/bin/env bash
set -euo pipefail
stub_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$1 $2" == "stack view" ]]; then cat "${stub_dir}/stack.json"; exit 0; fi
if [[ "$1 $2" == "pr list" ]]; then
  number="$(jq -r --arg b "$4" '.branches[] | select(.name == $b) | .pr.number // empty' \
    "${stub_dir}/stack.json")"
  if [[ -z "${number}" ]] && grep -qx -- "$4" "${stub_dir}/linked" 2>/dev/null; then
    number="$(jq -r --arg b "$4" '.branches | map(.name) | index($b) + 1' "${stub_dir}/stack.json")"
  fi
  printf '%s\n' "${number}"
  exit 0
fi
if [[ "$1 $2" == "stack checkout" ]]; then
  printf '%s\n' "$*" >> "${stub_dir}/checkouts"
  [[ "$(cat "${stub_dir}/checkout-mode" 2>/dev/null || echo real)" == fail ]] && exit 1
  [[ "$3" == "$(cat "${stub_dir}/stack-number")" ]] || exit 1
  touch "${stub_dir}/linked"
  linked="$(jq -R . "${stub_dir}/linked" | jq -s .)"
  jq --argjson linked "${linked}" '.branches |= [to_entries[] | .value + (
    if .value.pr == null and (.value.name | IN($linked[])) then
      {pr: {number: (.key + 1), state: "OPEN",
            url: ("https://github.example/acme/widgets/pull/" + (.key + 1 | tostring))}}
    else {} end)]' "${stub_dir}/stack.json" > "${stub_dir}/stack.json.new"
  mv "${stub_dir}/stack.json.new" "${stub_dir}/stack.json"
  if [[ -s "${stub_dir}/linked" ]]; then git switch -q "$(tail -n 1 "${stub_dir}/linked")"; fi
  exit 0
fi
if [[ "$1" == api ]]; then
  [[ "$(cat "${stub_dir}/api-mode" 2>/dev/null || echo real)" == fail ]] && exit 1
  cat "${stub_dir}/stack-number" 2>/dev/null || echo null
  exit 0
fi
if [[ "$1 $2" == "stack link" ]]; then
  printf '%s\n' "$*" >> "${stub_dir}/links"
  if [[ -f "${stub_dir}/before-link" ]]; then bash "${stub_dir}/before-link"; fi
  mode="$(cat "${stub_dir}/link-mode" 2>/dev/null || echo real)"
  [[ "${mode}" == fail ]] && exit 1
  [[ "${mode}" == noop ]] && exit 0
  shift 2
  refspecs=()
  while [[ "${1:-}" == --* ]]; do shift 2; done
  if [[ "${1:-}" =~ ^[0-9]+$ ]] && ! git show-ref -q --verify "refs/heads/$1"; then
    [[ "$1" == "$(cat "${stub_dir}/stack-number" 2>/dev/null)" ]] || exit 1
    shift
  fi
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --remote | --base) shift 2 ;;
      *)
        if git show-ref -q --verify "refs/heads/$1"; then refspecs+=("refs/heads/$1:refs/heads/$1"); fi
        shift
        ;;
    esac
  done
  [[ ${#refspecs[@]} -eq 0 ]] || git push -q --atomic origin "${refspecs[@]}"
  for ref in "${refspecs[@]}"; do ref="${ref%%:*}"; printf '%s\n' "${ref#refs/heads/}"; done >> "${stub_dir}/linked"
  [[ -f "${stub_dir}/stack-number" ]] || echo 7 > "${stub_dir}/stack-number"
  exit 0
fi
echo "unexpected gh call: $*" >&2
exit 99
"""

# Runs the before-push hook once, before the first git push, and the after-ls-remote hook
# once, after the first git ls-remote; otherwise hands over to the real git.
STUB_GIT = r"""#!/usr/bin/env bash
set -euo pipefail
stub_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
hook="${stub_dir}/before-push"
if [[ "${1:-}" == push && -f "${hook}" ]]; then mv "${hook}" "${hook}.ran"; bash "${hook}.ran"; fi
hook="${stub_dir}/after-ls-remote"
if [[ "${1:-}" == ls-remote && -f "${hook}" ]]; then
  listing="$(REAL_GIT "$@")"
  mv "${hook}" "${hook}.ran"
  bash "${hook}.ran"
  printf '%s\n' "${listing}"
  exit 0
fi
exec REAL_GIT "$@"
"""


def pr_url(number: int) -> str:
    """Return the made-up URL of pull request `number`."""
    return f'https://github.example/acme/widgets/pull/{number}'


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
        self.queued: set[str] = set()
        self.without_pr: set[str] = set()
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

    def write_stack(self, names: tuple[str, ...] = ('layer-a', 'layer-b')) -> None:
        """Describe the stack the way gh stack view --json does; layer N has PR N."""
        branches = [
            {
                'name': name,
                'isMerged': name in self.merged,
                'isQueued': name in self.queued,
                'pr': {'number': number, 'url': pr_url(number), 'state': 'OPEN'},
            }
            for number, name in enumerate(names, start=1)
        ]
        for branch in branches:
            if branch['name'] in self.without_pr:
                del branch['pr']
        stack = json.dumps({'trunk': 'main', 'branches': branches})
        (self.stub / 'stack.json').write_text(stack)

    def peer_commit(self, branch: str, name: str) -> str:
        """Push a new commit to `branch` from the peer clone."""
        git(self.peer, 'fetch', '-q', 'origin')
        git(self.peer, 'switch', '-q', branch)
        git(self.peer, 'reset', '-q', '--hard', f'origin/{branch}')
        sha = commit_file(self.peer, name, f'{name}\n')
        git(self.peer, 'push', '-q', 'origin', branch)
        return sha

    def squash_merge_layer_a(self, describe: bool = True) -> None:
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
        if describe:
            self.write_stack()

    def view(self) -> dict:
        """Return what gh stack view --json reports now."""
        return json.loads((self.stub / 'stack.json').read_text())

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
        """Make hook `hook` (a STUB_GH or STUB_GIT hook file) push a peer commit `name`."""
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

    def set_link_mode(self, mode: str) -> None:
        """Make the stub's gh stack link really push (real), fail, or exit 0 untouched (noop)."""
        (self.stub / 'link-mode').write_text(mode)

    def links(self) -> list[str]:
        """Return the gh stack link invocations the stub recorded."""
        path = self.stub / 'links'
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
    assert stack.links() == []
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


def github_rebase_layer_b(stack: Stack, *remote_only: list[str]) -> None:
    """Advance main and rebase layer-b onto it from the peer, adding commits on top."""
    git(stack.peer, 'fetch', '-q', 'origin')
    git(stack.peer, 'switch', '-q', 'main')
    git(stack.peer, 'reset', '-q', '--hard', 'origin/main')
    commit_file(stack.peer, 'm.txt', 'trunk\n')
    git(stack.peer, 'push', '-q', 'origin', 'main')
    git(stack.peer, 'switch', '-q', 'layer-b')
    git(stack.peer, 'reset', '-q', '--hard', 'origin/layer-b')
    git(stack.peer, 'rebase', '-q', 'main')
    for command in remote_only:
        git(stack.peer, *command)
    git(stack.peer, 'push', '-q', '--force', 'origin', 'layer-b')


def test_begin_stops_on_a_reapplied_commit_on_a_rebased_layer(
    plugin_root: Path, stack: Stack
) -> None:
    """A reapply shares its original's patch-id; each local commit matches only once."""
    commit_file(stack.work, 'x.txt', 'x\n')
    git(stack.work, 'revert', '--no-edit', 'HEAD')
    git(stack.work, 'push', '-q', 'origin', 'layer-b')
    github_rebase_layer_b(
        stack, ['revert', '--no-edit', 'HEAD'], ['commit', '-q', '--amend', '-m', 'Reapply X']
    )

    completed, _ = guard(plugin_root, stack, 'begin')

    assert outcome(completed) == (3, 'RESULT=REMOTE_ONLY_COMMITS')
    assert 'Reapply X' in completed.stderr


def test_begin_accepts_a_rebased_layer_with_an_empty_commit(
    plugin_root: Path, stack: Stack
) -> None:
    """An empty commit on both sides has no patch-id but still matches by count."""
    git(stack.work, 'commit', '-q', '--allow-empty', '-m', 'retrigger CI')
    git(stack.work, 'push', '-q', 'origin', 'layer-b')
    github_rebase_layer_b(stack)

    completed, _ = guard(plugin_root, stack, 'begin')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')


def test_begin_stops_on_an_empty_commit_only_on_the_remote(
    plugin_root: Path, stack: Stack
) -> None:
    """An empty commit the local branch lacks is remote work like any other."""
    github_rebase_layer_b(stack, ['commit', '-q', '--allow-empty', '-m', 'retrigger CI'])

    completed, _ = guard(plugin_root, stack, 'begin')

    assert outcome(completed) == (3, 'RESULT=REMOTE_ONLY_COMMITS')
    assert 'retrigger CI' in completed.stderr


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
    assert stack.links() == []


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
    assert stack.links() == []
    assert stack.remote_tip('layer-b') == remote_before


def test_publish_stops_when_a_remote_moved_after_begin(plugin_root: Path, stack: Stack) -> None:
    """A push to a layer during the edit stops publish before anything is pushed."""
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    commit_file(stack.work, 'l.txt', 'local\n')
    remote_sha = stack.peer_commit('layer-b', 'R-fix')

    completed, _ = guard(plugin_root, stack, 'publish')

    assert outcome(completed) == (4, 'RESULT=REMOTE_MOVED')
    assert 'layer-b' in completed.stderr
    assert stack.links() == []
    assert stack.remote_tip('layer-b') == remote_sha


def test_publish_reports_a_push_that_left_a_layer_behind(plugin_root: Path, stack: Stack) -> None:
    """A remote tip that differs from the local one after the push is not published."""
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    commit_file(stack.work, 'l.txt', 'local\n')
    stack.race_peer_push('layer-b', 'R-late', 'before-link')
    stack.set_link_mode('noop')
    (stack.stub / 'stack-number').write_text('7\n')

    completed, _ = guard(plugin_root, stack, 'publish', '--submit')

    assert outcome(completed) == (6, 'RESULT=PUSH_INCOMPLETE')
    assert 'layer-b' in completed.stderr


def test_publish_reports_a_failed_link(plugin_root: Path, stack: Stack) -> None:
    """A failing gh stack link surfaces as PUSH_FAILED."""
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    stack.set_link_mode('fail')

    completed, _ = guard(plugin_root, stack, 'publish', '--submit')

    assert outcome(completed) == (5, 'RESULT=PUSH_FAILED')


def test_publish_rerun_after_a_failed_link_completes(plugin_root: Path, stack: Stack) -> None:
    """Layers the failed publish already pushed are not mistaken for a foreign move."""
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    git(stack.work, 'switch', '-q', 'layer-a')
    commit_file(stack.work, 'a2.txt', 'a2\n')
    git(stack.work, 'rebase', '-q', 'layer-a', 'layer-b')
    stack.set_link_mode('fail')
    published = guard(plugin_root, stack, 'publish', '--submit')[0]
    assert outcome(published) == (5, 'RESULT=PUSH_FAILED')
    assert stack.remote_tip('layer-a') == git(stack.work, 'rev-parse', 'layer-a')
    stack.set_link_mode('real')

    completed, _ = guard(plugin_root, stack, 'publish', '--submit')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    for layer in ('layer-a', 'layer-b'):
        assert stack.remote_tip(layer) == git(stack.work, 'rev-parse', layer)


def test_publish_submit_keeps_a_push_that_lands_before_link(
    plugin_root: Path, stack: Stack
) -> None:
    """Link never force-pushes, so a push landing just before it survives."""
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    commit_file(stack.work, 'l.txt', 'local\n')
    stack.race_peer_push('layer-b', 'R-race', 'before-link')

    completed, _ = guard(plugin_root, stack, 'publish', '--submit')

    assert outcome(completed) == (5, 'RESULT=PUSH_FAILED')
    assert stack.remote_tip('layer-b') == git(stack.peer, 'rev-parse', 'HEAD')
    assert 'R-race' in stack.remote_log('layer-b')


def test_publish_stops_on_a_push_between_listing_and_fetching(
    plugin_root: Path, stack: Stack
) -> None:
    """The tip publish checks is the one it fetched, so a push right after ls-remote is seen."""
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    stack.race_peer_push('layer-b', 'R-race', 'after-ls-remote')

    completed, _ = guard(plugin_root, stack, 'publish')

    assert outcome(completed) == (4, 'RESULT=REMOTE_MOVED')
    assert 'R-race' in stack.remote_log('layer-b')


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
    assert stack.links() == []


def test_publish_stops_on_a_push_to_a_queued_layer(plugin_root: Path, stack: Stack) -> None:
    """A queued layer is guarded like any other: a push to it during the edit stops publish."""
    stack.queued.add('layer-a')
    stack.write_stack()
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    remote_sha = stack.peer_commit('layer-a', 'R-fix')

    completed, _ = guard(plugin_root, stack, 'publish')

    assert outcome(completed) == (4, 'RESULT=REMOTE_MOVED')
    assert 'layer-a' in completed.stderr
    assert stack.remote_tip('layer-a') == remote_sha


def test_publish_leaves_a_still_queued_layer_alone(plugin_root: Path, stack: Stack) -> None:
    """A layer still queued is not pushed, and publishing the layers above it succeeds."""
    stack.queued.add('layer-a')
    stack.write_stack()
    queued_sha = stack.remote_tip('layer-a')
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    git(stack.work, 'switch', '-q', 'layer-a')
    commit_file(stack.work, 'a2.txt', 'a2\n')
    git(stack.work, 'rebase', '-q', 'layer-a', 'layer-b')

    completed, _ = guard(plugin_root, stack, 'publish')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert 'layer-a' in completed.stderr
    assert stack.remote_tip('layer-a') == queued_sha
    assert stack.remote_tip('layer-b') == git(stack.work, 'rev-parse', 'layer-b')
    assert outcome(guard(plugin_root, stack, 'publish')[0]) == (0, 'RESULT=SUCCESS')


def test_publish_submit_links_the_layers_bottom_to_top(plugin_root: Path, stack: Stack) -> None:
    """--submit pushes through the guard, then links every layer with gh stack link."""
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    commit_file(stack.work, 'l.txt', 'local\n')

    completed, _ = guard(plugin_root, stack, 'publish', '--submit')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert stack.links() == ['stack link --remote origin --base main layer-a layer-b']
    assert stack.remote_tip('layer-b') == git(stack.work, 'rev-parse', 'layer-b')


def test_publish_submit_links_a_queued_layer_by_its_pr(plugin_root: Path, stack: Stack) -> None:
    """A queued layer stays in the link by PR URL, so link neither pushes nor drops it."""
    stack.queued.add('layer-a')
    stack.write_stack()
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    commit_file(stack.work, 'l.txt', 'local\n')

    completed, _ = guard(plugin_root, stack, 'publish', '--submit')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert stack.links() == [f'stack link --remote origin --base main {pr_url(1)} layer-b']


def merge_layer_a_and_add_layer_c(stack: Stack) -> None:
    """Squash-merge layer-a, refresh layer-b locally, and add layer-c on top without a PR."""
    stack.squash_merge_layer_a()
    git(stack.work, 'fetch', '-q', 'origin')
    git(stack.work, 'reset', '-q', '--hard', 'origin/layer-b')
    git(stack.work, 'switch', '-q', '-c', 'layer-c')
    commit_file(stack.work, 'c.txt', 'c\n')
    stack.without_pr.add('layer-c')
    stack.write_stack(('layer-a', 'layer-b', 'layer-c'))
    (stack.stub / 'stack-number').write_text('7\n')


def test_publish_submit_appends_a_new_layer_to_the_github_stack(
    plugin_root: Path, stack: Stack
) -> None:
    """After a lower layer merged, a new top layer is appended in link's add mode."""
    merge_layer_a_and_add_layer_c(stack)
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')

    completed, _ = guard(plugin_root, stack, 'publish', '--submit')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert stack.links() == ['stack link --remote origin 7 layer-c']
    assert stack.remote_tip('layer-c') == git(stack.work, 'rev-parse', 'layer-c')
    assert stack.view()['branches'][2]['pr']['number'] == 3


def test_publish_submit_records_new_prs_so_the_next_run_appends(
    plugin_root: Path, stack: Stack
) -> None:
    """Link records nothing locally; checkout does, so a later --submit sees the PRs."""
    stack.without_pr.update(('layer-a', 'layer-b'))
    stack.write_stack()
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')

    completed, _ = guard(plugin_root, stack, 'publish', '--submit')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert [b['pr']['number'] for b in stack.view()['branches']] == [1, 2]
    assert git(stack.work, 'branch', '--show-current') == 'layer-b'
    stack.squash_merge_layer_a(describe=False)
    git(stack.work, 'fetch', '-q', 'origin')
    git(stack.work, 'reset', '-q', '--hard', 'origin/layer-b')
    git(stack.work, 'switch', '-q', '-c', 'layer-c')
    commit_file(stack.work, 'c.txt', 'c\n')
    view = stack.view()
    view['branches'][0]['isMerged'] = True
    view['branches'].append({'name': 'layer-c', 'isMerged': False, 'isQueued': False})
    (stack.stub / 'stack.json').write_text(json.dumps(view))
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')

    completed, _ = guard(plugin_root, stack, 'publish', '--submit')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert stack.links()[-1] == 'stack link --remote origin 7 layer-c'
    assert stack.view()['branches'][2]['pr']['number'] == 3
    assert git(stack.work, 'branch', '--show-current') == 'layer-c'


def test_publish_submit_reports_prs_it_could_not_record(plugin_root: Path, stack: Stack) -> None:
    """A failed checkout after the link names the recovery instead of claiming success."""
    stack.without_pr.update(('layer-a', 'layer-b'))
    stack.write_stack()
    (stack.stub / 'checkout-mode').write_text('fail')
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')

    completed, _ = guard(plugin_root, stack, 'publish', '--submit')

    assert outcome(completed) == (5, 'RESULT=PUSH_FAILED')
    assert 'gh stack checkout 7' in completed.stderr
    assert git(stack.work, 'branch', '--show-current') == 'layer-b'


def test_publish_submit_skips_link_when_every_layer_has_a_pr(
    plugin_root: Path, stack: Stack
) -> None:
    """With a merged layer and no new layer, the push already updated every PR."""
    merge_layer_a_and_add_layer_c(stack)
    stack.without_pr.clear()
    stack.write_stack(('layer-a', 'layer-b', 'layer-c'))
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')

    completed, _ = guard(plugin_root, stack, 'publish', '--submit')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert stack.links() == []
    assert stack.remote_tip('layer-c') == git(stack.work, 'rev-parse', 'layer-c')


def test_publish_submit_refuses_a_new_layer_below_a_linked_one(
    plugin_root: Path, stack: Stack
) -> None:
    """Add mode only appends, so a PR-less layer under a layer with a PR stops --submit."""
    stack.without_pr.add('layer-a')
    stack.write_stack()
    (stack.stub / 'stack-number').write_text('7\n')
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')
    commit_file(stack.work, 'l.txt', 'local\n')
    remote_before = stack.remote_tip('layer-b')

    completed, _ = guard(plugin_root, stack, 'publish', '--submit')

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert 'layer-a' in completed.stderr
    assert stack.links() == []
    assert stack.remote_tip('layer-b') == remote_before


def test_publish_submit_stops_when_the_stack_lookup_fails(plugin_root: Path, stack: Stack) -> None:
    """A failed stack-number lookup stops --submit before anything is pushed."""
    merge_layer_a_and_add_layer_c(stack)
    (stack.stub / 'api-mode').write_text('fail')
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')

    completed, _ = guard(plugin_root, stack, 'publish', '--submit')

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert stack.links() == []
    assert git(stack.remote, 'branch', '--list', 'layer-c') == ''


def test_publish_submit_opens_a_new_github_stack(plugin_root: Path, stack: Stack) -> None:
    """With no PR yet, link creates the PRs and the stack from every layer."""
    stack.without_pr.update(('layer-a', 'layer-b'))
    stack.write_stack()
    assert outcome(guard(plugin_root, stack, 'begin')[0]) == (0, 'RESULT=SUCCESS')

    completed, _ = guard(plugin_root, stack, 'publish', '--submit')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert stack.links() == ['stack link --remote origin --base main layer-a layer-b']


def test_publish_submit_refuses_a_numeric_layer_name(plugin_root: Path, stack: Stack) -> None:
    """Link reads a numeric argument as a PR number first, so --submit refuses it."""
    git(stack.work, 'branch', '123', 'layer-b')
    stack.write_stack(('layer-a', '123'))

    completed, _ = guard(plugin_root, stack, 'publish', '--submit')

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert '123' in completed.stderr
    assert stack.links() == []


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
