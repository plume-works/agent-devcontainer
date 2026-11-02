#!/usr/bin/env python3
"""
Choose what the CI pre-commit job checks for the triggering GitHub event.

Writes ``from_ref``, ``to_ref``, ``all_files``, and ``gitleaks_log_opts`` to ``GITHUB_OUTPUT``.
A range that changes a tool-version owner checks every file, so a formatter bump fails at the
pull request that made it; gitleaks still scans only the range's commits. See spec/pre-commit-gate.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
import os
from pathlib import Path
import subprocess
import sys

TOOL_VERSION_OWNERS = (
    'uv.lock',
    'pyproject.toml',
    '.pre-commit-config.yaml',
    'ansible/roles/dev_tools/defaults/main.yml',
    'devcontainer-compose-pins.yml',
)
ZERO_SHA = '0' * 40


class RangeError(Exception):
    """An event this job cannot choose a check for."""


def _event_range(event_name: str, event: Mapping[str, object]) -> tuple[str, str] | None:
    """Return the event's (from, to) commits, or None when it checks every file."""
    if event_name == 'pull_request':
        pull = event['pull_request']
        return pull['base']['sha'], pull['head']['sha']  # type: ignore[index]
    if event_name == 'merge_group':
        group = event['merge_group']
        return group['base_sha'], group['head_sha']  # type: ignore[index]
    if event_name == 'push':
        before, after = str(event['before']), str(event['after'])
        return None if before == ZERO_SHA else (before, after)
    if event_name == 'workflow_dispatch':
        return None
    raise RangeError(f'unsupported event: {event_name}')


def _changed_files(from_ref: str, to_ref: str, cwd: Path) -> set[str]:
    """Return the files the range changed, diffed from the merge base as pre-commit does."""
    diff = subprocess.run(
        ['git', 'diff', '--name-only', '--no-ext-diff', f'{from_ref}...{to_ref}'],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    )
    return set(diff.stdout.splitlines())


def outputs(event_name: str, event: Mapping[str, object], cwd: Path) -> dict[str, str]:
    """Return the job's outputs for one event."""
    commits = _event_range(event_name, event)
    if commits is None:
        log_opts = f'-1 {event["after"]}' if event_name == 'push' else '--all'
        return {'from_ref': '', 'to_ref': '', 'all_files': 'true', 'gitleaks_log_opts': log_opts}
    from_ref, to_ref = commits
    touches_owner = not _changed_files(from_ref, to_ref, cwd).isdisjoint(TOOL_VERSION_OWNERS)
    return {
        'from_ref': from_ref,
        'to_ref': to_ref,
        'all_files': 'true' if touches_owner else 'false',
        'gitleaks_log_opts': f'{from_ref}..{to_ref}',
    }


def main(env: Mapping[str, str] | None = None, cwd: Path | None = None) -> int:
    """Write the outputs for the event GitHub Actions describes in the environment."""
    env = os.environ if env is None else env
    try:
        event = json.loads(Path(env['GITHUB_EVENT_PATH']).read_text())
        values = outputs(env['GITHUB_EVENT_NAME'], event, cwd or Path.cwd())
    except (RangeError, KeyError, subprocess.CalledProcessError) as error:
        print(f'pre-commit-ci-range: {error}', file=sys.stderr)
        return 1
    with open(env['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
        for name, value in values.items():
            output.write(f'{name}={value}\n')
            print(f'{name}={value}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
