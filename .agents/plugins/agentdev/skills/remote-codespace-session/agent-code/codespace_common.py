#!/usr/bin/env python3

"""
Shared helpers for the remote-codespace-session skill scripts.

Imported by the four entry points beside it; standard library only.
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import result_codes as rc  # noqa: E402  (path set above so the plugin's bin/ resolves)
from skill_common import print_error, require_git_repo, run_tool, Stop  # noqa: E402

PREFLIGHT_ERROR = 2
# require_codespace_auth is shared by every script in this skill, so the situation
# it reports is declared once, here; each script declares its own outcomes from 4.
CODESPACE_SCOPE_MISSING = 3


def install(results: dict[int, str]) -> None:
    """Declare the shared and the script's own results, then install the RESULT hooks."""
    rc.RESULT_CODES[CODESPACE_SCOPE_MISSING] = 'CODESPACE_SCOPE_MISSING'
    rc.RESULT_CODES.update(results)
    rc.install()


def help_header(description: str) -> str:
    """Return the description and skill root lines every script's help starts with."""
    return f'{description}\n\nSkill root: {Path(__file__).resolve().parents[1]}\n'


def captured(*arguments: str, stderr: int | None = None) -> subprocess.CompletedProcess[str]:
    """Run a command with stdout captured; stderr passes through unless redirected."""
    sys.stdout.flush()
    return subprocess.run(
        list(arguments), check=False, stdout=subprocess.PIPE, stderr=stderr, text=True
    )


def strip_lines(text: str) -> str:
    """Trim each line as `sed 's/^[[:space:]]*//; s/[[:space:]]*$//'` does, read by `$(...)`."""
    return '\n'.join(line.strip() for line in text.split('\n')).rstrip('\n')


def require_gh() -> None:
    """Stop unless gh is on PATH."""
    if shutil.which('gh') is None:
        print_error("The GitHub CLI ('gh') is required but was not found on PATH.")
        raise Stop(PREFLIGHT_ERROR)


def require_rsync() -> None:
    """Stop unless rsync is on PATH."""
    if shutil.which('rsync') is None:
        print_error(
            "'rsync' is required for the dirty-tree sync path but was not found on PATH. "
            "Install it locally (e.g. 'apt-get install -y rsync'); it is pre-installed in the "
            'codespace image on the remote end.'
        )
        raise Stop(PREFLIGHT_ERROR)


def require_codespace_auth() -> None:
    """Stop unless gh can list codespaces: a scope error is CODESPACE_SCOPE_MISSING."""
    listing = subprocess.run(
        ['gh', 'codespace', 'list', '--json', 'name', '-q', 'length'],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if listing.returncode == 0:
        return
    if re.search('403|scope', listing.stderr, re.IGNORECASE):
        print_error(
            "gh is authenticated but the token is missing the 'codespace' OAuth scope. This "
            "skill needs a token with 'repo' + 'codespace' scopes (set GH_TOKEN/GITHUB_TOKEN, "
            "or run 'gh auth login' with those scopes)."
        )
        raise Stop(CODESPACE_SCOPE_MISSING)
    print_error("gh is not authenticated. Run 'gh auth status' to check, then 'gh auth login'.")
    raise Stop(PREFLIGHT_ERROR)


def require_int_min(flag: str, value: str, minimum: int) -> int:
    """
    Return `value` as an integer, stopping unless it is a decimal integer >= `minimum`.

    Rejected during parsing, so a bad value is a PREFLIGHT_ERROR rather than a crash or
    an endless poll later; 08 reads as eight, not octal.
    """
    if not re.fullmatch(r'[0-9]+', value) or int(value) < minimum:
        print_error(f'{flag} expects an integer >= {minimum}, got: {value}')
        raise Stop(PREFLIGHT_ERROR)
    return int(value)


def current_branch() -> str:
    """Return the checked-out branch, or '' when git cannot name HEAD."""
    completed = run_tool('git', 'rev-parse', '--abbrev-ref', 'HEAD')
    if completed.returncode != 0:
        return ''
    return completed.stdout.strip()


def resolve_owner_repo() -> str:
    """
    Return OWNER/NAME for this checkout, stopping when gh cannot resolve it.

    Called after require_codespace_auth proved gh works, so a failure is a broken call.
    """
    view = captured(
        'gh', 'repo', 'view', '--json', 'owner,name', '-q', '.owner.login + "/" + .name',
        stderr=subprocess.DEVNULL,
    )  # fmt: skip
    value = view.stdout.rstrip('\n')
    if view.returncode != 0 or not value:
        print_error(
            "Could not resolve the GitHub repository for this checkout. Check 'gh repo view'."
        )
        raise Stop(PREFLIGHT_ERROR)
    return value


def codespace_workspace_dir() -> str:
    """
    Return /workspaces/<repo>, where Codespaces clones the repository.

    Derived from the repository name rather than the local checkout's location.
    """
    view = captured(
        'gh', 'repo', 'view', '--json', 'name', '-q', '.name', stderr=subprocess.DEVNULL
    )
    name = view.stdout.rstrip('\n')
    if view.returncode != 0 or not name:
        print_error(
            "Could not resolve the GitHub repository name for this checkout. Check 'gh repo view'."
        )
        raise Stop(PREFLIGHT_ERROR)
    return f'/workspaces/{name}'


def branch_slug(branch: str) -> str:
    """
    Return the branch lower-cased, runs of other characters as '-', cut to 40.

    No collision handling: branches sharing a 40-character sanitized prefix share a
    codespace display name, and codespace-ensure.py reuses it.
    """
    slug = branch.translate(
        str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')
    )
    slug = re.sub(r'[^a-z0-9-]+', '-', slug).lstrip('-').rstrip('-')
    return slug[:40]


def codespace_display_name(branch: str) -> str:
    """Return the display name of the branch's codespace."""
    return f'agent-{branch_slug(branch)}'


def repo_root_tmp_dir() -> Path:
    """Return the repository's .tmp, creating it."""
    tmp_dir = require_git_repo() / '.tmp'
    tmp_dir.mkdir(parents=True, exist_ok=True)
    return tmp_dir


def codespace_name_file() -> Path:
    """Return where the session's codespace name is recorded."""
    return repo_root_tmp_dir() / 'codespace-name'


def ssh_config_file() -> Path:
    """Return where the generated SSH config is written."""
    return repo_root_tmp_dir() / 'codespace-ssh-config'


def sync_exclude_file() -> Path:
    """Return where the rsync exclude list is written."""
    return repo_root_tmp_dir() / 'codespace-sync-exclude'


def write_codespace_name(name: str) -> None:
    """Record the session's codespace name."""
    codespace_name_file().write_text('\n'.join(line.strip() for line in name.split('\n')))


def read_codespace_name() -> str:
    """Return the recorded codespace name, stopping when none was recorded."""
    name_file = codespace_name_file()
    if not name_file.is_file() or name_file.stat().st_size == 0:
        print_error('No codespace name recorded. Run codespace-ensure.py first.')
        raise Stop(PREFLIGHT_ERROR)
    return strip_lines(name_file.read_text())


def _lookup(owner_repo: str, fields: str, key: str, value: str, field: str) -> str | None:
    """Return `field` of the first listed codespace whose `key` is `value`; None on failure."""
    listing = captured(
        'gh', 'codespace', 'list', '-R', owner_repo, '--json', fields,
        '-q', f'.[] | select(.{key}=="{value}") | .{field}',
        stderr=subprocess.DEVNULL,
    )  # fmt: skip
    if listing.returncode != 0:
        return None
    return listing.stdout.rstrip('\n').split('\n')[0]


def codespace_lookup_by_display_name(owner_repo: str, display_name: str) -> str | None:
    """Return the name of the codespace with `display_name`, '' for none, None on failure."""
    return _lookup(owner_repo, 'name,displayName', 'displayName', display_name, 'name')


def codespace_state_by_name(owner_repo: str, name: str) -> str | None:
    """Return the state of codespace `name`, '' when it is gone, None on failure."""
    return _lookup(owner_repo, 'name,state', 'name', name, 'state')


def preflight(*, codespace_auth: bool = True) -> None:
    """Run the checks every script runs first: a repository, gh, and codespace access."""
    require_git_repo()
    require_gh()
    if codespace_auth:
        require_codespace_auth()
