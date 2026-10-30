#!/usr/bin/env python3

"""
Look up and save the one saved Verify report per plan, keyed by commit and catalog digest.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re
import subprocess
import sys
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import result_codes as rc  # noqa: E402  (path set above so the plugin's bin/ resolves)

USAGE = """\
Look up or save the one saved Verify report for a plan or for audit mode,
keyed by the commit Verify ran on and the digest of the active agentdev
catalog. Run from inside the repository being verified.

Usage:
  verify-cache.py lookup <plan-key|audit> [--fresh]
  verify-cache.py save <plan-key|audit> --commit <sha> --verdict <verdict> < report

Arguments:
  <plan-key|audit>  data/plans/<YYYYMMDD>-<slug>, its file path, or audit.

Options:
  --fresh           lookup only: report a miss even when a saved report matches.
  --commit <sha>    save only: the COMMIT the lookup's miss printed.
  --verdict <v>     save only: Ready to ship, Blocked, or Audit. A Needs
                    decision report is never saved.
  -h, --help        Show this help text.

Output (key=value lines):
  RESULT
  lookup HIT:   REPORT (the saved report's path), COMMIT, VERDICT
  lookup MISS:  COMMIT, CATALOG_DIGEST
  save:         REPORT

The saved report lives at .tmp/verify/<plan file name>.md, or
.tmp/verify/audit.md, under the repository root, and each save overwrites it.
A dirty worktree is any tracked change or any untracked file Git does not
ignore; the cache directory ignores itself.

Results (RESULT / exit code):
  SUCCESS            0  save: the report was saved; or help was printed
  HIT                3  lookup: the saved report matches HEAD and the catalog
  MISS               4  lookup: no saved report matches, or --fresh was given
  DIRTY_WORKTREE     5  The worktree has a tracked change or an unignored file
  HEAD_MOVED         6  save: HEAD is no longer the --commit the lookup printed
  PREFLIGHT_ERROR    2  Usage error, a disallowed verdict, not a git
                        repository, or a repository with no commit
  SCRIPT_FAILURE     1  Unhandled error
  SIGNAL_HUP       129  Interrupted by HUP
  SIGNAL_INT       130  Interrupted by INT
  SIGNAL_TERM      143  Interrupted by TERM\
"""

PREFLIGHT_ERROR = 2
HIT = 3
MISS = 4
DIRTY_WORKTREE = 5
HEAD_MOVED = 6

AUDIT = 'audit'
SAVED_VERDICTS = ('Ready to ship', 'Blocked', 'Audit')
PLUGIN_ROOT = Path(__file__).resolve().parents[3]
CACHE_DIRECTORY = Path('.tmp') / 'verify'
FRONTMATTER = re.compile(r'---\n(.*?)\n---\n', re.DOTALL)


class Options(NamedTuple):
    """The parsed command line."""

    command: str
    target: str
    fresh: bool
    commit: str
    verdict: str


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
    fresh, commit, verdict = False, '', ''
    while rest:
        flag = rest.pop(0)
        if command == 'lookup' and flag == '--fresh':
            fresh = True
        elif command == 'save' and flag in ('--commit', '--verdict') and rest:
            value = rest.pop(0)
            commit, verdict = (value, verdict) if flag == '--commit' else (commit, value)
        else:
            return None
    if command == 'save' and not (commit and verdict):
        return None
    return Options(command, canonical_target(target), fresh, commit, verdict)


def canonical_target(target: str) -> str:
    """Normalize a plan key or plan file path to data/plans/<name>; audit stays audit."""
    return AUDIT if target == AUDIT else f'data/plans/{Path(target).stem}'


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
    fields = (line.partition(': ') for line in match.group(1).splitlines())
    return {key: value for key, _, value in fields}


def run_lookup(options: Options, report: Path) -> int:
    """Report the saved report when it matches HEAD and the active catalog."""
    require_clean_worktree()
    commit = git('rev-parse', 'HEAD')
    digest = catalog_digest()
    saved = read_frontmatter(report)
    matches = (
        saved.get('plan') == options.target
        and saved.get('commit') == commit
        and saved.get('catalog_digest') == digest
    )
    if matches and not options.fresh:
        print(f'REPORT={report}')
        print(f'COMMIT={commit}')
        print(f'VERDICT={saved.get("verdict", "")}')
        return HIT
    print(f'COMMIT={commit}')
    print(f'CATALOG_DIGEST={digest}')
    return MISS


def run_save(options: Options, report: Path) -> int:
    """Overwrite the saved report with stdin, stamped with commit and digest."""
    if options.verdict not in SAVED_VERDICTS:
        print_error(f"Verdict '{options.verdict}' is not saved; use one of {SAVED_VERDICTS}.")
        return PREFLIGHT_ERROR
    require_clean_worktree()
    if git('rev-parse', 'HEAD') != options.commit:
        print_error(f'HEAD moved off {options.commit} since the lookup.')
        return HEAD_MOVED
    body = sys.stdin.read()
    report.parent.mkdir(parents=True, exist_ok=True)
    (report.parent / '.gitignore').write_text('*\n', encoding='utf-8')
    saved_at = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    report.write_text(
        '---\n'
        f'plan: {options.target}\n'
        f'commit: {options.commit}\n'
        f'catalog_digest: {catalog_digest()}\n'
        f'verdict: {options.verdict}\n'
        f'saved_at: {saved_at}\n'
        '---\n'
        f'{body}',
        encoding='utf-8',
    )
    print(f'REPORT={report}')
    return 0


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
        root = Path(git('rev-parse', '--show-toplevel'))
        git('rev-parse', '--verify', '--quiet', 'HEAD')
        report = root / CACHE_DIRECTORY / f'{Path(options.target).name}.md'
        if options.command == 'lookup':
            return run_lookup(options, report)
        return run_save(options, report)
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES[HIT] = 'HIT'
    rc.RESULT_CODES[MISS] = 'MISS'
    rc.RESULT_CODES[DIRTY_WORKTREE] = 'DIRTY_WORKTREE'
    rc.RESULT_CODES[HEAD_MOVED] = 'HEAD_MOVED'
    rc.install()
    rc.run(main)
