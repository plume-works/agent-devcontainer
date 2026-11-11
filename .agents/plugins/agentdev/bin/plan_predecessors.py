#!/usr/bin/env python3

"""
Find the open pull requests an IWE plan's work branch must be stacked on.

Standard library only.
"""

from __future__ import annotations

import json
from pathlib import Path
import posixpath
import re
import sys
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

import result_codes as rc  # noqa: E402  (path set above so the plugin's bin/ resolves)
from skill_common import print_error, require_git_repo, run_tool, Stop  # noqa: E402

PREFLIGHT_ERROR = 2
NO_PULL_REQUEST = 3
GH_FAILED = 4

USAGE = """\
Find the open pull requests an IWE plan's work branch must be stacked on.

Usage:
  plan_predecessors.py <plan-key> [--remote <name>]

  <plan-key>        data/plans/<YYYYMMDD>-<slug>, read from the checkout.
  --remote <name>   The remote whose repository holds the pull requests.
                    Default: origin
  -h, --help        Show this help text.

Candidates are the plan's own open iwe/<slug>/iter-* pull requests and those of
each plan linked from '## Depends on' that is not 'stage: done' in the
checkout; a section whose text starts with 'None' links none. Each
contributes the top of its chain, walked down base branches. A candidate below
another candidate in the same chain is dropped.

Output (key=value lines):
  RESULT            the last line
  PREDECESSOR=<n>   one per pull request to pass to git-new-branch --depends-on;
                    none means the branch is cut from the default branch

Results (RESULT / exit code):
  SUCCESS            0  The predecessors, possibly none, were printed
  PREFLIGHT_ERROR    2  Bad usage, not a repository, no .iwe/config.toml, or no
                        plan at the key
  NO_PULL_REQUEST    3  A dependency is not shipped and has no open pull request
  GH_FAILED          4  gh could not list the open pull requests
"""

LINK = re.compile(r'\]\(([^)\s]+\.md)\)')
WORK_BRANCH = re.compile(r'iwe/([^/]+)/iter-[1-9][0-9]*-(?:plan|impl|ship)')
DATED_PLAN = re.compile(r'[0-9]{8}-(.+)')


class PullRequest(NamedTuple):
    """An open pull request's number and branches."""

    number: int
    head: str
    base: str


def open_pull_requests(remote_url: str) -> list[PullRequest]:
    """Return every open pull request of the repository `remote_url` names."""
    completed = run_tool(
        'gh', 'pr', 'list', '--repo', remote_url, '--state', 'open', '--limit', '1000',
        '--json', 'number,headRefName,baseRefName',
    )  # fmt: skip
    if completed.returncode != 0:
        print_error(f'gh could not list the open pull requests: {completed.stderr.strip()}')
        raise Stop(GH_FAILED)
    return [
        PullRequest(item['number'], item['headRefName'], item['baseRefName'])
        for item in json.loads(completed.stdout)
    ]


def library_path(root: Path) -> str:
    """Return [workspace].path of the IWE config, relative to `root`; '.' when unset."""
    config = root / '.iwe' / 'config.toml'
    if not config.is_file():
        print_error(f'No .iwe/config.toml at {root}; run from an IWE workspace root.')
        raise Stop(PREFLIGHT_ERROR)
    in_workspace = False
    for line in config.read_text().splitlines():
        if line.startswith('['):
            in_workspace = line.strip() == '[workspace]'
        elif in_workspace and line.split('=', 1)[0].strip() == 'path' and '=' in line:
            return line.split('=', 1)[1].strip().strip('"\'').rstrip('/') or '.'
    return '.'


def depends_on_paths(text: str, plan_path: str) -> list[str]:
    """Return the plan paths linked from the ``## Depends on`` section of `text`."""
    section = re.search(r'^## Depends on[ \t]*$(.*?)(?=^#{1,2} |\Z)', text, re.M | re.S)
    if section is None or section.group(1).lstrip().startswith('None'):
        return []
    plans_dir = posixpath.dirname(plan_path)
    paths = [
        posixpath.normpath(posixpath.join(plans_dir, target))
        for target in LINK.findall(section.group(1))
    ]
    return [path for path in dict.fromkeys(paths) if posixpath.dirname(path) == plans_dir]


def stage_of(path: Path) -> str:
    """Return the frontmatter stage of the plan at `path`; '' when absent or missing."""
    lines = path.read_text().splitlines() if path.is_file() else []
    if not lines or lines[0].strip() != '---':
        return ''
    for line in lines[1:]:
        if line.strip() == '---':
            break
        key, _, value = line.partition(':')
        if key.strip() == 'stage':
            return value.strip().strip('\'"')
    return ''


def slug_of(path: str) -> str:
    """Return the slug of a dated plan path."""
    name = posixpath.basename(path).removesuffix('.md')
    match = DATED_PLAN.fullmatch(name)
    return match.group(1) if match else name


def below(pull: PullRequest, by_head: dict[str, PullRequest]) -> set[int]:
    """Return the numbers of the open pull requests under `pull` in its chain."""
    found: set[int] = set()
    lower = by_head.get(pull.base)
    while lower is not None and lower.number not in found and lower.number != pull.number:
        found.add(lower.number)
        lower = by_head.get(lower.base)
    return found


def chain_tops(slug: str, pulls: list[PullRequest], by_head: dict[str, PullRequest]) -> list[int]:
    """Return the open work pull requests of `slug` that no other one of them sits on."""
    own = [
        pull
        for pull in pulls
        if (match := WORK_BRANCH.fullmatch(pull.head)) and match.group(1) == slug
    ]
    under = set().union(*(below(pull, by_head) for pull in own))
    return [pull.number for pull in own if pull.number not in under]


def predecessors(plan_key: str, remote: str) -> list[int]:
    """Return the pull requests the plan's work branch depends on, ascending."""
    root = require_git_repo()
    library = library_path(root)
    relative = f'{plan_key.removesuffix(".md")}.md'
    plan_path = relative if library == '.' else f'{library}/{relative}'
    if not (root / plan_path).is_file():
        print_error(f'No plan at {plan_path}.')
        raise Stop(PREFLIGHT_ERROR)
    remote_url = run_tool('git', 'remote', 'get-url', remote)
    if remote_url.returncode != 0:
        print_error(f"No remote named '{remote}'.")
        raise Stop(PREFLIGHT_ERROR)
    pulls = open_pull_requests(remote_url.stdout.strip())
    by_head = {pull.head: pull for pull in pulls}
    candidates = chain_tops(slug_of(plan_path), pulls, by_head)
    text = (root / plan_path).read_text()
    for path in depends_on_paths(text, plan_path):
        if stage_of(root / path) == 'done':
            continue
        tops = chain_tops(slug_of(path), pulls, by_head)
        if not tops:
            key = path.removeprefix(f'{library}/').removesuffix('.md')
            print_error(f'{key} is not shipped and has no open pull request to build on.')
            raise Stop(NO_PULL_REQUEST)
        candidates += tops
    numbers = {pull.number: pull for pull in pulls}
    under = set().union(*(below(numbers[number], by_head) for number in candidates))
    return sorted(set(candidates) - under)


def main() -> int:
    """Print the predecessors of the plan the command line names."""
    arguments = sys.argv[1:]
    if any(argument in ('-h', '--help') for argument in arguments):
        print(USAGE)
        return 0
    remote = 'origin'
    if len(arguments) == 3 and arguments[1] == '--remote' and arguments[2]:
        remote = arguments[2]
    elif len(arguments) != 1:
        print(USAGE, file=sys.stderr)
        return PREFLIGHT_ERROR
    try:
        for number in predecessors(arguments[0], remote):
            print(f'PREDECESSOR={number}')
    except Stop as stop:
        return stop.code
    return 0


if __name__ == '__main__':
    rc.RESULT_CODES[NO_PULL_REQUEST] = 'NO_PULL_REQUEST'
    rc.RESULT_CODES[GH_FAILED] = 'GH_FAILED'
    rc.install()
    rc.run(main)
