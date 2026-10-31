#!/usr/bin/env python3

"""
Diff this repository's copy of the agent-devcontainer template against the upstream template.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import result_codes as rc  # noqa: E402  (path set above so the plugin's bin/ resolves)
from skill_common import help_header, print_error, require_git_repo, run_tool, Stop  # noqa: E402

NO_MARKER = 3
UP_TO_DATE = 4
CHANGES_FOUND = 5
CLONE_FAILED = 6
INVALID_MARKER = 7
PREFLIGHT_ERROR = 2

MARKER_NAME = '.agent.metadata.json'
SECTION = 'template-consume'

DESCRIPTION = (
    "Diff this repository's copy of the agent-devcontainer template against the upstream "
    "repository's current default branch."
)

USAGE = """
Usage:
  check-updates.py [--repo <owner/name>] [--repo-url <url>] [--root <path>]

Options:
  --repo <owner/name>  Template source repository, recorded for display.
                       Default: plume-works/agent-devcontainer
  --repo-url <url>     Clone URL to fetch, when it differs from https://github.com/<repo>.git
                        (a fork, a GitHub Enterprise host, or a local path).
  --root <path>        Consumer repository root. Default: discovered via `git rev-parse`.
  -h, --help           Show this help text.

Reads the template-consume section of .agent.metadata.json at the consumer repository root,
shallow-clones the template repository's default branch into ./.tmp/, and lists
which files under template-owned paths changed between the marker's consumed_ref
and the upstream HEAD. Prints nothing about paths this consumer already deleted.

Output (key=value lines):
  RESULT, CONSUMED_REF, UPSTREAM_REF
  On CHANGES_FOUND also: CHANGED_PATHS (newline-indented list)

Results (RESULT / exit code):
  UP_TO_DATE      4  consumed_ref already matches the upstream default branch
  CHANGES_FOUND   5  One or more files under tracked template paths changed upstream
  NO_MARKER       3  No .agent.metadata.json or template-consume section; run setup mode first
  INVALID_MARKER  7  Marker file exists but is not valid JSON or is missing consumed_ref
  CLONE_FAILED    6  Could not fetch the template repository
  PREFLIGHT_ERROR 2  Usage or preflight error (not a repo)
  SCRIPT_FAILURE  1  Unhandled error

Examples:
  agent-code/check-updates.py
  agent-code/check-updates.py --repo plume-works/agent-devcontainer
  agent-code/check-updates.py --repo-url git@github.com:my-org/agent-devcontainer.git
"""

OPTIONS = ('--repo', '--repo-url', '--root')


def usage() -> str:
    """Return the full help text."""
    return help_header(DESCRIPTION, __file__) + USAGE


def parse_arguments(arguments: list[str]) -> dict[str, str]:
    """Return the option values, stopping at a usage error or help."""
    values = {'--repo': 'plume-works/agent-devcontainer', '--repo-url': '', '--root': ''}
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument in OPTIONS:
            if not remaining:
                print_error(f'Missing value for {argument}')
                raise Stop(PREFLIGHT_ERROR)
            values[argument] = remaining.pop(0)
        elif argument in ('-h', '--help'):
            print(usage(), end='')
            raise Stop(0)
        else:
            print_error(f'Unknown argument: {argument}')
            print(usage(), end='', file=sys.stderr)
            raise Stop(PREFLIGHT_ERROR)
    return values


def jq_text(value: Any) -> str:
    """Return a JSON value as `jq -r` prints it."""
    return value if isinstance(value, str) else json.dumps(value)


def read_marker(marker_path: Path) -> tuple[str, list[str]]:
    """Return consumed_ref and tracked_paths, stopping on a missing or invalid section."""
    try:
        marker = json.loads(marker_path.read_text())
    except (json.JSONDecodeError, UnicodeDecodeError):
        marker = None
        valid = False
    else:
        valid = marker is not None and marker is not False
    if not valid:
        print_error(f'{MARKER_NAME} is not valid JSON.')
        raise Stop(INVALID_MARKER)
    if not isinstance(marker, dict) or not isinstance(marker.get(SECTION), dict):
        print_error(f'No {SECTION} section in {MARKER_NAME}. Run setup mode first.')
        raise Stop(NO_MARKER)
    section = marker[SECTION]
    consumed_ref = section.get('consumed_ref')
    consumed_ref = '' if consumed_ref in (None, False) else jq_text(consumed_ref)
    tracked_paths = section.get('tracked_paths')
    if not consumed_ref or not isinstance(tracked_paths, list) or not tracked_paths:
        print_error(
            f'The {SECTION} section in {MARKER_NAME} is missing consumed_ref or tracked_paths.'
        )
        raise Stop(INVALID_MARKER)
    return consumed_ref, [jq_text(path) for path in tracked_paths]


def changed_paths(
    clone_dir: str, consumer_root: Path, consumed_ref: str, upstream_ref: str, tracked: list[str]
) -> list[str]:
    """Return changed files under tracked paths, skipping ones the consumer deleted."""
    changed: list[str] = []
    for path in tracked:
        diff = run_tool(
            'git', '-C', clone_dir, 'diff', '--name-only', consumed_ref, upstream_ref, '--', path
        )
        for changed_path in diff.stdout.splitlines():
            if not changed_path:
                continue
            local = consumer_root / changed_path
            existed = (
                run_tool(
                    'git', '-C', clone_dir, 'cat-file', '-e', f'{consumed_ref}:{changed_path}'
                ).returncode
                == 0
            )
            if existed and not local.exists() and not local.is_symlink():
                continue
            if changed_path not in changed:
                changed.append(changed_path)
    return changed


def compare(
    values: dict[str, str], consumer_root: Path, clone_dir: str, marker: tuple[str, list[str]]
) -> int:
    """Clone the template and report what changed since the consumed commit."""
    consumed_ref, tracked = marker
    repo_url = values['--repo-url'] or f'https://github.com/{values["--repo"]}.git'
    clone = run_tool('git', 'clone', '--quiet', '--filter=blob:none', repo_url, clone_dir)
    if clone.returncode != 0:
        print_error(f'Failed to clone {repo_url} into {clone_dir}.')
        return CLONE_FAILED

    upstream_ref = run_tool('git', '-C', clone_dir, 'rev-parse', 'HEAD').stdout.strip()
    print(f'CONSUMED_REF={consumed_ref}')
    print(f'UPSTREAM_REF={upstream_ref}')
    if consumed_ref == upstream_ref:
        return UP_TO_DATE
    if run_tool('git', '-C', clone_dir, 'cat-file', '-e', consumed_ref).returncode != 0:
        print_error(
            f'consumed_ref {consumed_ref} is not reachable in {values["--repo"]}; '
            "it may predate this clone's history."
        )
        return INVALID_MARKER

    changed = changed_paths(clone_dir, consumer_root, consumed_ref, upstream_ref, tracked)
    if not changed:
        return UP_TO_DATE
    print(f'CHANGED_PATHS={len(changed)}')
    for path in changed:
        print(f'  {path}')
    return CHANGES_FOUND


def run(arguments: list[str]) -> int:
    """Check the consumer's template copy against the upstream default branch."""
    values = parse_arguments(arguments)
    root = values['--root']
    if not root:
        consumer_root = require_git_repo()
    elif run_tool('git', '-C', root, 'rev-parse', '--show-toplevel').returncode != 0:
        print_error(f'--root {root} is not inside a Git repository.')
        return PREFLIGHT_ERROR
    else:
        consumer_root = Path(root)

    marker_path = consumer_root / MARKER_NAME
    if not marker_path.is_file():
        print_error(f'No {MARKER_NAME} at {consumer_root}. Run setup mode first.')
        return NO_MARKER
    marker = read_marker(marker_path)

    tmp_root = consumer_root / '.tmp'
    tmp_root.mkdir(parents=True, exist_ok=True)
    clone_dir = tempfile.mkdtemp(prefix='template-consume.', dir=tmp_root)
    try:
        return compare(values, consumer_root, clone_dir, marker)
    finally:
        shutil.rmtree(clone_dir, ignore_errors=True)


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES.update(
        {
            NO_MARKER: 'NO_MARKER',
            UP_TO_DATE: 'UP_TO_DATE',
            CHANGES_FOUND: 'CHANGES_FOUND',
            CLONE_FAILED: 'CLONE_FAILED',
            INVALID_MARKER: 'INVALID_MARKER',
        }
    )
    rc.install()
    rc.run(main)
