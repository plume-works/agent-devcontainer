#!/usr/bin/env python3

"""
Restack a chain of manual stacked pull requests with merges, never a rewrite.

Works in one fresh detached worktree under ``./.tmp/`` built from remote refs,
so no local branch is checked out, created, or moved. Design: see the
repository's ``openspec/specs/stacked-prs`` spec.

Standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Protocol
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parent))

import depends_on  # noqa: E402  (path set above so the plugin's bin/ resolves)
import git_default_branch  # noqa: E402
import result_codes as rc  # noqa: E402
from skill_common import (  # noqa: E402
    bash_quote,
    print_error,
    require_git_repo,
    run_tool,
    Stop,
)

PREFLIGHT_ERROR = 2
GH_FAILED = 3
CHAIN_BROKEN = 4
PREDECESSOR_CLOSED = 5
HEAD_MISMATCH = 6
MERGE_CONFLICT = 7
PUSH_REJECTED = 8
FETCH_FAILED = 9
BODY_UPDATE_FAILED = 10

USAGE = """\
Restack a chain of manual stacked pull requests with merges, never a rewrite.

Usage:
  pr_restack_all.py <top-pr> [--remote <name>] [--trunk <branch>]
  pr_restack_all.py <branch> [--remote <name>] [--trunk <branch>] [--list]

  <top-pr>          The top pull request of a chain, as <n> or #<n>. The chain
                    is walked down through each base branch to a base of the
                    trunk; each pull request is restacked onto the last entry of
                    its '## Depends on' section, bottom to top.
  <branch>          A branch, with or without a pull request; its dependencies
                    are its own 'Depends-on: #<n>' trailers, and every merged
                    one is reconnected.
  --remote <name>   Remote to fetch from and push to. Default: origin
  --trunk <branch>  The branch a chain bottoms out on. Default: the remote's
                    default branch, else main
  --list            With <branch>: print its dependencies and change nothing
  -h, --help        Show this help text.

Output (key=value lines):
  CHAIN=#<n>,...                         the chain, bottom to top
  DEPENDENCY=#<n> <STATE> <head-branch>  with --list, one per own dependency
  RECONNECTED=#<P> HEAD=<HEAD> MERGE=<MERGE>  one per reconnect
  PUSHED=<branch> <sha>                  one per branch that moved
  WORKTREE=<path>                        on MERGE_CONFLICT: resolve there

Results (RESULT / exit code):
  SUCCESS             0  Every pull request is restacked
  PREFLIGHT_ERROR     2  Bad usage or not a repository
  GH_FAILED           3  gh could not read or edit a pull request
  CHAIN_BROKEN        4  A pull request is not open, its head is in a fork, no
                         open pull request has its base as head, or its last
                         '## Depends on' entry is not the pull request below it
  PREDECESSOR_CLOSED  5  A predecessor was closed without merging
  HEAD_MISMATCH       6  refs/pull/<P>/head differs from P's recorded final head
  MERGE_CONFLICT      7  A merge conflicted; the worktree is kept at WORKTREE
  PUSH_REJECTED       8  A plain push was rejected; the branch moved, rerun
  FETCH_FAILED        9  The remote could not be fetched
  BODY_UPDATE_FAILED 10  The push landed but the merge record was not written
"""


@dataclass(frozen=True)
class PullRequest:
    """The pull request fields a restack reads."""

    number: int
    state: str
    head_branch: str
    base_branch: str
    head_oid: str
    merge_oid: str | None
    body: str
    cross_repository: bool = False


class PullRequests(Protocol):
    """The pull request metadata a restack reads and the body it edits."""

    def view(self, number: int) -> PullRequest:
        """Return pull request `number`."""

    def open_with_head(self, branch: str) -> PullRequest | None:
        """Return the open pull request whose head is `branch`, if any."""

    def edit_body(self, number: int, body: str) -> None:
        """Replace pull request `number`'s body."""


class GitHubPullRequests:
    """Pull request metadata from `gh`, scoped to the remote's repository."""

    FIELDS = 'number,state,headRefName,baseRefName,headRefOid,mergeCommit,body,isCrossRepository'

    def __init__(self, repository: str) -> None:
        self.repository = repository

    def _gh(self, *arguments: str, stdin: str | None = None) -> str:
        completed = subprocess.run(
            ['gh', *arguments, '--repo', self.repository],
            check=False, capture_output=True, text=True, input=stdin,
        )  # fmt: skip
        if completed.returncode != 0:
            print_error(f'gh {" ".join(arguments[:3])} failed: {completed.stderr.strip()}')
            raise Stop(GH_FAILED)
        return completed.stdout

    def view(self, number: int) -> PullRequest:
        """Return pull request `number`."""
        data = json.loads(self._gh('pr', 'view', str(number), '--json', self.FIELDS))
        return PullRequest(
            number=data['number'],
            state=data['state'],
            head_branch=data['headRefName'],
            base_branch=data['baseRefName'],
            head_oid=data['headRefOid'],
            merge_oid=(data.get('mergeCommit') or {}).get('oid'),
            body=data.get('body') or '',
            cross_repository=bool(data.get('isCrossRepository')),
        )

    def open_with_head(self, branch: str) -> PullRequest | None:
        """Return the open pull request whose head is `branch`, if any."""
        listing = json.loads(
            self._gh('pr', 'list', '--state', 'open', '--head', branch, '--json', 'number')
        )
        return self.view(listing[0]['number']) if listing else None

    def edit_body(self, number: int, body: str) -> None:
        """Replace pull request `number`'s body."""
        self._gh('pr', 'edit', str(number), '--body-file', '-', stdin=body)


class Git:
    """Git commands run in one directory."""

    def __init__(self, cwd: Path) -> None:
        self.cwd = cwd

    def run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        """Run git, capturing its output, without raising."""
        return run_tool('git', *arguments, cwd=self.cwd)

    def out(self, *arguments: str) -> str:
        """Return git's stripped stdout, raising when it fails."""
        completed = self.run(*arguments)
        if completed.returncode != 0:
            raise subprocess.CalledProcessError(
                completed.returncode, ['git', *arguments], completed.stdout, completed.stderr
            )
        return completed.stdout.strip()

    def is_ancestor(self, commit: str, of: str) -> bool:
        """Return whether `commit` is reachable from `of`."""
        return self.run('merge-base', '--is-ancestor', commit, of).returncode == 0


@dataclass
class Restack:
    """One restack run: the remote, its trunk, the worktree, and what was pushed."""

    prs: PullRequests
    root: Git
    remote: str
    trunk: str
    worktree: Path | None = None

    @property
    def tree(self) -> Git:
        """Return git in the detached worktree, creating it on first use."""
        if self.worktree is None:
            scratch = Path(self.root.cwd) / '.tmp'
            scratch.mkdir(exist_ok=True)
            if self.root.run('check-ignore', '--quiet', '.tmp/').returncode != 0:
                exclude = Path(self.root.out('rev-parse', '--git-path', 'info/exclude'))
                exclude = exclude if exclude.is_absolute() else Path(self.root.cwd) / exclude
                exclude.parent.mkdir(parents=True, exist_ok=True)
                with exclude.open('a') as handle:
                    handle.write('.tmp/\n')
            self.worktree = scratch / f'pr-restack-all-{uuid4().hex[:8]}'
            start = f'refs/remotes/{self.remote}/{self.trunk}'
            self.root.out('worktree', 'add', '--quiet', '--detach', str(self.worktree), start)
        return Git(self.worktree)

    def remove_worktree(self) -> None:
        """Remove the worktree after a run that left nothing to resolve."""
        if self.worktree is not None:
            self.root.run('worktree', 'remove', '--force', str(self.worktree))
            self.worktree = None

    def fetch(self, *refspecs: str) -> None:
        """Fetch from the remote, stopping when it fails."""
        completed = self.root.run('fetch', '--quiet', self.remote, *refspecs)
        if completed.returncode != 0:
            print_error(f'git fetch {self.remote} failed: {completed.stderr.strip()}')
            raise Stop(FETCH_FAILED)

    def merge(self, commit: str, message: str, branch: str, resume: str = '') -> None:
        """
        Merge `commit` into the worktree's HEAD, stopping on a conflict.

        `resume` holds the commands that turn the resolved HEAD into `branch`'s new tip.
        """
        completed = self.tree.run('merge', '--no-ff', '--no-edit', '-m', message, commit)
        if completed.returncode != 0:
            sys.stderr.write(completed.stdout + completed.stderr)
            print(f'WORKTREE={self.worktree}')
            print_error(
                f'Merging {commit} for {branch} conflicted. Resolve and commit in the '
                f'worktree, then run: {resume}git push {bash_quote(self.remote)} '
                f'{bash_quote("HEAD:refs/heads/" + branch)}'
                ' and rerun; restacked pull requests are skipped.'
            )
            raise Stop(MERGE_CONFLICT)

    def checkout(self, branch: str) -> str:
        """Detach the worktree at the remote branch and return its commit."""
        self.tree.out('checkout', '--quiet', '--detach', f'refs/remotes/{self.remote}/{branch}')
        return self.tree.out('rev-parse', 'HEAD')

    def push(self, branch: str, before: str) -> None:
        """Push the worktree's HEAD to `branch` without force when it moved."""
        after = self.tree.out('rev-parse', 'HEAD')
        if after == before:
            return
        completed = self.tree.run('push', '--quiet', self.remote, f'HEAD:refs/heads/{branch}')
        if completed.returncode != 0:
            sys.stderr.write(completed.stderr)
            print_error(f'The push to {branch} was rejected; it moved meanwhile. Rerun.')
            raise Stop(PUSH_REJECTED)
        self.tree.run('update-ref', f'refs/remotes/{self.remote}/{branch}', after)
        print(f'PUSHED={branch} {after}')

    def final_head(self, predecessor: PullRequest) -> str:
        """Fetch P's final head and require it to equal its recorded ``headRefOid``."""
        self.fetch(f'refs/pull/{predecessor.number}/head')
        fetched = self.root.out('rev-parse', 'FETCH_HEAD')
        if fetched != predecessor.head_oid:
            print_error(
                f'refs/pull/{predecessor.number}/head is {fetched}, not its recorded final '
                f'head {predecessor.head_oid}.'
            )
            raise Stop(HEAD_MISMATCH)
        return fetched

    def reconnect(self, predecessor: PullRequest, branch: str) -> bool:
        """
        Reconnect `branch`, detached in the worktree, to merged `predecessor`.

        Returns whether the branch now holds both P's final head and its merge commit.
        """
        head = self.final_head(predecessor)
        merge = predecessor.merge_oid
        if not merge:
            print_error(f'#{predecessor.number} is merged but GitHub reports no merge commit.')
            raise Stop(GH_FAILED)
        if self.tree.is_ancestor(merge, 'HEAD'):
            return self.tree.is_ancestor(head, 'HEAD')
        tip = self.tree.out('rev-parse', 'HEAD')
        self.tree.out('checkout', '--quiet', '--detach', head)
        reconnect = f'Reconnect #{predecessor.number} after its squash merge'
        self.merge(
            merge,
            f'Merge the squash commit of #{predecessor.number} into its head',
            branch,
            # The worktree now holds P's head, which is never pushed: merge it in first.
            resume=(
                f'copy=$(git rev-parse HEAD); git checkout --detach {tip}; '
                f'git merge --no-ff -m {bash_quote(reconnect)} "$copy"; '
            ),
        )
        copy = self.tree.out('rev-parse', 'HEAD')
        self.tree.out('checkout', '--quiet', '--detach', tip)
        self.merge(copy, reconnect, branch)
        print(f'RECONNECTED=#{predecessor.number} HEAD={head} MERGE={merge}')
        return True

    def write_record(self, number: int, predecessor: PullRequest) -> None:
        """Replace P's entry in pull request `number`'s body with its merge record."""
        body = self.prs.view(number).body
        entry = next(
            (item for item in depends_on.entries(body) if item.number == predecessor.number),
            None,
        )
        if entry is None or entry.merge is not None:
            return
        short = lambda commit: self.root.out('rev-parse', '--short=8', commit)  # noqa: E731
        try:
            edited = depends_on.record_merge(
                body, predecessor.number, short(predecessor.merge_oid), short(predecessor.head_oid)
            )
            self.prs.edit_body(number, edited)
        except (depends_on.DependsOnError, Stop) as failure:
            print_error(f'The merge record of #{predecessor.number} was not written: {failure}')
            raise Stop(BODY_UPDATE_FAILED) from failure

    def require_predecessor(self, number: int, of: str) -> PullRequest:
        """Return predecessor `number`, stopping when it was closed without merging."""
        predecessor = self.prs.view(number)
        if predecessor.state == 'CLOSED':
            print_error(f'#{number}, a predecessor of {of}, was closed without merging.')
            raise Stop(PREDECESSOR_CLOSED)
        return predecessor

    def require_same_repository(self, pull_request: PullRequest) -> None:
        """Stop for a pull request whose head branch lives in a fork, not on the remote."""
        if pull_request.cross_repository:
            print_error(
                f"#{pull_request.number}'s head {pull_request.head_branch} is in a fork; "
                f'only branches of {self.remote} are restacked.'
            )
            raise Stop(CHAIN_BROKEN)

    def restack_pull_request(self, pull_request: PullRequest) -> None:
        """Restack one pull request onto the last entry of its ``## Depends on``."""
        entries = depends_on.entries(pull_request.body)
        if not entries:
            return
        predecessor = self.require_predecessor(entries[-1].number, f'#{pull_request.number}')
        if predecessor.state == 'OPEN' and pull_request.base_branch != predecessor.head_branch:
            print_error(
                f'#{pull_request.number} depends on open #{predecessor.number} but is based on '
                f'{pull_request.base_branch}, not {predecessor.head_branch}.'
            )
            raise Stop(CHAIN_BROKEN)
        self.require_same_repository(pull_request)
        if predecessor.state == 'OPEN':
            self.require_same_repository(predecessor)
        branch = pull_request.head_branch
        before = self.checkout(branch)
        if predecessor.state == 'OPEN':
            self.merge(
                f'refs/remotes/{self.remote}/{predecessor.head_branch}',
                f'Merge #{predecessor.number} into #{pull_request.number}',
                branch,
            )
            self.push(branch, before)
            return
        reconnected = self.reconnect(predecessor, branch)
        self.push(branch, before)
        if reconnected:
            self.write_record(pull_request.number, predecessor)

    def chain(self, top: int) -> list[PullRequest]:
        """Walk from the top pull request down to a base of the trunk; return bottom first."""
        links = [self.prs.view(top)]
        if links[0].state != 'OPEN':
            print_error(f'#{top} is {links[0].state}, not open.')
            raise Stop(CHAIN_BROKEN)
        self.require_same_repository(links[0])
        while links[-1].base_branch != self.trunk:
            upper = links[-1]
            lower = self.prs.open_with_head(upper.base_branch)
            if lower is None:
                print_error(
                    f"No open pull request has #{upper.number}'s base {upper.base_branch}."
                )
                raise Stop(CHAIN_BROKEN)
            self.require_same_repository(lower)
            entries = depends_on.entries(upper.body)
            if not entries or entries[-1].number != lower.number:
                print_error(
                    f"#{upper.number}'s last '## Depends on' entry is not #{lower.number}, "
                    'the pull request below it.'
                )
                raise Stop(CHAIN_BROKEN)
            if any(link.number == lower.number for link in links):
                print_error(f'The chain loops back to #{lower.number}.')
                raise Stop(CHAIN_BROKEN)
            links.append(lower)
        return list(reversed(links))

    def restack_chain(self, top: int) -> None:
        """Restack every pull request of the chain under `top`, bottom to top."""
        self.fetch()
        links = self.chain(top)
        print(f'CHAIN={",".join(f"#{link.number}" for link in links)}')
        for link in links:
            # Re-read the body: a lower restack may not change it, but an owner may have.
            self.restack_pull_request(self.prs.view(link.number))

    def own_dependencies(self, branch: str) -> list[PullRequest]:
        """
        Return the pull requests `branch`'s own trailers name, oldest first.

        Trailers carried in from a predecessor's branch are dropped: they are
        reachable from that predecessor's final head.
        """
        ref = f'refs/remotes/{self.remote}/{branch}'
        named = [
            self.prs.view(number) for number in depends_on.read_trailers(ref, cwd=self.root.cwd)
        ]
        for predecessor in named:
            self.fetch(f'refs/pull/{predecessor.number}/head')
        heads = [predecessor.head_oid for predecessor in named]
        own = depends_on.read_trailers(ref, *heads, cwd=self.root.cwd)
        return [predecessor for predecessor in named if predecessor.number in own]

    def restack_branch(self, branch: str, list_only: bool) -> None:
        """Reconnect every merged dependency `branch`'s own trailers name."""
        self.fetch()
        if not self.root.run(
            'rev-parse', '--verify', '--quiet', f'refs/remotes/{self.remote}/{branch}'
        ).stdout:
            print_error(f"'{self.remote}/{branch}' does not exist.")
            raise Stop(PREFLIGHT_ERROR)
        dependencies = self.own_dependencies(branch)
        if list_only:
            for predecessor in dependencies:
                print(
                    f'DEPENDENCY=#{predecessor.number} {predecessor.state} {predecessor.head_branch}'
                )
            return
        before = self.checkout(branch)
        reconnected = []
        for predecessor in dependencies:
            self.require_predecessor(predecessor.number, branch)
            if predecessor.state == 'MERGED' and self.reconnect(predecessor, branch):
                reconnected.append(predecessor)
        self.push(branch, before)
        pull_request = self.prs.open_with_head(branch) if reconnected else None
        for predecessor in reconnected if pull_request else []:
            self.write_record(pull_request.number, predecessor)


_PULL_REQUEST = re.compile(r'#?([0-9]+)')


def run(arguments: list[str], prs: PullRequests | None = None) -> int:
    """Parse the command line and run the restack."""
    target = ''
    remote = 'origin'
    trunk = ''
    list_only = False
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument in ('-h', '--help'):
            print(USAGE, end='')
            return 0
        if argument in ('--remote', '--trunk'):
            if not remaining:
                print_error(f'Missing value for {argument}')
                return PREFLIGHT_ERROR
            value = remaining.pop(0)
            remote, trunk = (value, trunk) if argument == '--remote' else (remote, value)
        elif argument == '--list':
            list_only = True
        elif argument.startswith('-') or target:
            print_error(f'Unexpected argument: {argument}')
            print(USAGE, end='', file=sys.stderr)
            return PREFLIGHT_ERROR
        else:
            target = argument
    if not target:
        print_error('Missing the top pull request or branch.')
        print(USAGE, end='', file=sys.stderr)
        return PREFLIGHT_ERROR
    number = _PULL_REQUEST.fullmatch(target)
    if number and list_only:
        print_error('--list takes a branch, not a pull request.')
        return PREFLIGHT_ERROR
    root = Git(require_git_repo())
    trunk = trunk or git_default_branch.remote_default_branch(remote) or 'main'
    if prs is None:
        prs = GitHubPullRequests(root.out('remote', 'get-url', remote))
    restack = Restack(prs, root, remote, trunk)
    try:
        if number:
            restack.restack_chain(int(number.group(1)))
        else:
            restack.restack_branch(target, list_only)
    except Stop as stop:
        if stop.code != MERGE_CONFLICT:
            restack.remove_worktree()
        raise
    restack.remove_worktree()
    return 0


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES.update(
        {
            GH_FAILED: 'GH_FAILED',
            CHAIN_BROKEN: 'CHAIN_BROKEN',
            PREDECESSOR_CLOSED: 'PREDECESSOR_CLOSED',
            HEAD_MISMATCH: 'HEAD_MISMATCH',
            MERGE_CONFLICT: 'MERGE_CONFLICT',
            PUSH_REJECTED: 'PUSH_REJECTED',
            FETCH_FAILED: 'FETCH_FAILED',
            BODY_UPDATE_FAILED: 'BODY_UPDATE_FAILED',
        }
    )
    rc.install()
    rc.run(main)
