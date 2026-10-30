#!/usr/bin/env python3

"""Sync the local working tree onto the codespace created by codespace-ensure.py."""

from __future__ import annotations

import subprocess
import sys

import codespace_common as cs
from codespace_common import print_error, run_tool, Stop

REMOTE_CHECKOUT_DIRTY = 4
REMOTE_COMMITS_ABSENT = 5
REMOTE_SSH_FAILED = 6
RSYNC_FAILED = 7
PUSH_REJECTED = 8
PREFLIGHT_ERROR = 2

DESCRIPTION = 'Sync the local working tree onto the codespace created by codespace-ensure.py.'

USAGE = """
Usage:
  codespace-sync.py

Options:
  -h, --help         Show this help text.

Behavior:
  Refuses to overwrite a dirty Codespace checkout or one with commits that are
  absent from origin. If both trees are safe, a clean local tree is pushed then
  synced by git; a dirty local tree is copied by rsync without deleting
  remote-only files, then removes only git-tracked paths deleted locally. Both
  paths exclude .git and ignored local files.

Output (key=value lines):
  RESULT, ACTION, CODESPACE
  ACTION=rsync also prints: HOST
  ACTION=git-push also prints: BRANCH, and the git push and remote git
  transcripts verbatim before the keys

Results (RESULT / exit code):
  SUCCESS                  0  Synced (either path)
  REMOTE_CHECKOUT_DIRTY    4  Codespace checkout has uncommitted or untracked files
  REMOTE_COMMITS_ABSENT    5  Codespace checkout has commits absent from origin
  REMOTE_SSH_FAILED        6  An SSH call to the codespace failed: checkout inspection,
                              SSH config generation, deleting locally-removed paths, or
                              the remote fetch/checkout/reset
  RSYNC_FAILED             7  rsync to the codespace failed
  PUSH_REJECTED            8  git push failed (diverged, or another push error)
  CODESPACE_SCOPE_MISSING  3  gh token is missing the 'codespace' OAuth scope
  PREFLIGHT_ERROR          2  Usage error, not a repo, detached HEAD, gh or rsync missing,
                              gh unauthenticated, or no recorded codespace name
  SCRIPT_FAILURE           1  Unhandled error

Examples:
  agent-code/codespace-sync.py
"""

DIRTY_MARKER = 'CODESPACE_REMOTE_CHECKOUT_DIRTY'
COMMITS_MARKER = 'CODESPACE_REMOTE_COMMITS_ABSENT_FROM_ORIGIN'


def merged(*arguments: str, stdin: object = None) -> tuple[int, str]:
    """Run a command with stderr folded into stdout; return its status and `$(...)` output."""
    sys.stdout.flush()
    completed = subprocess.run(
        list(arguments),
        check=False,
        stdin=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    return completed.returncode, completed.stdout.rstrip('\n')


def preflight_command(workspace_q: str) -> str:
    """
    Return the remote check that refuses a dirty checkout or one with unpushed commits.

    Ignored build output does not count as dirty; each refusal prints a marker, so an
    SSH or git failure over the same connection is never mistaken for one.
    """
    return (
        f'cd {workspace_q} && git fetch origin && '
        'remote_status=$(git status --porcelain) && '
        'if [[ -n "${remote_status}" ]]; then '
        f"  printf '%s\\n' '{DIRTY_MARKER}' >&2; "
        '  exit 4; '
        'fi && '
        'remote_only_count=$(git rev-list --count HEAD --not --remotes=origin) && '
        'if (( remote_only_count > 0 )); then '
        f"  printf '%s\\n' '{COMMITS_MARKER}' >&2; "
        '  exit 5; '
        'fi'
    )


def rsync_sync(name: str, workspace_dir: str, workspace_q: str) -> int:
    """Copy a dirty tree with rsync, then delete the tracked paths removed locally."""
    cs.require_rsync()
    ssh_config = cs.ssh_config_file()
    sys.stdout.flush()
    with ssh_config.open('w') as config:
        generated = subprocess.run(
            ['gh', 'codespace', 'ssh', '-c', name, '--config'], check=False, stdout=config
        )
    if generated.returncode != 0:
        print_error(f'Failed to generate SSH config for codespace {name}.')
        return REMOTE_SSH_FAILED
    host = next(
        (
            fields[1]
            for fields in (line.split() for line in ssh_config.read_text().splitlines())
            if len(fields) > 1 and fields[0] == 'Host'
        ),
        '',
    )
    if not host:
        print_error('Could not parse SSH host alias from generated config.')
        return REMOTE_SSH_FAILED

    repo_root = run_tool('git', 'rev-parse', '--show-toplevel').stdout.strip()
    exclude_file = cs.sync_exclude_file()
    # git's fully resolved ignore list, since rsync can neither read nested
    # .gitignore files nor honour a '!' negation such as .vscode/mcp.json.
    ignored = run_tool(
        'git', '-C', repo_root, 'ls-files', '--others', '--ignored', '--exclude-standard'
    ).stdout
    exclude_file.write_text(''.join(f'/{line}\n' for line in ignored.splitlines()))

    status, output = merged(
        'rsync', '-az', '-e', f'ssh -F {ssh_config}',
        f'--exclude-from={exclude_file}', '--exclude', '.git',
        f'{repo_root}/', f'{host}:{workspace_dir}/',
    )  # fmt: skip
    if status != 0:
        print_error('rsync to codespace failed:')
        print(output, file=sys.stderr)
        return RSYNC_FAILED

    # No rsync --delete: remote-only logs and ignored work must survive. Only tracked
    # paths deleted locally are removed; --no-renames makes a rename a deletion plus
    # a copied path, and NUL-delimited names keep spaces and newlines safe.
    deleted_file = cs.repo_root_tmp_dir() / 'codespace-sync-deleted-paths'
    deleted = subprocess.run(
        ['git', '-C', repo_root, 'diff', '--no-renames', '--name-only', '-z',
         '--diff-filter=D', 'HEAD', '--'],
        check=False,
        capture_output=True,
    ).stdout  # fmt: skip
    deleted_file.write_bytes(deleted)
    if deleted:
        with deleted_file.open('rb') as names:
            status, output = merged(
                'ssh', '-F', str(ssh_config), host,
                f'cd {workspace_q} && xargs -0 -r rm -f --',
                stdin=names,
            )  # fmt: skip
        if status != 0:
            print_error('Could not remove git-tracked paths deleted locally:')
            print(output, file=sys.stderr)
            return REMOTE_SSH_FAILED

    print('ACTION=rsync')
    print(f'HOST={host}')
    print(f'CODESPACE={name}')
    return 0


def push_sync(name: str, workspace_q: str) -> int:
    """Push a clean tree, then fetch and reset the codespace checkout to it."""
    branch = cs.current_branch()
    if not branch:
        print_error('Could not determine the current branch.')
        return PREFLIGHT_ERROR
    if branch == 'HEAD':
        print_error('Detached HEAD: check out the branch to sync before running this script.')
        return PREFLIGHT_ERROR

    tracked = run_tool(
        'git', 'rev-parse', '--abbrev-ref', '--symbolic-full-name', f'{branch}@{{u}}'
    )
    push = ['git', 'push'] if tracked.returncode == 0 else ['git', 'push', '-u', 'origin', branch]
    status, output = merged(*push)
    if status != 0:
        print_error('Git push failed. Fetch/merge or rebase to resolve, then re-run:')
        print(output, file=sys.stderr)
        return PUSH_REJECTED
    print(output)

    branch_q = cs.bash_quote(branch)
    status, output = merged(
        'gh', 'codespace', 'ssh', '-c', name, '--',
        f'cd {workspace_q} && git fetch origin && git checkout {branch_q} '
        f'&& git reset --hard origin/{branch_q}',
    )  # fmt: skip
    if status != 0:
        print_error('Remote sync over SSH failed:')
        print(output, file=sys.stderr)
        return REMOTE_SSH_FAILED
    print(output)

    print('ACTION=git-push')
    print(f'BRANCH={branch}')
    print(f'CODESPACE={name}')
    return 0


def run(arguments: list[str]) -> int:
    """Refuse an unsafe codespace checkout, then sync by rsync or by push."""
    for argument in arguments:
        if argument in ('-h', '--help'):
            print(cs.help_header(DESCRIPTION) + USAGE, end='')
            return 0
        print_error(f'Unknown argument: {argument}')
        print(cs.help_header(DESCRIPTION) + USAGE, end='', file=sys.stderr)
        return PREFLIGHT_ERROR

    cs.preflight()
    name = cs.read_codespace_name()
    workspace_dir = cs.codespace_workspace_dir()
    workspace_q = cs.bash_quote(workspace_dir)

    status, output = merged(
        'gh', 'codespace', 'ssh', '-c', name, '--', preflight_command(workspace_q)
    )
    if status != 0:
        if DIRTY_MARKER in output:
            print_error(
                f'Codespace {name} has uncommitted or untracked files; refusing to overwrite '
                'them. Commit and push them, or discard them, then re-run sync.'
            )
            return REMOTE_CHECKOUT_DIRTY
        if COMMITS_MARKER in output:
            print_error(
                f'Codespace {name} has commits absent from origin; refusing to reset it. Push '
                'or recover those commits, or explicitly return the Codespace checkout to an '
                'origin commit, then re-run sync.'
            )
            return REMOTE_COMMITS_ABSENT
        print_error(f'Could not safely inspect the Codespace checkout: {output}')
        return REMOTE_SSH_FAILED

    if run_tool('git', 'status', '--porcelain').stdout.strip():
        return rsync_sync(name, workspace_dir, workspace_q)
    return push_sync(name, workspace_q)


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    cs.install(
        {
            REMOTE_CHECKOUT_DIRTY: 'REMOTE_CHECKOUT_DIRTY',
            REMOTE_COMMITS_ABSENT: 'REMOTE_COMMITS_ABSENT',
            REMOTE_SSH_FAILED: 'REMOTE_SSH_FAILED',
            RSYNC_FAILED: 'RSYNC_FAILED',
            PUSH_REJECTED: 'PUSH_REJECTED',
        }
    )
    cs.rc.run(main)
