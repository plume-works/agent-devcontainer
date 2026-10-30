#!/usr/bin/env python3

"""
Guard every update of a GitHub stack's remote branches against dropping remote-only commits.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import result_codes as rc  # noqa: E402  (path set above so the plugin's bin/ resolves)
from skill_common import (  # noqa: E402
    print_error,
    run_inherited,
    run_to_stderr,
    run_tool,
    skill_root,
    Stop,
)

REMOTE_ONLY_COMMITS = 3
REMOTE_MOVED = 4
PUSH_FAILED = 5
PUSH_INCOMPLETE = 6
PREFLIGHT_ERROR = 2

USAGE = """\
Guard every update of a GitHub stack's remote branches against dropping commits
that exist only on a layer's remote.

Skill root: {skill_root}

Usage:
  stack-guard.py begin [--remote <name>]
  stack-guard.py publish [--submit] [--remote <name>]

Subcommands:
  begin     Run before anything rewrites the stack. Fetches every unmerged layer,
            queued ones included, fast-forwards a layer its remote is ahead of,
            stops on a layer whose remote holds a commit the local branch has no
            identical patch for (each local commit matching one remote commit)
            or a merge it lacks, and records every layer's
            remote tip.
  publish   Run in place of gh stack push (or, with --submit, of
            gh stack submit --auto). Stops when a layer's remote tip moved since
            begin to anything but its local tip, then pushes every changed layer
            in one atomic push leased on the tips it checked; this is the only
            force-push. --submit then runs gh stack link, which pushes without
            force and opens the missing draft PRs: create mode for a stack with
            no merged layer, add mode (link <stack#> <new layers>) to append
            PR-less top layers once one has merged, and no link when every
            layer has a PR and one has merged. After a link it runs
            gh stack checkout <stack#> to record the PRs locally, keeping the
            current branch. Finally verifies every remote
            tip equals its local tip. A layer still in the merge queue is never
            pushed and is noted on stderr.
            Without a begin record, applies begin's remote-only test instead.

Options:
  --remote <name>  Remote of the stack. Default: remote.pushDefault, else origin
  --submit         publish only: also open and link the PRs with gh stack link;
                   refused for a PR-less layer below one with a PR, an
                   all-digit layer name, or a failed stack-number lookup
  -h, --help       Show this help text.

Output (key=value lines):
  RESULT, STATE_FILE
  begin also: FAST_FORWARDED=<layer> for each layer it moved; run
  gh stack rebase --upstack from the lowest of them before editing further
  On REMOTE_ONLY_COMMITS and REMOTE_MOVED, stderr names the layer and commits

Results (RESULT / exit code):
  SUCCESS              0  Nothing on any remote would be or was lost
  REMOTE_ONLY_COMMITS  3  A layer's remote holds commits the local branch lacks;
                          nothing was changed
  REMOTE_MOVED         4  publish: a layer's remote tip changed since begin or
                          after the check; nothing was pushed
  PUSH_FAILED          5  publish: the guard's push, gh stack link, or recording
                          the linked PRs locally failed
  PUSH_INCOMPLETE      6  publish: the push exited 0 but a remote tip still
                          differs from its local tip
  PREFLIGHT_ERROR      2  Bad usage, not a repo, not in a stack, detached HEAD,
                          fetch failure, a layer that cannot be fast-forwarded,
                          or a stack --submit cannot link
  SCRIPT_FAILURE       1  Unhandled error
  SIGNAL_HUP         129  Interrupted by HUP
  SIGNAL_INT         130  Interrupted by INT
  SIGNAL_TERM        143  Interrupted by TERM

Examples:
  agent-code/stack-guard.py begin
  agent-code/stack-guard.py publish
  agent-code/stack-guard.py publish --submit
"""


def usage() -> str:
    """Return the full help text."""
    return USAGE.format(skill_root=skill_root(__file__))


def git_out(*arguments: str) -> str:
    """Return a git command's stripped stdout, whatever its status."""
    return run_tool('git', *arguments).stdout.strip()


def verify(ref: str) -> str:
    """Return the commit `ref` names, or '' when it names none."""
    completed = run_tool('git', 'rev-parse', '-q', '--verify', ref)
    return completed.stdout.strip() if completed.returncode == 0 else ''


def gh_out(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run gh with stdout captured and stderr passed through."""
    sys.stdout.flush()
    return subprocess.run(['gh', *arguments], check=False, stdout=subprocess.PIPE, text=True)


def jq_text(value: Any) -> str:
    """Return a JSON value as `jq -r ... // empty` prints it."""
    if value is None or value is False:
        return ''
    return value if isinstance(value, str) else json.dumps(value)


class Guard:
    """One begin or publish run over the stack the current branch belongs to."""

    def __init__(self, remote: str, submit: bool) -> None:
        self.remote = remote
        self.submit = submit
        self.trunk = ''
        self.layers: list[str] = []
        self.queued: set[str] = set()
        self.branches: list[dict[str, Any]] = []
        self.state_file = Path()
        # Tip of each branch on the remote, as fetched. ls-remote only says which branches
        # exist, so the checks, the record, and the lease all use the very SHA examined.
        self.remote_tip: dict[str, str] = {}
        self.link_args: list[str] = []
        self.stack_number = ''

    def load_stack(self) -> None:
        """Read the stack from gh stack view and print where its state is recorded."""
        root = run_tool('git', 'rev-parse', '--show-toplevel')
        if root.returncode != 0:
            print_error('This script must be run inside a Git repository.')
            raise Stop(PREFLIGHT_ERROR)
        if run_tool('git', 'symbolic-ref', '-q', 'HEAD').returncode != 0:
            print_error('HEAD is detached; check out a stack branch first.')
            raise Stop(PREFLIGHT_ERROR)
        if not self.remote:
            push_default = run_tool('git', 'config', '--get', 'remote.pushDefault')
            self.remote = push_default.stdout.strip() if push_default.returncode == 0 else 'origin'
        if run_tool('git', 'remote', 'get-url', self.remote).returncode != 0:
            print_error(f'No remote named {self.remote}.')
            raise Stop(PREFLIGHT_ERROR)
        view = run_tool('gh', 'stack', 'view', '--json')
        if view.returncode != 0:
            print_error('The current branch is not in a gh stack (gh stack view --json failed).')
            raise Stop(PREFLIGHT_ERROR)
        stack = json.loads(view.stdout)
        self.trunk = jq_text(stack.get('trunk'))
        self.branches = stack.get('branches') or []
        unmerged = [branch for branch in self.branches if not branch.get('isMerged')]
        self.layers = [branch['name'] for branch in unmerged]
        # Queued layers are checked and recorded like any other, but never pushed.
        self.queued = {branch['name'] for branch in unmerged if branch.get('isQueued')}
        if not self.trunk:
            print_error('gh stack view --json reported no trunk.')
            raise Stop(PREFLIGHT_ERROR)
        self.state_file = Path(root.stdout.strip()) / '.tmp' / 'gh-stack-guard' / 'tips'
        print(f'STATE_FILE={self.state_file}')

    def fetch_layers(self) -> None:
        """Fetch the trunk and every layer present on the remote, recording their tips."""
        sys.stdout.flush()
        listing = subprocess.run(
            ['git', 'ls-remote', '--heads', self.remote],
            check=False,
            stdout=subprocess.PIPE,
            text=True,
        )
        if listing.returncode != 0:
            print_error(f'Could not list branches on {self.remote}.')
            raise Stop(PREFLIGHT_ERROR)
        on_remote = {
            fields[1].removeprefix('refs/heads/')
            for fields in (line.split() for line in listing.stdout.splitlines())
            if len(fields) > 1
        }
        present = [branch for branch in [self.trunk, *self.layers] if branch in on_remote]
        if present:
            refspecs = [f'+refs/heads/{b}:refs/remotes/{self.remote}/{b}' for b in present]
            if run_inherited('git', 'fetch', '--quiet', self.remote, *refspecs):
                print_error(f'Could not fetch the stack from {self.remote}.')
                raise Stop(PREFLIGHT_ERROR)
        self.remote_tip = {
            branch: git_out('rev-parse', '--verify', f'refs/remotes/{self.remote}/{branch}')
            for branch in present
        }

    def side_patch_keys(self, *arguments: str) -> list[tuple[str, str]]:
        """
        Return (key, commit), oldest first, for the non-merge commits of one side.

        The key is the verbatim patch-id (the default ignores whitespace), or "empty"
        for an empty diff.
        """
        log = run_tool(
            'git', 'log', '-p', '--no-merges', '--no-color', '--no-ext-diff',
            '--format=commit %H', *arguments,
        )  # fmt: skip
        patch_ids = subprocess.run(
            ['git', 'patch-id', '--verbatim'],
            check=False,
            input=log.stdout,
            capture_output=True,
            text=True,
        )
        ids = {}
        for line in patch_ids.stdout.splitlines():
            patch_id, _, sha = line.partition(' ')
            ids[sha] = patch_id
        commits = git_out('rev-list', '--reverse', '--no-merges', *arguments).split()
        return [(ids.get(sha, 'empty'), sha) for sha in commits]

    def remote_only_commits(self, layer: str) -> list[str]:
        """
        Return the layer's remote commits outside the trunk that the local branch lacks.

        Each local commit matches one remote commit of the same key, oldest first, so the
        surplus is reported; plus every remote-only merge.
        """
        trunk_ref = f'refs/remotes/{self.remote}/{self.trunk}'
        exclude = [f'^{trunk_ref}'] if verify(trunk_ref) else []
        span = f'refs/heads/{layer}...refs/remotes/{self.remote}/{layer}'
        local_count = Counter(
            key for key, _ in self.side_patch_keys('--left-only', span, *exclude)
        )
        surplus = []
        for key, sha in self.side_patch_keys('--right-only', span, *exclude):
            if local_count[key] > 0:
                local_count[key] -= 1
            else:
                surplus.append(sha)
        merges = git_out('rev-list', '--right-only', '--merges', span, *exclude).split()
        return surplus + merges

    def report_remote_only(self, layer: str, commits: list[str]) -> None:
        """Name the layer and the remote commits it would lose."""
        print_error(f'{layer} on {self.remote} holds commits the local branch lacks:')
        run_to_stderr('git', 'log', '--no-walk', '--format=  %h %s', *commits)

    def classify_layer(self, layer: str) -> str:
        """
        Return absent, behind, equal, ahead, rewritten, or diverged for one layer.

        rewritten: the histories split, but the remote holds no patch the local branch lacks.
        """
        remote_sha = self.remote_tip.get(layer, '')
        if not remote_sha:
            return 'absent'
        local_sha = verify(f'refs/heads/{layer}')
        if not local_sha:
            return 'behind'
        if local_sha == remote_sha:
            return 'equal'
        if run_tool('git', 'merge-base', '--is-ancestor', local_sha, remote_sha).returncode == 0:
            return 'behind'
        if run_tool('git', 'merge-base', '--is-ancestor', remote_sha, local_sha).returncode == 0:
            return 'ahead'
        return 'diverged' if self.remote_only_commits(layer) else 'rewritten'

    def check_layers(self, allow_behind: bool, layers: list[str]) -> list[str]:
        """
        Stop with REMOTE_ONLY_COMMITS when a layer would lose remote work.

        Returns the layers its remote is ahead of when `allow_behind`; otherwise those
        count as losses too.
        """
        behind, stop = [], False
        for layer in layers:
            kind = self.classify_layer(layer)
            if kind == 'behind' and allow_behind:
                behind.append(layer)
            elif kind == 'behind':
                commits = git_out(
                    'rev-list', f'refs/heads/{layer}..refs/remotes/{self.remote}/{layer}'
                ).split()
                self.report_remote_only(layer, commits)
                stop = True
            elif kind == 'diverged':
                self.report_remote_only(layer, self.remote_only_commits(layer))
                stop = True
        if stop:
            raise Stop(REMOTE_ONLY_COMMITS)
        return behind

    @staticmethod
    def worktree_of(layer: str) -> str:
        """Return the worktree that has `layer` checked out, or ''."""
        path = ''
        for line in git_out('worktree', 'list', '--porcelain').splitlines():
            if line.startswith('worktree '):
                path = line.removeprefix('worktree ')
            elif line == f'branch refs/heads/{layer}':
                return path
        return ''

    def fast_forward(self, layer: str) -> None:
        """Move the local layer to its remote tip, in its worktree when it has one."""
        target = f'refs/remotes/{self.remote}/{layer}'
        old = verify(f'refs/heads/{layer}')
        path = self.worktree_of(layer)
        if path:
            if run_inherited('git', '-C', path, 'merge', '--quiet', '--ff-only', target):
                print_error(
                    f'Could not fast-forward {layer} in {path}; commit or stash its changes.'
                )
                raise Stop(PREFLIGHT_ERROR)
        else:
            status = run_inherited(
                'git', 'update-ref', f'refs/heads/{layer}', target, *([old] if old else [])
            )
            if status:
                raise Stop(status)
        print(f'FAST_FORWARDED={layer}')

    def exclude_state_dir(self) -> None:
        """Ignore .tmp/, since an untracked one makes gh stack rebase refuse the worktree."""
        if run_tool('git', 'check-ignore', '--quiet', str(self.state_file)).returncode == 0:
            return
        common_dir = git_out('rev-parse', '--path-format=absolute', '--git-common-dir')
        exclude_file = Path(common_dir) / 'info' / 'exclude'
        exclude_file.parent.mkdir(parents=True, exist_ok=True)
        existing = exclude_file.read_bytes() if exclude_file.exists() else b''
        with exclude_file.open('ab') as exclude:
            if existing and not existing.endswith(b'\n'):
                exclude.write(b'\n')
            exclude.write(b'.tmp/\n')

    def write_state(self) -> None:
        """Record every layer's remote tip, or '-' for a layer absent from the remote."""
        self.exclude_state_dir()
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(
            ''.join(f'{layer} {self.remote_tip.get(layer) or "-"}\n' for layer in self.layers)
        )

    def push_layers(self) -> None:
        """
        Push every changed layer in one atomic push leased on the tips publish checked.

        The only force-push: a push landing after the check is refused, not overwritten.
        """
        leases, refspecs = [], []
        for layer in self.layers:
            local_sha = verify(f'refs/heads/{layer}')
            if not local_sha or local_sha == self.remote_tip.get(layer, ''):
                continue
            # Pushing would take the layer out of the merge queue.
            if layer in self.queued:
                print(f'NOTE: {layer} is queued; leaving it unpushed.', file=sys.stderr)
                continue
            leases.append(
                f'--force-with-lease=refs/heads/{layer}:{self.remote_tip.get(layer, "")}'
            )
            refspecs.append(f'refs/heads/{layer}:refs/heads/{layer}')
        if not refspecs:
            return
        sys.stdout.flush()
        pushed = subprocess.run(
            ['git', 'push', '--atomic', '--porcelain', *leases, self.remote, *refspecs],
            check=False,
            stdout=subprocess.PIPE,
            text=True,
        )
        if pushed.returncode == 0:
            return
        moved = False
        for line in pushed.stdout.rstrip('\n').split('\n'):
            flag, _, rest = line.strip('\t').partition('\t')
            ref, _, summary = rest.partition('\t')
            if flag != '!' or '(stale info)' not in summary:
                continue
            ref = ref.split(':', 1)[0].removeprefix('refs/heads/')
            print_error(f'{ref} on {self.remote} moved after the check; nothing was pushed.')
            moved = True
        if moved:
            raise Stop(REMOTE_MOVED)
        sys.stderr.write(pushed.stdout.rstrip('\n') + '\n')
        print_error(f'Pushing the stack to {self.remote} failed.')
        raise Stop(PUSH_FAILED)

    def pr_of(self, name: str, field: str) -> str:
        """Return a layer's PR field as text, or '' when it has no PR."""
        return ''.join(
            jq_text((branch.get('pr') or {}).get(field))
            for branch in self.branches
            if branch.get('name') == name
        )

    def plan_link(self) -> None:
        """
        Choose the gh stack link call before anything is pushed.

        None when every layer has a PR and one has merged, add mode to append PR-less top
        layers, else create mode. Policy: see architecture/stack-push-guard.
        """
        merged = sum(1 for branch in self.branches if branch.get('isMerged'))
        numbers = [
            jq_text((branch.get('pr') or {}).get('number'))
            for branch in self.branches
            if jq_text((branch.get('pr') or {}).get('number'))
        ]
        number = numbers[-1] if numbers else ''
        new: list[str] = []
        for layer in self.layers:
            if not self.pr_of(layer, 'number'):
                if layer in self.queued:
                    print_error(f'Queued layer {layer} has no PR to link.')
                    raise Stop(PREFLIGHT_ERROR)
                new.append(layer)
            elif new:
                print_error(
                    f'{new[0]} has no PR but {layer} above it does; link can only append on top.'
                )
                raise Stop(PREFLIGHT_ERROR)
        stack_number = ''
        if new and number:
            lookup = gh_out(
                'api', f'repos/{{owner}}/{{repo}}/pulls/{number}', '--jq', '.stack.number'
            )
            if lookup.returncode != 0:
                print_error(
                    f'Could not read the GitHub stack of PR #{number}; nothing was pushed.'
                )
                raise Stop(PREFLIGHT_ERROR)
            stack_number = lookup.stdout.rstrip('\n')
            if stack_number == 'null':
                stack_number = ''
        names: list[str] = []
        if stack_number:
            names = list(new)
            self.link_args = [stack_number, *names]
        elif not new and merged > 0:
            self.link_args = []
        elif merged > 0:
            print_error('The stack has merged layers but no GitHub stack to append to.')
            raise Stop(PREFLIGHT_ERROR)
        else:
            self.link_args = ['--base', self.trunk]
            for layer in self.layers:
                if layer in self.queued:
                    self.link_args.append(self.pr_of(layer, 'url'))
                else:
                    names.append(layer)
                    self.link_args.append(layer)
        for layer in names:
            if re.fullmatch(r'[0-9]+', layer):
                print_error(
                    f'gh stack link would read layer {layer} as a PR number; rename the branch.'
                )
                raise Stop(PREFLIGHT_ERROR)

    def record_stack(self) -> bool:
        """
        Record the linked PRs locally with gh stack checkout, restoring the branch.

        gh stack link writes no local state, so the next view would report the new PRs
        as missing. gh stack checkout may move HEAD, which is restored.
        """
        head = run_tool('git', 'symbolic-ref', '-q', '--short', 'HEAD')
        if head.returncode != 0:
            return False
        branch = head.stdout.strip()
        if self.link_args[0] == '--base':
            layer = next((name for name in self.layers if name not in self.queued), '')
            layer = layer or (self.layers[-1] if self.layers else '')
            listing = gh_out(
                'pr', 'list', '--head', layer, '--json', 'number', '--jq', '.[0].number'
            )
            number = listing.stdout.rstrip('\n')
            if listing.returncode != 0 or not number:
                return False
            lookup = gh_out(
                'api', f'repos/{{owner}}/{{repo}}/pulls/{number}', '--jq', '.stack.number'
            )
            if lookup.returncode != 0:
                return False
            self.stack_number = lookup.stdout.rstrip('\n')
            if not self.stack_number or self.stack_number == 'null':
                return False
        else:
            self.stack_number = self.link_args[0]
        sys.stdout.flush()
        checkout = subprocess.run(
            ['gh', 'stack', 'checkout', self.stack_number],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=sys.stderr,
        )
        if checkout.returncode != 0:
            return False
        if git_out('symbolic-ref', '-q', '--short', 'HEAD') == branch:
            return True
        return run_inherited('git', 'switch', '-q', branch) == 0

    def link_layers(self) -> None:
        """Open and link the missing PRs, then record them locally."""
        if not self.link_args:
            return
        if run_to_stderr('gh', 'stack', 'link', '--remote', self.remote, *self.link_args):
            print_error('gh stack link failed.')
            raise Stop(PUSH_FAILED)
        self.stack_number = ''
        if not self.record_stack():
            print_error(
                'PRs are linked but not recorded locally; '
                f'run gh stack checkout {self.stack_number or "<stack#>"} '
                'or rerun publish --submit.'
            )
            raise Stop(PUSH_FAILED)

    def begin(self) -> int:
        """Fetch, refuse remote-only work, fast-forward behind layers, and record the tips."""
        self.fetch_layers()
        for layer in self.check_layers(True, self.layers):
            self.fast_forward(layer)
        self.write_state()
        return 0

    def publish(self) -> int:
        """Push the stack leased on the tips begin recorded, then verify every remote tip."""
        if self.submit:
            self.plan_link()
        self.fetch_layers()
        recorded_tip: dict[str, str] = {}
        if self.state_file.is_file():
            for line in self.state_file.read_text().splitlines():
                layer, _, recorded = line.strip().partition(' ')
                if layer:
                    recorded_tip[layer] = recorded.strip()
        unrecorded, moved, checked_tip = [], False, {}
        for layer in self.layers:
            recorded = recorded_tip.get(layer, '')
            remote = self.remote_tip.get(layer, '')
            # A remote already at the local tip loses nothing, e.g. a layer a failed publish pushed.
            current = verify(f'refs/heads/{layer}')
            if not recorded:
                unrecorded.append(layer)
            elif recorded != (remote or '-') and current != remote:
                print_error(
                    f'{layer} on {self.remote} moved since begin: '
                    f'{recorded[:7]} -> {remote or "deleted"}'
                )
                moved = True
            checked_tip[layer] = remote
        if moved:
            raise Stop(REMOTE_MOVED)
        if unrecorded:
            self.check_layers(False, unrecorded)

        self.push_layers()
        if self.submit:
            self.link_layers()

        self.fetch_layers()
        incomplete = False
        for layer in self.layers:
            local_sha = verify(f'refs/heads/{layer}')
            published = self.remote_tip.get(layer, '')
            if local_sha == published:
                continue
            if layer in self.queued and published == checked_tip[layer]:
                print(f'NOTE: {layer} is queued and was not published.', file=sys.stderr)
            else:
                print_error(
                    f'{layer} is not published: local {local_sha[:7]}, '
                    f'{self.remote} {published[:7]}'
                )
                incomplete = True
        if incomplete:
            raise Stop(PUSH_INCOMPLETE)
        self.write_state()
        return 0


def parse_arguments(arguments: list[str]) -> tuple[str, str, bool]:
    """Return the subcommand, remote, and --submit, stopping at a usage error or help."""
    if not arguments:
        print(usage(), end='', file=sys.stderr)
        raise Stop(PREFLIGHT_ERROR)
    subcommand, remaining = arguments[0], list(arguments[1:])
    if subcommand in ('-h', '--help'):
        print(usage(), end='')
        raise Stop(0)
    if subcommand not in ('begin', 'publish'):
        print_error(f'Unknown subcommand: {subcommand}')
        raise Stop(PREFLIGHT_ERROR)
    remote, submit = '', False
    while remaining:
        argument = remaining.pop(0)
        if argument == '--remote':
            if not remaining:
                print_error('Missing value for --remote')
                raise Stop(PREFLIGHT_ERROR)
            remote = remaining.pop(0)
        elif argument == '--submit':
            if subcommand != 'publish':
                print_error('--submit applies to publish only')
                raise Stop(PREFLIGHT_ERROR)
            submit = True
        elif argument in ('-h', '--help'):
            print(usage(), end='')
            raise Stop(0)
        else:
            print_error(f'Unknown argument: {argument}')
            raise Stop(PREFLIGHT_ERROR)
    return subcommand, remote, submit


def main() -> int:
    """Run begin or publish, turning a declared stop into its result code."""
    try:
        subcommand, remote, submit = parse_arguments(sys.argv[1:])
        guard = Guard(remote, submit)
        guard.load_stack()
        return guard.begin() if subcommand == 'begin' else guard.publish()
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES.update(
        {
            REMOTE_ONLY_COMMITS: 'REMOTE_ONLY_COMMITS',
            REMOTE_MOVED: 'REMOTE_MOVED',
            PUSH_FAILED: 'PUSH_FAILED',
            PUSH_INCOMPLETE: 'PUSH_INCOMPLETE',
        }
    )
    rc.install()
    rc.run(main)
