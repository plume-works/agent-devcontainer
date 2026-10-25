#!/usr/bin/env python3

"""
Name an IWE plan's work branches and read the plan's state at the remote default branch.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import result_codes as rc  # noqa: E402  (path set above so the plugin's bin/ resolves)

USAGE = """\
Name an IWE plan's work branches <phase>/<slug>/iteration-<N> and read the
plan's state at the remote default branch. Creates, switches, and deletes no
branch.

Usage:
  iwe-branch-name.py parse <branch>
  iwe-branch-name.py plan-state <plan-key|slug> [--remote <name>]
  iwe-branch-name.py next <plan-key|slug> [--phase impl|ship] [--remote <name>]

Arguments:
  <branch>          A branch name to split into phase, slug, and iteration.
  <plan-key|slug>   data/plans/<YYYYMMDD>-<slug>, <YYYYMMDD>-<slug>, or <slug>.

Options:
  --remote <name>   The remote whose default branch holds the plan and whose
                    branches count as used iterations. Default: origin.
  --phase <phase>   next only: impl or ship, naming the next iteration of that
                    phase without reading the plan.
  -h, --help        Show this help text.

Output (key=value lines):
  RESULT
  parse:       PHASE, SLUG, ITERATION
  plan-state:  DEFAULT_BRANCH, PLAN_STATE (missing | cancelled | done | complete
               | incomplete), and PLAN_KEY when the plan exists
  next:        NEXT, NEXT_KIND (default | impl | ship), and ITERATION for a
               work branch; without --phase also the plan-state keys

Without --phase, next names the default branch for a done, cancelled, or
missing plan, the next ship iteration for a complete one, and the next impl
iteration for an incomplete one. The next iteration is one more than the
highest used for the phase and slug across local branches, the remote's
branches, and the repository's pull requests in any state.

Results (RESULT / exit code):
  SUCCESS            0  The name's parts, the plan's state, or the next name was reported
  NOT_A_WORK_BRANCH  3  parse: the branch is not <impl|ship>/<slug>/iteration-<N>
  AMBIGUOUS_PLAN     4  The slug matches more than one plan at the default branch
  FETCH_FAILED       5  The remote could not be fetched or its branches listed
  GH_UNAVAILABLE     6  gh is missing, unauthenticated, or its pull-request query failed
  PREFLIGHT_ERROR    2  Usage error, not a git repository, no .iwe/config.toml,
                        or the remote's default branch is unknown
  SCRIPT_FAILURE     1  Unhandled error
  SIGNAL_HUP       129  Interrupted by HUP
  SIGNAL_INT       130  Interrupted by INT
  SIGNAL_TERM      143  Interrupted by TERM\
"""

PREFLIGHT_ERROR = 2
NOT_A_WORK_BRANCH = 3
AMBIGUOUS_PLAN = 4
FETCH_FAILED = 5
GH_UNAVAILABLE = 6

PHASES = ('impl', 'ship')
WORK_BRANCH = re.compile(r'(impl|ship)/([^/]+)/iteration-([1-9][0-9]*)')
DATED_PLAN = re.compile(r'([0-9]{8})-(.+)')
# The task sections the repository's plan-checkbox gate also reads.
TASK_SECTIONS = ('## Implementation Steps', '## Tasks')
DEFAULT_BRANCH_HELPER = Path(__file__).resolve().parents[3] / 'bin' / 'git-default-branch.sh'


class WorkBranch(NamedTuple):
    """A branch name split into its parts."""

    phase: str
    slug: str
    iteration: int


class Options(NamedTuple):
    """The parsed command line."""

    command: str
    target: str
    remote: str
    phase: str


class PlanState(NamedTuple):
    """A plan as the remote default branch holds it."""

    default_branch: str
    state: str
    key: str


class Stop(Exception):
    """End the run with a declared result after the diagnostic was printed."""

    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.code = code


def print_error(message: str) -> None:
    """Report a failure on stderr in the shared ERROR: form."""
    print(f'ERROR: {message}', file=sys.stderr)


def run_tool(*arguments: str) -> subprocess.CompletedProcess[str]:
    """Run a command, capturing its output, without raising on failure."""
    return subprocess.run(list(arguments), check=False, capture_output=True, text=True)


def parse_work_branch(branch: str) -> WorkBranch | None:
    """Split `branch` into phase, slug, and iteration, or None when off the shape."""
    match = WORK_BRANCH.fullmatch(branch)
    if match is None:
        return None
    return WorkBranch(match.group(1), match.group(2), int(match.group(3)))


def plan_name(target: str) -> str:
    """Strip an optional data/plans/ prefix and .md suffix from a plan argument."""
    name = target.removeprefix('data/plans/')
    return name.removesuffix('.md')


def slug_of(target: str) -> str:
    """Return the slug of a plan key, a dated plan name, or a bare slug."""
    name = plan_name(target)
    match = DATED_PLAN.fullmatch(name)
    return match.group(2) if match else name


def library_from_config(config_file: Path) -> str:
    """Read [workspace].path, or pre-v4 [library].path, from an IWE config; '' when absent."""
    in_library = False
    for line in config_file.read_text().splitlines():
        if line.startswith('['):
            in_library = line.strip() in ('[workspace]', '[library]')
            continue
        if in_library and line.split('=', 1)[0].strip() == 'path' and '=' in line:
            return line.split('=', 1)[1].strip().replace('"', '').replace("'", '')
    return ''


def repository_root() -> Path:
    """Return the repository's top level, or stop when not inside one."""
    completed = run_tool('git', 'rev-parse', '--show-toplevel')
    if completed.returncode != 0:
        print_error('This script must be run inside a Git repository.')
        raise Stop(PREFLIGHT_ERROR)
    return Path(completed.stdout.strip())


def library_path(root: Path) -> str:
    """Return the IWE library directory relative to `root`, or stop without a config."""
    config_file = root / '.iwe' / 'config.toml'
    if not config_file.is_file():
        print_error(f'No .iwe/config.toml at {root}; run from an IWE workspace root.')
        raise Stop(PREFLIGHT_ERROR)
    return (library_from_config(config_file) or '.').rstrip('/')


def require_remote(remote: str) -> str:
    """Return the URL of `remote`, or stop with a preflight error when it is not configured."""
    completed = run_tool('git', 'remote', 'get-url', remote)
    if completed.returncode != 0:
        print_error(f"No remote named '{remote}'.")
        raise Stop(PREFLIGHT_ERROR)
    return completed.stdout.strip()


def remote_default_branch(remote: str) -> str:
    """Resolve the remote's default branch through the shared shell helper."""
    completed = run_tool(
        'bash',
        '-c',
        'source "$1" && remote_default_branch "$2"',
        'git-default-branch',
        str(DEFAULT_BRANCH_HELPER),
        remote,
    )
    name = completed.stdout.strip()
    if completed.returncode != 0 or not name:
        print_error(
            f"Cannot tell the default branch of '{remote}': set it with "
            f'`git remote set-head {remote} --auto`.'
        )
        raise Stop(PREFLIGHT_ERROR)
    return name


def fetch_default_branch(remote: str, branch: str) -> str:
    """Fetch the remote's default branch and return its remote-tracking ref."""
    completed = run_tool('git', 'fetch', '--quiet', remote, branch)
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)
        print_error(f"Failed to fetch '{branch}' from remote '{remote}'.")
        raise Stop(FETCH_FAILED)
    ref = f'refs/remotes/{remote}/{branch}'
    if run_tool('git', 'rev-parse', '--verify', '--quiet', f'{ref}^{{commit}}').returncode != 0:
        print_error(f"Fetched '{branch}' from '{remote}' but {ref} does not exist.")
        raise Stop(FETCH_FAILED)
    return ref


def find_plan(ref: str, library: str, target: str) -> str:
    """Return the path of the plan `target` names in `ref`'s tree, or '' when missing."""
    plans_dir = 'data/plans' if library == '.' else f'{library}/data/plans'
    listing = run_tool('git', 'ls-tree', '--name-only', f'{ref}:{plans_dir}')
    names = listing.stdout.splitlines() if listing.returncode == 0 else []
    name = plan_name(target)
    if DATED_PLAN.fullmatch(name):
        matches = [entry for entry in names if entry == f'{name}.md']
    else:
        matches = [
            entry
            for entry in names
            if (dated := DATED_PLAN.fullmatch(entry.removesuffix('.md')))
            and entry.endswith('.md')
            and dated.group(2) == name
        ]
    if len(matches) > 1:
        print_error(f"Slug '{name}' matches more than one plan: {', '.join(sorted(matches))}.")
        raise Stop(AMBIGUOUS_PLAN)
    return f'{plans_dir}/{matches[0]}' if matches else ''


def frontmatter_stage(lines: list[str]) -> str:
    """Return the frontmatter `stage` value, or '' when the plan carries none."""
    if not lines or lines[0].strip() != '---':
        return ''
    for line in lines[1:]:
        if line.strip() == '---':
            break
        key, separator, value = line.partition(':')
        if separator and key.strip() == 'stage':
            return value.strip().strip('\'"')
    return ''


def task_checkboxes(lines: list[str]) -> list[bool]:
    """Return each task checkbox under a task section as ticked or not."""
    boxes: list[bool] = []
    in_steps = False
    in_fence = False
    for line in lines:
        if line.lstrip().startswith('```'):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if line.startswith('## '):
            in_steps = line.strip() in TASK_SECTIONS
            continue
        if in_steps:
            box = re.match(r'\s*[-*] \[([ xX])\]', line)
            if box:
                boxes.append(box.group(1) != ' ')
    return boxes


def classify_plan(text: str) -> str:
    """Return a plan document's state from its stage and its task checkboxes."""
    lines = text.splitlines()
    stage = frontmatter_stage(lines)
    if stage in ('done', 'cancelled'):
        return stage
    boxes = task_checkboxes(lines)
    return 'complete' if boxes and all(boxes) else 'incomplete'


def read_plan_state(target: str, remote: str) -> PlanState:
    """Fetch the remote default branch and read the plan `target` names there."""
    root = repository_root()
    library = library_path(root)
    require_remote(remote)
    default_branch = remote_default_branch(remote)
    ref = fetch_default_branch(remote, default_branch)
    path = find_plan(ref, library, target)
    if not path:
        return PlanState(default_branch, 'missing', '')
    text = run_tool('git', 'cat-file', 'blob', f'{ref}:{path}').stdout
    plans_dir = path.rsplit('/', 1)[0]
    key = f'data/plans/{path.removeprefix(plans_dir + "/").removesuffix(".md")}'
    return PlanState(default_branch, classify_plan(text), key)


def print_plan_state(plan: PlanState) -> None:
    """Print the plan-state keys."""
    print(f'DEFAULT_BRANCH={plan.default_branch}')
    if plan.key:
        print(f'PLAN_KEY={plan.key}')
    print(f'PLAN_STATE={plan.state}')


def local_branches() -> list[str]:
    """Return the repository's local branch names."""
    completed = run_tool('git', 'for-each-ref', '--format=%(refname:short)', 'refs/heads/')
    return completed.stdout.splitlines()


def remote_branches(remote: str) -> list[str]:
    """Return the remote's branch names, or stop when it cannot be listed."""
    completed = run_tool('git', 'ls-remote', '--heads', remote)
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)
        print_error(f"Failed to list the branches of remote '{remote}'.")
        raise Stop(FETCH_FAILED)
    return [
        line.split('\t', 1)[1].removeprefix('refs/heads/')
        for line in completed.stdout.splitlines()
        if '\t' in line
    ]


def pull_request_heads(phase: str, slug: str, remote_url: str) -> list[str]:
    """Return the heads of the remote repository's pull requests, or stop when gh cannot say."""
    if shutil.which('gh') is None:
        print_error('gh is not installed; a merged pull request may already hold the next name.')
        raise Stop(GH_UNAVAILABLE)
    completed = run_tool(
        'gh', 'pr', 'list', '--repo', remote_url, '--state', 'all',
        '--search', f'head:{phase}/{slug}/',
        '--limit', '1000', '--json', 'headRefName', '--jq', '.[].headRefName',
    )  # fmt: skip
    if completed.returncode != 0:
        sys.stderr.write(completed.stderr)
        print_error(
            f'gh could not list pull requests of {remote_url}; run `gh auth status` to check the '
            'login, or the remote may not be a GitHub repository.'
        )
        raise Stop(GH_UNAVAILABLE)
    return completed.stdout.splitlines()


def next_iteration(phase: str, slug: str, remote: str) -> int:
    """Return one more than the highest iteration of `phase` and `slug` already used."""
    remote_url = require_remote(remote)
    names = [
        *local_branches(),
        *remote_branches(remote),
        *pull_request_heads(phase, slug, remote_url),
    ]
    used = [
        branch.iteration
        for name in names
        if (branch := parse_work_branch(name.strip())) and branch[:2] == (phase, slug)
    ]
    return max(used, default=0) + 1


def run_next(options: Options) -> int:
    """Print the next branch name for the plan, from --phase or from its state."""
    repository_root()
    phase = options.phase
    slug = slug_of(options.target)
    if not phase:
        plan = read_plan_state(options.target, options.remote)
        print_plan_state(plan)
        if plan.state not in ('complete', 'incomplete'):
            print(f'NEXT={plan.default_branch}')
            print('NEXT_KIND=default')
            return 0
        phase = 'ship' if plan.state == 'complete' else 'impl'
        slug = slug_of(plan.key)
    iteration = next_iteration(phase, slug, options.remote)
    print(f'NEXT={phase}/{slug}/iteration-{iteration}')
    print(f'NEXT_KIND={phase}')
    print(f'ITERATION={iteration}')
    return 0


def parse_arguments(argv: list[str]) -> Options | None:
    """Return the parsed options, or None after printing why the usage is wrong."""
    if not argv or argv[0] not in ('parse', 'plan-state', 'next'):
        print_error('Expected a subcommand: parse, plan-state, or next.')
        return None
    command, positional = argv[0], []
    remote, phase = 'origin', ''
    rest = iter(argv[1:])
    for argument in rest:
        if argument in ('--remote', '--phase') and command != 'parse':
            value = next(rest, '')
            if not value:
                print_error(f'Missing value for {argument}.')
                return None
            if argument == '--remote':
                remote = value
            elif command == 'next' and value in PHASES:
                phase = value
            else:
                print_error(f'--phase takes impl or ship and applies to next only: {value}.')
                return None
        elif argument.startswith('-'):
            print_error(f'Unknown option: {argument}.')
            return None
        else:
            positional.append(argument)
    if len(positional) != 1 or not positional[0]:
        print_error(f'{command} takes exactly one argument.')
        return None
    return Options(command, positional[0], remote, phase)


def main() -> int:
    """Dispatch the subcommand and report its result."""
    if any(argument in ('-h', '--help') for argument in sys.argv[1:]):
        print(USAGE)
        return 0
    options = parse_arguments(sys.argv[1:])
    if options is None:
        print(USAGE, file=sys.stderr)
        return PREFLIGHT_ERROR
    try:
        if options.command == 'parse':
            return run_parse(options.target)
        if options.command == 'next':
            return run_next(options)
        print_plan_state(read_plan_state(options.target, options.remote))
        return 0
    except Stop as stop:
        return stop.code


def run_parse(branch: str) -> int:
    """Print the parts of a work branch name."""
    work_branch = parse_work_branch(branch)
    if work_branch is None:
        print_error(f"'{branch}' is not <impl|ship>/<slug>/iteration-<N>.")
        return NOT_A_WORK_BRANCH
    print(f'PHASE={work_branch.phase}')
    print(f'SLUG={work_branch.slug}')
    print(f'ITERATION={work_branch.iteration}')
    return 0


if __name__ == '__main__':
    rc.RESULT_CODES[NOT_A_WORK_BRANCH] = 'NOT_A_WORK_BRANCH'
    rc.RESULT_CODES[AMBIGUOUS_PLAN] = 'AMBIGUOUS_PLAN'
    rc.RESULT_CODES[FETCH_FAILED] = 'FETCH_FAILED'
    rc.RESULT_CODES[GH_UNAVAILABLE] = 'GH_UNAVAILABLE'
    rc.install()
    rc.run(main)
