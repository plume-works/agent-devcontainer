#!/usr/bin/env python3

"""
Create a work branch at the freshly fetched remote base and push it with its own upstream.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import git_default_branch  # noqa: E402  (path set above so the plugin's bin/ resolves)
import result_codes as rc  # noqa: E402
from skill_common import (  # noqa: E402
    help_header,
    main_checkout_dir,
    print_error,
    require_git_repo,
    run_inherited,
    run_to_stderr,
    run_tool,
    Stop,
)

BRANCH_EXISTS = 3
CARRY_CONFLICT = 4
PUSH_FAILED = 5
FETCH_FAILED = 6
STASH_CONFLICTS = 7
CREATE_FAILED = 8
DEPENDENCY_NOT_OPEN = 9
GH_FAILED = 10
MERGE_FAILED = 11
PREFLIGHT_ERROR = 2

USAGE = """
Usage:
  git-new-branch.py <name> [--remote <name>] [--base <branch>] [--stash]
  git-new-branch.py <name> --worktree [--worktree-root <dir>] [--remote <name>] [--base <branch>]
  git-new-branch.py <name> --depends-on <pr> [--depends-on <pr>]... [--remote <name>]
                    [--stash | --worktree [--worktree-root <dir>]]

Options:
  --remote <name>        Remote to fetch from and push to. Default: origin
  --base <branch>        Base branch on the remote. Default: main; when it does
                         not exist, the branch refs/remotes/<remote>/HEAD names,
                         or, when that is unset, the default branch gh reports
  --stash                Stash uncommitted and untracked changes, create the
                         branch, then pop them onto it. Only with user approval.
  --worktree             Create the branch in a new worktree; leave the current
                         checkout alone
  --worktree-root <dir>  Parent directory for the worktree (implies --worktree).
                         Default: <main checkout>/.worktrees under
                         AGENTDEV_RUNTIME_MODE=deploy, else /workspaces when
                         the main checkout lives directly under it and it is
                         writable, otherwise <main checkout>/.worktrees.
                         The worktree is <parent>/<repo>-<name>; a '/' in <name>
                         stays a directory separator
  --depends-on <pr>      Repeatable. Each pull request must be open. The branch
                         starts at the first one's head branch instead of
                         --base, merges the other heads, and gets one empty
                         commit with a 'Depends-on: #<pr>' trailer per pull
                         request before it is pushed
  -h, --help             Show this help text.

Output (key=value lines):
  RESULT, BRANCH, BASE, BASE_SHA
  In worktree mode also: WORKTREE
  With --depends-on also: DEPENDS_ON (the pull requests, comma-separated)
  When main/master holds commits the base lacks also: LOCAL_COMMITS; the
  branch then starts at HEAD instead of the base, and outside worktree mode
  main/master is reset to the base afterwards; DEFAULT_RESET=failed when
  that reset failed and main/master still holds the moved commits
  When changes are left stashed also: STASH_SHA (the entry's commit) and
  STASH_REF (its current stash@{n}; absent if the entry left the list)

Results (RESULT / exit code):
  SUCCESS          0  Branch created, pushed, and tracking <remote>/<name>
  BRANCH_EXISTS    3  <name> exists locally or on the remote; nothing was created
  CARRY_CONFLICT   4  Uncommitted changes touch paths that differ between HEAD
                      and the base, or would be carried onto a branch merging
                      more than one dependency; nothing was changed
  PUSH_FAILED      5  The branch was created locally but the push failed
  FETCH_FAILED     6  The remote could not be fetched
  STASH_CONFLICTS  7  The branch was created but popping the stash conflicted;
                      the stash entry STASH_REF is kept
  CREATE_FAILED    8  The branch could not be created; the checkout is unchanged
                      and any stash was restored (STASH_REF when restoring failed)
  DEPENDENCY_NOT_OPEN 9  A --depends-on pull request is not open; nothing was
                      created
  GH_FAILED       10  gh could not read a --depends-on pull request; nothing
                      was created
  MERGE_FAILED    11  Merging another dependency's head failed; the branch is
                      kept locally, unpushed, with the merge left to resolve
  PREFLIGHT_ERROR  2  Bad usage, not a repo, invalid name, or no base ref
  SCRIPT_FAILURE   1  Unhandled error
  SIGNAL_HUP     129  Interrupted by HUP
  SIGNAL_INT     130  Interrupted by INT
  SIGNAL_TERM    143  Interrupted by TERM

Examples:
  agent-code/git-new-branch.py my-feature
  agent-code/git-new-branch.py my-feature --stash
  agent-code/git-new-branch.py my-feature --worktree
  agent-code/git-new-branch.py my-feature --depends-on 591
"""

DESCRIPTION = (
    'Create a work branch at the freshly fetched remote base and push it with its own upstream.'
)


class Options(NamedTuple):
    """The parsed command line."""

    branch: str
    remote: str
    base: str
    worktree: bool
    worktree_root: str
    stash: bool
    depends_on: tuple[int, ...] = ()


class Dependency(NamedTuple):
    """An open pull request the new branch builds on."""

    number: int
    head_branch: str


class WorktreeParent(NamedTuple):
    """Where a worktree goes, and whether that is the checkout's own .worktrees/."""

    path: str
    in_checkout: bool


def usage() -> str:
    """Return the full help text."""
    return help_header(DESCRIPTION, __file__) + USAGE


def worktree_parent(main_dir: str, runtime_mode: str, worktree_root: str) -> WorktreeParent:
    """
    Choose the worktree parent: --worktree-root, else by runtime mode and checkout location.

    The deploy runtime mounts only the checkout, so nothing else there persists, and a
    non-root account cannot write the root-owned /workspaces.
    """
    if worktree_root:
        return WorktreeParent(worktree_root, False)
    sibling = runtime_mode != 'deploy' and os.path.dirname(main_dir) == '/workspaces'
    if sibling and os.access('/workspaces', os.W_OK):
        return WorktreeParent('/workspaces', False)
    return WorktreeParent(f'{main_dir}/.worktrees', True)


def parse_arguments(arguments: list[str]) -> Options:
    """Parse the command line in order, stopping at the first usage error or help."""
    branch = ''
    remote = 'origin'
    base = 'main'
    worktree = False
    worktree_root = ''
    stash = False
    base_given = False
    depends_on: list[int] = []
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument in ('--remote', '--base', '--worktree-root', '--depends-on'):
            if not remaining:
                print_error(f'Missing value for {argument}')
                raise Stop(PREFLIGHT_ERROR)
            value = remaining.pop(0)
            if argument == '--remote':
                remote = value
            elif argument == '--base':
                base = value
                base_given = True
            elif argument == '--depends-on':
                number = value.removeprefix('#')
                if not number.isdigit() or int(number) == 0:
                    print_error(f'--depends-on takes a pull request number, not {value!r}')
                    raise Stop(PREFLIGHT_ERROR)
                if int(number) not in depends_on:
                    depends_on.append(int(number))
            else:
                worktree_root = value
                worktree = True
        elif argument == '--worktree':
            worktree = True
        elif argument == '--stash':
            stash = True
        elif argument in ('-h', '--help'):
            print(usage(), end='')
            raise Stop(0)
        elif argument.startswith('-'):
            print_error(f'Unknown option: {argument}')
            print(usage(), end='', file=sys.stderr)
            raise Stop(PREFLIGHT_ERROR)
        elif branch:
            print_error(f'Unexpected argument: {argument}')
            print(usage(), end='', file=sys.stderr)
            raise Stop(PREFLIGHT_ERROR)
        else:
            branch = argument
    if not branch:
        print_error('Missing branch name.')
        print(usage(), end='', file=sys.stderr)
        raise Stop(PREFLIGHT_ERROR)
    if worktree and stash:
        print_error(
            '--stash has no effect in worktree mode, which leaves the current checkout alone.'
        )
        raise Stop(PREFLIGHT_ERROR)
    if depends_on and base_given:
        print_error('--depends-on sets the base to its first pull request; drop --base.')
        raise Stop(PREFLIGHT_ERROR)
    return Options(branch, remote, base, worktree, worktree_root, stash, tuple(depends_on))


def git_ok(*arguments: str) -> bool:
    """Return whether a quiet git command succeeds."""
    return run_tool('git', *arguments).returncode == 0


def git_out(*arguments: str) -> str:
    """Return a git command's stripped stdout, whatever its status."""
    return run_tool('git', *arguments).stdout.strip()


def commit_of(ref: str) -> str:
    """Return the commit `ref` names, or '' when it names none."""
    completed = run_tool('git', 'rev-parse', '--verify', '--quiet', f'{ref}^{{commit}}')
    return completed.stdout.strip() if completed.returncode == 0 else ''


def resolve_base(remote: str, base: str) -> str:
    """Return the remote-tracking base, falling back to the remote's default branch."""
    base_ref = f'{remote}/{base}'
    if commit_of(f'refs/remotes/{base_ref}'):
        return base_ref
    default_branch = git_default_branch.remote_default_branch(remote)
    if default_branch is None:
        print_error(
            f"'{base_ref}' does not exist, refs/remotes/{remote}/HEAD is not set, "
            'and gh could not report the default branch.'
        )
        print_error(f'Pass --base <branch>, or run: git remote set-head {remote} --auto')
        raise Stop(PREFLIGHT_ERROR)
    default_ref = f'{remote}/{default_branch}'
    if not commit_of(f'refs/remotes/{default_ref}'):
        print_error(
            f"The remote default branch '{default_branch}' was not fetched as '{default_ref}'."
        )
        raise Stop(PREFLIGHT_ERROR)
    print(
        f"'{base_ref}' does not exist; using the remote default branch '{default_ref}'.",
        file=sys.stderr,
    )
    return default_ref


def open_dependencies(options: Options) -> list[Dependency]:
    """Look up every --depends-on pull request, stopping unless each one is open."""
    repository = git_out('remote', 'get-url', options.remote)
    dependencies = []
    for number in options.depends_on:
        completed = run_tool(
            'gh', 'pr', 'view', str(number), '--repo', repository,
            '--json', 'state,isCrossRepository,headRefName',
            '--jq', '.state + " " + (.isCrossRepository | tostring) + " " + .headRefName',
        )  # fmt: skip
        state, _, rest = completed.stdout.strip().partition(' ')
        cross_repository, _, head_branch = rest.partition(' ')
        if completed.returncode != 0 or not head_branch:
            print_error(f'gh could not read pull request #{number}: {completed.stderr.strip()}')
            raise Stop(GH_FAILED)
        if state != 'OPEN':
            print_error(f'Pull request #{number} is {state}, not open; nothing was created.')
            raise Stop(DEPENDENCY_NOT_OPEN)
        if cross_repository != 'false':
            print_error(
                f"Pull request #{number}'s head is in a fork; a dependent branch can only be "
                f'cut from a branch of {options.remote}.'
            )
            raise Stop(PREFLIGHT_ERROR)
        dependencies.append(Dependency(number, head_branch))
    return dependencies


def resolve_dependency_base(remote: str, dependency: Dependency) -> str:
    """Return the remote-tracking head branch of `dependency`; there is no fallback."""
    head_ref = f'{remote}/{dependency.head_branch}'
    if not commit_of(f'refs/remotes/{head_ref}'):
        print_error(f"Pull request #{dependency.number}'s head '{head_ref}' was not fetched.")
        raise Stop(PREFLIGHT_ERROR)
    return head_ref


def record_dependencies(options: Options, dependencies: list[Dependency], cwd: str) -> int:
    """
    Add one trailer commit per dependency, then merge every dependency head after the first.

    The trailer commits are built with commit-tree, so carried changes stay uncommitted.
    """
    for dependency in dependencies:
        tree = git_out('-C', cwd, 'rev-parse', 'HEAD^{tree}')
        parent = git_out('-C', cwd, 'rev-parse', 'HEAD')
        commit = git_out(
            '-C', cwd, 'commit-tree', tree, '-p', parent,
            '-m', f'Depend on #{dependency.number}',
            '-m', f'Depends-on: #{dependency.number}',
        )  # fmt: skip
        if not commit or run_to_stderr(
            'git', '-C', cwd, 'update-ref', f'refs/heads/{options.branch}', commit, parent
        ):
            print_error(f'Could not record the dependency on #{dependency.number}.')
            return CREATE_FAILED
    for dependency in dependencies[1:]:
        head_ref = resolve_dependency_base(options.remote, dependency)
        if run_to_stderr('git', '-C', cwd, 'merge', '--no-edit', head_ref):
            print_error(
                f"Merging {head_ref} into '{options.branch}' failed; the branch is kept "
                'locally and unpushed. Resolve and commit the merge, then push with: '
                f'git push --set-upstream {options.remote} {options.branch}'
            )
            return MERGE_FAILED
    return 0


def push_branch(options: Options) -> int:
    """Push the new branch with its own upstream; git's output goes to stderr."""
    print(f'Pushing {options.branch} to {options.remote}...', file=sys.stderr)
    return run_to_stderr('git', 'push', '--set-upstream', options.remote, options.branch)


def create_worktree(options: Options, start_sha: str, dependencies: list[Dependency]) -> int:
    """Create the branch in a new worktree and push it."""
    main_dir = main_checkout_dir()
    if main_dir is None:
        return 1
    parent = worktree_parent(
        str(main_dir), os.environ.get('AGENTDEV_RUNTIME_MODE', ''), options.worktree_root
    )
    if parent.in_checkout and not git_ok(
        '-C', str(main_dir), 'check-ignore', '--quiet', '.worktrees/'
    ):
        common_dir = git_out('rev-parse', '--path-format=absolute', '--git-common-dir')
        exclude_file = Path(common_dir) / 'info' / 'exclude'
        exclude_file.parent.mkdir(parents=True, exist_ok=True)
        with exclude_file.open('a') as exclude:
            exclude.write('.worktrees/\n')
        print(f'Added .worktrees/ to {exclude_file}.', file=sys.stderr)
    worktree_dir = f'{parent.path}/{main_dir.name}-{options.branch}'
    if os.path.lexists(worktree_dir):
        print_error(f"Worktree path '{worktree_dir}' already exists.")
        return PREFLIGHT_ERROR
    # A failed add can still leave the new branch behind; it did not exist before.
    if run_to_stderr(
        'git', 'worktree', 'add', '--no-track', '-b', options.branch, worktree_dir, start_sha
    ):
        if git_ok('show-ref', '--verify', '--quiet', f'refs/heads/{options.branch}'):
            run_to_stderr('git', 'branch', '-D', options.branch)
        print_error(f"Could not add the worktree '{worktree_dir}'; nothing was created.")
        return CREATE_FAILED
    print(f'WORKTREE={worktree_dir}')
    recorded = record_dependencies(options, dependencies, worktree_dir)
    if recorded:
        return recorded
    if push_branch(options):
        print_error('Push failed; the local branch and worktree are kept.')
        return PUSH_FAILED
    return 0


def null_separated(*arguments: str) -> list[str]:
    """
    Return the NUL-separated paths a git command prints, in any encoding.

    `-z` turns off git's quoting, so names arrive as raw bytes; `os.fsdecode`
    keeps a non-UTF-8 name round-trippable instead of failing on it.
    """
    listing = subprocess.run(['git', *arguments], check=False, capture_output=True).stdout
    return [os.fsdecode(path) for path in listing.split(b'\0') if path]


def blocked_paths(start_sha: str) -> list[str]:
    """Return uncommitted paths that also differ between HEAD and the start commit."""
    changed_between = set(
        null_separated('diff', '--no-renames', '--name-only', '-z', 'HEAD', start_sha)
    )
    uncommitted = [
        *null_separated('diff', '--no-renames', '--name-only', '-z', 'HEAD'),
        *null_separated('diff', '--cached', '--no-renames', '--name-only', '-z'),
        *null_separated('ls-files', '--others', '--exclude-standard', '-z'),
    ]
    return [path for path in uncommitted if path in changed_between]


class OwnStash:
    """The stash entry this run created, found by its commit since the stack is shared."""

    def __init__(self, sha: str) -> None:
        self.sha = sha

    def ref(self) -> str | None:
        """Return the entry's current stash@{n}, or None once it left the list."""
        for line in git_out('stash', 'list', '--format=%gd %H').splitlines():
            ref, _, sha = line.partition(' ')
            if sha == self.sha:
                return ref
        return None

    def pop(self) -> bool:
        """Pop exactly this entry; False when it is gone or popping failed."""
        ref = self.ref()
        if ref is None:
            print_error(f'Stash entry {self.sha} is no longer in the stash list.')
            return False
        return run_to_stderr('git', 'stash', 'pop', ref) == 0

    def report(self) -> str:
        """Print STASH_REF when still listed and STASH_SHA; return the name to cite."""
        ref = self.ref()
        if ref is not None:
            print(f'STASH_REF={ref}')
        print(f'STASH_SHA={self.sha}')
        return ref or self.sha


def stash_changes(branch: str) -> OwnStash | None:
    """Stash every change, untracked included; None when git saved nothing."""
    before = commit_of('refs/stash')
    status = run_to_stderr(
        'git', 'stash', 'push', '--include-untracked', '--message', f'git-new-branch: {branch}'
    )
    if status:
        raise Stop(status)
    after = commit_of('refs/stash')
    if after and after != before:
        return OwnStash(after)
    print('git stash saved nothing; no stash entry will be popped.', file=sys.stderr)
    return None


def create_in_place(
    options: Options,
    base_ref: str,
    base_sha: str,
    start_sha: str,
    current: str,
    dependencies: list[Dependency],
) -> int:
    """Create the branch in this checkout, carrying or stashing changes, and push it."""
    dirty = bool(git_out('status', '--porcelain', '--untracked-files=all'))
    if dirty and not options.stash and len(dependencies) > 1:
        # A real merge of the further heads refuses a checkout with changes.
        print_error(
            'Uncommitted changes cannot be carried onto a branch that merges more than one '
            'dependency. Nothing was changed. Commit them first, or rerun with --stash only '
            'after the user approves stashing.'
        )
        return CARRY_CONFLICT
    if dirty and not options.stash:
        blocked = blocked_paths(start_sha)
        if blocked:
            print_error(
                f'Uncommitted changes touch paths that differ between HEAD and {base_ref}:'
            )
            sys.stderr.flush()
            for path in blocked:
                sys.stderr.buffer.write(b'  ' + os.fsencode(path) + b'\n')
            sys.stderr.buffer.flush()
            print_error(
                'Nothing was changed. Rerun with --stash only after the user approves stashing.'
            )
            return CARRY_CONFLICT

    stash = stash_changes(options.branch) if dirty and options.stash else None

    if run_to_stderr('git', 'switch', '--no-track', '--create', options.branch, start_sha):
        print_error(f"Could not create '{options.branch}'; the checkout was not changed.")
        if stash is not None and not stash.pop():
            kept = stash.report()
            print_error(f'Restoring the stash failed; the stash entry {kept} holds the changes.')
        return CREATE_FAILED

    # The default branch is reset only once its old tip is safe on the new branch.
    if start_sha != base_sha and git_ok(
        'merge-base', '--is-ancestor', start_sha, f'refs/heads/{options.branch}'
    ):
        if run_to_stderr('git', 'branch', '--force', current, base_sha) == 0:
            print(
                f"Reset '{current}' to {base_ref}; its commits now live on '{options.branch}'.",
                file=sys.stderr,
            )
        else:
            print('DEFAULT_RESET=failed')
            print_error(
                f"Could not reset '{current}' to {base_ref}; it still holds the moved commits."
            )

    recorded = record_dependencies(options, dependencies, '.')
    if recorded:
        if stash is not None:
            kept = stash.report()
            print_error(f'The stash entry {kept} still holds the changes.')
        return recorded

    push_status = push_branch(options)

    if stash is not None and not stash.pop():
        kept = stash.report()
        print_error(f'Popping the stash conflicted; the stash entry {kept} is kept.')
        if push_status:
            print_error('The push also failed; the branch has no upstream yet.')
        return STASH_CONFLICTS

    if push_status:
        print_error(f"Push failed; the local branch '{options.branch}' is kept.")
        return PUSH_FAILED
    return 0


def run(arguments: list[str]) -> int:
    """Create, push, and report the work branch."""
    options = parse_arguments(arguments)
    require_git_repo()
    if not git_ok('check-ref-format', '--branch', options.branch):
        print_error(f"'{options.branch}' is not a valid branch name.")
        return PREFLIGHT_ERROR

    print(f'BRANCH={options.branch}')
    dependencies = open_dependencies(options)
    if dependencies:
        print(f'DEPENDS_ON={",".join(str(dependency.number) for dependency in dependencies)}')
    print(f'Fetching {options.remote}...', file=sys.stderr)
    if run_inherited('git', 'fetch', options.remote):
        print_error(f"Failed to fetch remote '{options.remote}'.")
        return FETCH_FAILED

    base_ref = (
        resolve_dependency_base(options.remote, dependencies[0])
        if dependencies
        else resolve_base(options.remote, options.base)
    )
    base_sha = commit_of(f'refs/remotes/{base_ref}')
    print(f'BASE={base_ref}')
    print(f'BASE_SHA={base_sha}')

    if git_ok('show-ref', '--verify', '--quiet', f'refs/heads/{options.branch}'):
        print_error(
            f"Local branch '{options.branch}' already exists; it is never reset or reused."
        )
        return BRANCH_EXISTS
    if git_ok(
        'show-ref', '--verify', '--quiet', f'refs/remotes/{options.remote}/{options.branch}'
    ):
        print_error(
            f"'{options.remote}/{options.branch}' already exists; it is never reset or reused."
        )
        return BRANCH_EXISTS

    # Commits made on the default branch move to the new branch instead of being
    # left behind; the caller merges the base in afterwards.
    start_sha = base_sha
    current = git_out('symbolic-ref', '--quiet', '--short', 'HEAD')
    if not dependencies and git_default_branch.is_default_branch(current):
        local_commits = int(git_out('rev-list', '--count', f'{base_sha}..HEAD') or 0)
        if local_commits > 0:
            start_sha = git_out('rev-parse', 'HEAD')
            print(f'LOCAL_COMMITS={local_commits}')
            print(
                f"'{current}' holds {local_commits} commit(s) not in {base_ref}; "
                'the branch starts at HEAD.',
                file=sys.stderr,
            )

    if options.worktree:
        return create_worktree(options, start_sha, dependencies)
    return create_in_place(options, base_ref, base_sha, start_sha, current, dependencies)


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES.update(
        {
            BRANCH_EXISTS: 'BRANCH_EXISTS',
            CARRY_CONFLICT: 'CARRY_CONFLICT',
            PUSH_FAILED: 'PUSH_FAILED',
            FETCH_FAILED: 'FETCH_FAILED',
            STASH_CONFLICTS: 'STASH_CONFLICTS',
            CREATE_FAILED: 'CREATE_FAILED',
            DEPENDENCY_NOT_OPEN: 'DEPENDENCY_NOT_OPEN',
            GH_FAILED: 'GH_FAILED',
            MERGE_FAILED: 'MERGE_FAILED',
        }
    )
    rc.install()
    rc.run(main)
