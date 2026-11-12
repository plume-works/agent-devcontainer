#!/usr/bin/env python3

"""
Look up and save the one saved Verify report per plan, keyed by its inputs and catalog digest.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import result_codes as rc  # noqa: E402  (path set above so the plugin's bin/ resolves)

USAGE = """\
Look up or save the one saved Verify report for a plan or for audit mode,
keyed by the content Verify judged and the digest of the active agentdev
catalog. Run from inside the repository being verified.

Usage:
  verify-cache.py lookup <plan-key|audit> [--fresh]
  verify-cache.py save <plan-key|audit> --key <key> --verdict <verdict>
                  --skill-request <text> --verifier-prompt <text> < report

Arguments:
  <plan-key|audit>  data/plans/<YYYYMMDD>-<slug>, an archived plan's key
                    data/archive/<release>/plans/<YYYYMMDD>-<slug>, either's
                    file path, or audit.

Options:
  --fresh           lookup only: report a miss even when a saved report matches.
  --key <key>       save only: the KEY the lookup's miss printed.
  --verdict <v>     save only: Ready to ship, Blocked, or Audit. A Needs
                    decision report is never saved.
  --skill-request <text>
                    save only: the request the iwe-verify skill was invoked
                    with, verbatim.
  --verifier-prompt <text>
                    save only: the prompt iwe-verifier was dispatched with,
                    verbatim.
  -h, --help        Show this help text.

Output (key=value lines):
  RESULT
  lookup HIT:   REPORT (the saved report's path), KEY, VERDICT
  lookup MISS:  KEY, CATALOG_DIGEST
  save:         REPORT

The saved report lives at .tmp/verify/<plan file name>.md, or
.tmp/verify/audit.md, under the repository root, and each save overwrites it.
A plan's key hashes its body, without frontmatter or `## Ship review` and with
links resolved from the repository root, and the committed content of every
path the plan names; a plan found under data/plans/ or the archive shares one
key. Audit mode's key is the commit's tree.
Both prompts are recorded in its frontmatter as block scalars; they are not
part of the key.
A dirty worktree is any tracked change or any untracked file Git does not
ignore; the cache directory ignores itself.

Results (RESULT / exit code):
  SUCCESS            0  save: the report was saved; or help was printed
  HIT                3  lookup: the saved report matches the key and the catalog
  MISS               4  lookup: no saved report matches, or --fresh was given
  DIRTY_WORKTREE     5  The worktree has a tracked change or an unignored file
  INPUTS_CHANGED     6  save: the key is no longer the --key the lookup printed
  PREFLIGHT_ERROR    2  Usage error, a disallowed verdict, not a git
                        repository, a repository with no commit, or no plan
                        file, or more than one, for the plan key
  SCRIPT_FAILURE     1  Unhandled error
  SIGNAL_HUP       129  Interrupted by HUP
  SIGNAL_INT       130  Interrupted by INT
  SIGNAL_TERM      143  Interrupted by TERM\
"""

PREFLIGHT_ERROR = 2
HIT = 3
MISS = 4
DIRTY_WORKTREE = 5
INPUTS_CHANGED = 6

AUDIT = 'audit'
ARCHIVED_PLAN = re.compile(r'data/archive/[^/]+/plans/[^/]+$')
SAVED_VERDICTS = ('Ready to ship', 'Blocked', 'Audit')
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
CACHE_DIRECTORY = Path('.tmp') / 'verify'
FRONTMATTER = re.compile(r'---\n(.*?)\n---\n', re.DOTALL)
SHIP_REVIEW = re.compile(r'^## Ship review[ \t]*$.*?(?=^## |\Z)', re.M | re.S)
LINK_TARGET = re.compile(r'\]\(([^)\s#]+)')
PATH_TOKEN = re.compile(r'[\w.-]+(?:/[\w.-]+)*/?')
CODE = re.compile(r'```.*?```|`[^`\n]+`', re.S)
SAVE_FLAGS = ('--key', '--verdict', '--skill-request', '--verifier-prompt')


class Options(NamedTuple):
    """The parsed command line."""

    command: str
    target: str
    fresh: bool
    key: str
    verdict: str
    skill_request: str
    verifier_prompt: str


class Stop(Exception):
    """End the run with a declared result after the diagnostic was printed."""

    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.code = code


def print_error(message: str) -> None:
    """Report a failure on stderr in the shared ERROR: form."""
    print(f'ERROR: {message}', file=sys.stderr)


def git(*arguments: str) -> str:
    """Return a git command's stripped stdout, or stop with PREFLIGHT_ERROR."""
    completed = subprocess.run(['git', *arguments], check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        print_error(completed.stderr.strip() or f'git {" ".join(arguments)} failed.')
        raise Stop(PREFLIGHT_ERROR)
    return completed.stdout.strip()


def parse_arguments(arguments: list[str]) -> Options | None:
    """Parse the command line, or return None on a usage error."""
    if len(arguments) < 2 or arguments[0] not in ('lookup', 'save'):
        return None
    command, target, rest = arguments[0], arguments[1], arguments[2:]
    fresh = False
    values: dict[str, str] = {}
    while rest:
        flag = rest.pop(0)
        if command == 'lookup' and flag == '--fresh':
            fresh = True
        elif command == 'save' and flag in SAVE_FLAGS and rest:
            values[flag] = rest.pop(0)
        else:
            return None
    if command == 'save' and not all(values.get(flag) for flag in SAVE_FLAGS):
        return None
    key, verdict, skill_request, verifier_prompt = (values.get(flag, '') for flag in SAVE_FLAGS)
    return Options(
        command, canonical_target(target), fresh, key, verdict, skill_request, verifier_prompt
    )


def canonical_target(target: str) -> str:
    """Normalize a plan key or file path to its live or archived plan key; audit stays audit."""
    if target == AUDIT:
        return AUDIT
    archived = ARCHIVED_PLAN.search(Path(target).with_suffix('').as_posix())
    return archived.group(0) if archived else f'data/plans/{Path(target).stem}'


def catalog_digest(root: Path = PLUGIN_ROOT) -> str:
    """Fingerprint every file of the active catalog, skipping bytecode caches."""
    digest = hashlib.sha256()
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if '__pycache__' in relative.parts or not path.is_file():
            continue
        digest.update(relative.as_posix().encode() + b'\0')
        digest.update(hashlib.sha256(path.read_bytes()).digest())
    return f'sha256:{digest.hexdigest()}'


def plan_file(root: Path, target: str) -> Path:
    """Find the one tracked plan file named like `target`, live or archived."""
    name = f'{Path(target).name}.md'
    found = git('ls-files', '--', f':(glob)**/plans/{name}', f':(glob)plans/{name}').splitlines()
    if len(found) != 1:
        print_error(f'Expected one tracked plan file {name}, found {len(found) or "none"}.')
        raise Stop(PREFLIGHT_ERROR)
    return root / found[0]


def named_paths(root: Path, body: str) -> list[str]:
    """Return every repository path, other than the root, a link or code in `body` names."""
    named = [*CODE.findall(body), *(target.lstrip('/') for target in LINK_TARGET.findall(body))]
    paths = set()
    for token in PATH_TOKEN.findall('\n'.join(named)):
        path = Path(os.path.normpath(root / token))
        if path != root and path.is_relative_to(root) and os.path.lexists(path):
            paths.add(path.relative_to(root).as_posix())
    return sorted(paths)


def plan_key(root: Path, plan: Path) -> str:
    """Hash the plan's body and the committed content of every path it names."""
    text = plan.read_text(encoding='utf-8')
    frontmatter = FRONTMATTER.match(text)
    body = SHIP_REVIEW.sub('', text[frontmatter.end() :] if frontmatter else text).strip()

    def from_root(match: re.Match[str]) -> str:
        target = match.group(1)
        if '://' in target or target.startswith('mailto:'):
            return match.group(0)
        resolved = Path(os.path.normpath(plan.parent / target))
        return (
            f'](/{resolved.relative_to(root).as_posix()}'
            if resolved.is_relative_to(root)
            else match.group(0)
        )

    body = LINK_TARGET.sub(from_root, body)
    own = plan.relative_to(root).as_posix()
    paths = [path for path in named_paths(root, body) if path != own]
    listing = git('ls-files', '--stage', '--', *paths) if paths else ''
    digest = hashlib.sha256(body.encode() + b'\0' + listing.encode())
    return f'sha256:{digest.hexdigest()}'


def content_key(root: Path, target: str) -> str:
    """Return the key of what Verify judges for `target`."""
    if target == AUDIT:
        return f'tree:{git("rev-parse", "HEAD^{tree}")}'
    return plan_key(root, plan_file(root, target))


def require_clean_worktree() -> None:
    """Stop with DIRTY_WORKTREE when a tracked change or unignored file exists."""
    status = git('status', '--porcelain', '--untracked-files=normal')
    if status:
        print_error(f'The worktree is dirty:\n{status}')
        raise Stop(DIRTY_WORKTREE)


def read_frontmatter(path: Path) -> dict[str, str]:
    """Return a saved report's frontmatter fields, or nothing when unreadable."""
    try:
        match = FRONTMATTER.match(path.read_text(encoding='utf-8'))
    except OSError:
        return {}
    if match is None:
        return {}
    # Indented lines belong to a block scalar, which holds no key field.
    lines = (line for line in match.group(1).splitlines() if not line.startswith(' '))
    return {key: value for key, _, value in (line.partition(': ') for line in lines)}


def block_scalar(key: str, text: str) -> str:
    """Render `text` as a YAML literal block that keeps every line verbatim."""
    body = ''.join(f'  {line}\n' if line else '\n' for line in text.rstrip('\n').split('\n'))
    return f'{key}: |2-\n{body}'


def run_lookup(options: Options, root: Path, report: Path) -> int:
    """Report the saved report when it matches the content key and the active catalog."""
    require_clean_worktree()
    key = content_key(root, options.target)
    digest = catalog_digest()
    saved = read_frontmatter(report)
    matches = saved.get('key') == key and saved.get('catalog_digest') == digest
    if matches and not options.fresh:
        print(f'REPORT={report}')
        print(f'KEY={key}')
        print(f'VERDICT={saved.get("verdict", "")}')
        return HIT
    print(f'KEY={key}')
    print(f'CATALOG_DIGEST={digest}')
    return MISS


def run_save(options: Options, root: Path, report: Path) -> int:
    """Overwrite the saved report with stdin, stamped with its key and digest."""
    if options.verdict not in SAVED_VERDICTS:
        print_error(f"Verdict '{options.verdict}' is not saved; use one of {SAVED_VERDICTS}.")
        return PREFLIGHT_ERROR
    require_clean_worktree()
    if content_key(root, options.target) != options.key:
        print_error(f'The content Verify judged changed since the lookup printed {options.key}.')
        return INPUTS_CHANGED
    body = sys.stdin.read()
    report.parent.mkdir(parents=True, exist_ok=True)
    (report.parent / '.gitignore').write_text('*\n', encoding='utf-8')
    saved_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    report.write_text(
        '---\n'
        f'plan: {options.target}\n'
        f'key: {options.key}\n'
        f'catalog_digest: {catalog_digest()}\n'
        f'verdict: {options.verdict}\n'
        f'saved_at: {saved_at}\n'
        f'{block_scalar("skill_request", options.skill_request)}'
        f'{block_scalar("verifier_prompt", options.verifier_prompt)}'
        '---\n'
        f'{body}',
        encoding='utf-8',
    )
    print(f'REPORT={report}')
    return 0


def main() -> int:
    """Dispatch the subcommand and report its result."""
    if sys.argv[1:2] in (['-h'], ['--help']):
        print(USAGE)
        return 0
    options = parse_arguments(sys.argv[1:])
    if options is None:
        print(USAGE, file=sys.stderr)
        return PREFLIGHT_ERROR
    try:
        root = Path(git('rev-parse', '--show-toplevel')).resolve()
        git('rev-parse', '--verify', '--quiet', 'HEAD')
        report = root / CACHE_DIRECTORY / f'{Path(options.target).name}.md'
        if options.command == 'lookup':
            return run_lookup(options, root, report)
        return run_save(options, root, report)
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES[HIT] = 'HIT'
    rc.RESULT_CODES[MISS] = 'MISS'
    rc.RESULT_CODES[DIRTY_WORKTREE] = 'DIRTY_WORKTREE'
    rc.RESULT_CODES[INPUTS_CHANGED] = 'INPUTS_CHANGED'
    rc.install()
    rc.run(main)
