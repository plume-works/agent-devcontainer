#!/usr/bin/env python3

"""
Classify codebase-map docs by whether the code they describe changed.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import result_codes as rc  # noqa: E402  (path set above so the plugin's bin/ resolves)

USAGE = """\
Classify every codebase-map doc (data/codebase/**/*.md) by whether the code it
describes changed after the source fingerprint or commit it was read at.

Usage:
  stale-map-docs.py [--library <path>]

Options:
  --library <path>  IWE library directory, relative to the repository root.
                    Default: [library].path from .iwe/config.toml, or "." when
                    the key is absent.
  -h, --help        Show this help text.

Output:
  One line per map doc, then the counts, then RESULT:
    FRESH <key>                          source digest or commit check is current
    STALE <key> source_digest <digest>   tracked source content changed
    STALE <key> <commit> <n>             n commits touched a source path
    GONE <key> <source>                  a source path no longer exists
    UNKNOWN_COMMIT <key> <commit>        the pinned commit is not in this clone
    EXPIRED <key> <stale_after>          fresh, but stale_after has passed
    NO_COMMIT <key>                      frontmatter has no commit (treated as stale)
  Keys: MAP_DIR, DOC_COUNT, FRESH_COUNT, STALE_COUNT, GONE_COUNT, EXPIRED_COUNT

Results (RESULT / exit code):
  SUCCESS          0  Every map doc is fresh
  STALE_FOUND      3  At least one doc is STALE, GONE, UNKNOWN_COMMIT, NO_COMMIT, or EXPIRED
  NO_MAP_DOCS      4  The library holds no data/codebase/ docs
  PREFLIGHT_ERROR  2  Usage error, not a git repository, or no .iwe/config.toml
  SCRIPT_FAILURE   1  Unhandled error
  SIGNAL_HUP     129  Interrupted by HUP
  SIGNAL_INT     130  Interrupted by INT
  SIGNAL_TERM    143  Interrupted by TERM\
"""

STALE_FOUND = 3
NO_MAP_DOCS = 4
PREFLIGHT_ERROR = 2


def print_error(message: str) -> None:
    """Report a failure on stderr in the shared ERROR: form."""
    print(f'ERROR: {message}', file=sys.stderr)


def git(*arguments: str) -> str:
    """Run git and return its stdout, stripped of the trailing newline."""
    completed = subprocess.run(['git', *arguments], check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def strip_quotes(value: str) -> str:
    """Drop one layer of matching or stray surrounding quotes, as the awk did."""
    return value.strip().strip('\'"')


def frontmatter_of(path: Path) -> list[str]:
    """Return the lines between the opening and closing `---` of a doc."""
    lines = path.read_text().splitlines()
    if not lines or lines[0] != '---':
        return []
    body: list[str] = []
    for line in lines[1:]:
        if line == '---':
            break
        body.append(line)
    return body


def scalar_field(frontmatter: list[str], key: str) -> str:
    """Return a top-level scalar value with quotes stripped, or '' when absent."""
    prefix = f'{key}:'
    for line in frontmatter:
        if line.startswith(prefix):
            return strip_quotes(line[len(prefix) :])
    return ''


def source_paths(frontmatter: list[str]) -> list[str]:
    """Read `source` in any of its three shapes: scalar, flow list, or block list."""
    for index, line in enumerate(frontmatter):
        if not line.startswith('source:'):
            continue
        value = line[len('source:') :].strip()
        if value.startswith('['):
            inner = value.strip('[]')
            return [item for item in (strip_quotes(p) for p in inner.split(',')) if item]
        if value:
            return [strip_quotes(value)]
        paths: list[str] = []
        for entry in frontmatter[index + 1 :]:
            match = re.match(r'^\s*-\s*(.*)$', entry)
            if not match:
                break
            paths.append(strip_quotes(match.group(1)))
        return [path for path in paths if path]
    return []


def source_digest_for_paths(sources: list[str]) -> str:
    """Fingerprint the tracked content under `sources`, as the shell original did."""
    if not sources:
        return f'sha256:{hashlib.sha256(b"").hexdigest()}'

    listed = subprocess.run(
        ['git', 'ls-files', '-z', '--', *sources],
        check=True,
        capture_output=True,
    ).stdout
    digest = hashlib.sha256()
    for raw_path in sorted({path for path in listed.split(b'\0') if path}):
        relative = raw_path.decode()
        content_hash = git('hash-object', '--', relative) if Path(relative).exists() else 'MISSING'
        digest.update(raw_path + b'\0' + content_hash.encode() + b'\0')
    return f'sha256:{digest.hexdigest()}'


def library_from_config(config_file: Path) -> str:
    """Read [library].path from an IWE config; '' when the key is absent."""
    in_library = False
    for line in config_file.read_text().splitlines():
        if line.startswith('['):
            in_library = line.strip() == '[library]'
            continue
        if in_library and line.split('=', 1)[0].strip() == 'path' and '=' in line:
            return line.split('=', 1)[1].strip().replace('"', '').replace("'", '')
    return ''


def parse_arguments(argv: list[str]) -> str | None:
    """Return the --library override ('' when unset), or None to stop with usage."""
    library_override = ''
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument in ('-h', '--help'):
            print(USAGE)
            rc.quit_by_code(0)
        elif argument == '--library':
            if index + 1 >= len(argv):
                print_error('Missing value for --library.')
                return None
            library_override = argv[index + 1]
            index += 2
        else:
            print_error(f'Unknown argument: {argument}')
            print(USAGE, file=sys.stderr)
            return None
    return library_override


def classify(key: str, frontmatter: list[str], today: str) -> tuple[str, str]:
    """Return the verdict line and its counter name for one map doc."""
    commit = scalar_field(frontmatter, 'commit')
    recorded_digest = scalar_field(frontmatter, 'source_digest')
    stale_after = scalar_field(frontmatter, 'stale_after')
    sources = source_paths(frontmatter)

    for source_path in sources:
        if not Path(source_path).exists():
            return f'GONE {key} {source_path}', 'gone'

    def expired_or_fresh() -> tuple[str, str]:
        if stale_after and stale_after < today:
            return f'EXPIRED {key} {stale_after}', 'expired'
        return f'FRESH {key}', 'fresh'

    if recorded_digest:
        current_digest = source_digest_for_paths(sources)
        if current_digest != recorded_digest:
            return f'STALE {key} source_digest {current_digest}', 'stale'
        return expired_or_fresh()

    if not commit:
        return f'NO_COMMIT {key}', 'stale'

    resolved = subprocess.run(
        ['git', 'cat-file', '-e', f'{commit}^{{commit}}'],
        check=False,
        capture_output=True,
    )
    if resolved.returncode != 0:
        return f'UNKNOWN_COMMIT {key} {commit}', 'stale'

    touching = 0
    if sources:
        log = git('log', '--oneline', f'{commit}..HEAD', '--', *sources)
        touching = len(log.splitlines()) if log else 0
    if touching > 0:
        return f'STALE {key} {commit} {touching}', 'stale'

    return expired_or_fresh()


def main() -> int:
    """Scan the library's map docs and report each one's freshness."""
    library_override = parse_arguments(sys.argv[1:])
    if library_override is None:
        return PREFLIGHT_ERROR

    try:
        repo_root = git('rev-parse', '--show-toplevel')
    except subprocess.CalledProcessError:
        print_error('This script must be run inside a Git repository.')
        return PREFLIGHT_ERROR
    os.chdir(repo_root)

    config_file = Path(repo_root) / '.iwe' / 'config.toml'
    if not config_file.is_file():
        print_error(f'No .iwe/config.toml at {repo_root}; run from an IWE workspace root.')
        return PREFLIGHT_ERROR

    library_path = library_override or library_from_config(config_file) or '.'
    library_path = library_path.rstrip('/')
    map_dir = f'{library_path}/data/codebase'
    print(f'MAP_DIR={map_dir}')

    # Sort the path strings bytewise, as `find | LC_ALL=C sort` does: sorting
    # Path objects compares them component-wise and orders subdirectories
    # differently.
    doc_files = (
        sorted(str(path) for path in Path(map_dir).rglob('*.md') if path.is_file())
        if Path(map_dir).is_dir()
        else []
    )
    if not doc_files:
        print('DOC_COUNT=0')
        return NO_MAP_DOCS

    today = dt.date.today().isoformat()
    counts = {'fresh': 0, 'stale': 0, 'gone': 0, 'expired': 0}

    for path in doc_files:
        key = path[: -len('.md')]
        prefix = f'{library_path}/'
        if key.startswith(prefix):
            key = key[len(prefix) :]
        line, counter = classify(key, frontmatter_of(Path(path)), today)
        print(line)
        counts[counter] += 1

    print(f'DOC_COUNT={len(doc_files)}')
    print(f'FRESH_COUNT={counts["fresh"]}')
    print(f'STALE_COUNT={counts["stale"]}')
    print(f'GONE_COUNT={counts["gone"]}')
    print(f'EXPIRED_COUNT={counts["expired"]}')

    if counts['stale'] + counts['gone'] + counts['expired'] > 0:
        return STALE_FOUND
    return 0


if __name__ == '__main__':
    rc.RESULT_CODES[STALE_FOUND] = 'STALE_FOUND'
    rc.RESULT_CODES[NO_MAP_DOCS] = 'NO_MAP_DOCS'
    rc.install()
    rc.run(main)
