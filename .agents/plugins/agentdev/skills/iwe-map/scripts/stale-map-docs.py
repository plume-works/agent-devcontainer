#!/usr/bin/env python3

"""
Classify codebase-map docs by whether the code they describe changed.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
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
  stale-map-docs.py [--library <path>] [--explain]

Options:
  --library <path>  IWE library directory, relative to the repository root.
                    Default: [library].path from .iwe/config.toml, or "." when
                    the key is absent.
  --explain         After the verdicts, print one MASK line per applied digest
                    mask, naming the doc, the source file, the metadata file
                    that declared it, the pattern, and its reason.
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
    BROKEN <key> <metadata-path>         a .agent.metadata.json could not be read
  With --explain, one line per applied mask:
    MASK <key> <source> <metadata-path> <pattern> <reason>
  Keys: MAP_DIR, DOC_COUNT, FRESH_COUNT, STALE_COUNT, GONE_COUNT, EXPIRED_COUNT,
        BROKEN_COUNT

Content designated machine-managed by an `iwe-map.digest_ignore` rule in a
`.agent.metadata.json` is replaced with a fixed placeholder before the source
fingerprint is computed, so an automerged pin bump does not mark a doc stale.

Results (RESULT / exit code):
  SUCCESS          0  Every map doc is fresh
  STALE_FOUND      3  At least one doc is STALE, GONE, UNKNOWN_COMMIT, NO_COMMIT, or EXPIRED
  NO_MAP_DOCS      4  The library holds no data/codebase/ docs
  BROKEN_METADATA  5  A .agent.metadata.json could not be read or compiled
  PREFLIGHT_ERROR  2  Usage error, not a git repository, or no .iwe/config.toml
  SCRIPT_FAILURE   1  Unhandled error
  SIGNAL_HUP     129  Interrupted by HUP
  SIGNAL_INT     130  Interrupted by INT
  SIGNAL_TERM    143  Interrupted by TERM\
"""

STALE_FOUND = 3
NO_MAP_DOCS = 4
BROKEN_METADATA = 5
PREFLIGHT_ERROR = 2

METADATA_FILENAME = '.agent.metadata.json'


class BrokenMetadata(Exception):
    """A metadata file along a walk could not be read or compiled."""

    def __init__(self, path: str) -> None:
        super().__init__(path)
        self.path = path


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


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Compile a pathspec-style glob where `**` crosses separators and `*` does not."""
    parts: list[str] = []
    index = 0
    while index < len(pattern):
        char = pattern[index]
        if pattern.startswith('**/', index):
            parts.append('(?:.*/)?')
            index += 3
        elif pattern.startswith('**', index):
            parts.append('.*')
            index += 2
        elif char == '*':
            parts.append('[^/]*')
            index += 1
        elif char == '?':
            parts.append('[^/]')
            index += 1
        else:
            parts.append(re.escape(char))
            index += 1
    return re.compile(f'^{"".join(parts)}$')


class Mask:
    """One compiled digest_ignore rule, and where it was declared."""

    def __init__(self, pattern: str, replace: str, reason: str, declared_in: str) -> None:
        self.pattern = pattern
        self.replace = replace
        self.reason = reason
        self.declared_in = declared_in
        self.expression = re.compile(pattern)

    def identity(self) -> str:
        """Return the part of a mask a doc's digest folds in when it applies."""
        return f'{self.pattern}\0{self.replace}'


def read_metadata(path: Path) -> list[tuple[str, list[Mask]]]:
    """Read one metadata file's digest_ignore rules, or raise BrokenMetadata."""
    declared_in = str(path)
    try:
        document = json.loads(path.read_text())
    except (OSError, ValueError) as error:
        raise BrokenMetadata(declared_in) from error
    if not isinstance(document, dict):
        raise BrokenMetadata(declared_in)

    section = document.get('iwe-map')
    if section is None:
        return []
    if not isinstance(section, dict):
        raise BrokenMetadata(declared_in)
    ignore = section.get('digest_ignore')
    if ignore is None:
        return []
    if not isinstance(ignore, dict):
        raise BrokenMetadata(declared_in)

    entries: list[tuple[str, list[Mask]]] = []
    for glob, rules in ignore.items():
        if not isinstance(rules, list):
            raise BrokenMetadata(declared_in)
        masks: list[Mask] = []
        for rule in rules:
            if not isinstance(rule, dict) or 'pattern' not in rule or 'replace' not in rule:
                raise BrokenMetadata(declared_in)
            try:
                masks.append(
                    Mask(
                        str(rule['pattern']),
                        str(rule['replace']),
                        str(rule.get('reason', '')),
                        declared_in,
                    )
                )
            except re.error as error:
                raise BrokenMetadata(declared_in) from error
        entries.append((glob, masks))
    return entries


class MetadataResolver:
    """Resolves the masks applying to a file, caching each directory's walk."""

    def __init__(self) -> None:
        self._by_directory: dict[str, list[tuple[str, str, list[Mask]]]] = {}

    def _for_directory(self, directory: Path) -> list[tuple[str, str, list[Mask]]]:
        """Accumulate (declaring dir, glob, masks) from the root down to `directory`."""
        key = str(directory)
        if key in self._by_directory:
            return self._by_directory[key]

        parent = directory.parent
        inherited = [] if directory in (parent, Path('.')) else self._for_directory(parent)
        resolved = list(inherited)
        candidate = directory / METADATA_FILENAME
        if candidate.is_file():
            for glob, masks in read_metadata(candidate):
                resolved.append((str(directory), glob, masks))
        self._by_directory[key] = resolved
        return resolved

    def verify(self, sources: list[str]) -> None:
        """Read every metadata file the walks over `sources` reach, raising if broken."""
        for source in sources:
            base = Path(source)
            self._for_directory(base if base.is_dir() else base.parent)
            if base.is_dir():
                for child in base.rglob('*'):
                    if child.is_dir():
                        self._for_directory(child)

    def masks_for(self, relative_path: str) -> list[Mask]:
        """Return the masks applying to `relative_path`, shallowest declaration first."""
        path = Path(relative_path)
        applicable: list[Mask] = []
        for declaring_directory, glob, masks in self._for_directory(path.parent):
            base = Path(declaring_directory)
            try:
                scoped = path.relative_to(base) if str(base) != '.' else path
            except ValueError:
                continue
            if glob_to_regex(glob).match(str(scoped)):
                applicable.extend(masks)
        return applicable


def masked_hash(relative_path: str, masks: list[Mask]) -> str:
    """Hash `relative_path` with each mask applied in resolution order."""
    content = Path(relative_path).read_text()
    for mask in masks:
        content = mask.expression.sub(mask.replace, content)
    return hashlib.sha256(content.encode()).hexdigest()


def source_digest_for_paths(
    sources: list[str],
    resolver: MetadataResolver | None = None,
    applied: list[tuple[str, Mask]] | None = None,
) -> str:
    """
    Fingerprint the tracked content under `sources`.

    An unmasked file contributes its `git hash-object` value, so a repository
    declaring no masks produces exactly the digests the unmasked script did.
    A masked file contributes the sha256 of its masked content instead, and the
    masks that applied are folded in by the caller.
    """
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
        if not Path(relative).exists():
            digest.update(raw_path + b'\0' + b'MISSING' + b'\0')
            continue
        masks = resolver.masks_for(relative) if resolver is not None else []
        if masks:
            content_hash = masked_hash(relative, masks)
            if applied is not None:
                applied.extend((relative, mask) for mask in masks)
        else:
            content_hash = git('hash-object', '--', relative)
        digest.update(raw_path + b'\0' + content_hash.encode() + b'\0')
    return f'sha256:{digest.hexdigest()}'


def fold_in_masks(digest: str, applied: list[tuple[str, Mask]]) -> str:
    """
    Fold the masks that actually applied into a doc's digest.

    Only masks that matched one of this doc's own source files are folded in, so
    editing a mask invalidates the docs it reaches and leaves the rest alone.
    """
    if not applied:
        return digest
    combined = hashlib.sha256(digest.encode())
    for identity in sorted({mask.identity() for _, mask in applied}):
        combined.update(b'\0' + identity.encode())
    return f'sha256:{combined.hexdigest()}'


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


def parse_arguments(argv: list[str]) -> tuple[str, bool] | None:
    """Return the --library override and --explain flag, or None to stop with usage."""
    library_override = ''
    explain = False
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument in ('-h', '--help'):
            print(USAGE)
            rc.quit_by_code(0)
        elif argument == '--explain':
            explain = True
            index += 1
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
    return library_override, explain


def classify(
    key: str,
    frontmatter: list[str],
    today: str,
    resolver: MetadataResolver,
    applied: list[tuple[str, Mask]],
) -> tuple[str, str]:
    """Return the verdict line and its counter name for one map doc."""
    commit = scalar_field(frontmatter, 'commit')
    recorded_digest = scalar_field(frontmatter, 'source_digest')
    stale_after = scalar_field(frontmatter, 'stale_after')
    sources = source_paths(frontmatter)

    for source_path in sources:
        if not Path(source_path).exists():
            return f'GONE {key} {source_path}', 'gone'

    # Resolve the walk for every doc, not only the digest path: a doc whose
    # sources reach an unreadable metadata file has unknown freshness however
    # its verdict would otherwise be reached.
    resolver.verify(sources)

    def expired_or_fresh() -> tuple[str, str]:
        if stale_after and stale_after < today:
            return f'EXPIRED {key} {stale_after}', 'expired'
        return f'FRESH {key}', 'fresh'

    if recorded_digest:
        current_digest = fold_in_masks(
            source_digest_for_paths(sources, resolver, applied), applied
        )
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
    parsed = parse_arguments(sys.argv[1:])
    if parsed is None:
        return PREFLIGHT_ERROR
    library_override, explain = parsed

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
    counts = {'fresh': 0, 'stale': 0, 'gone': 0, 'expired': 0, 'broken': 0}
    resolver = MetadataResolver()
    explanations: list[str] = []

    for path in doc_files:
        key = path[: -len('.md')]
        prefix = f'{library_path}/'
        if key.startswith(prefix):
            key = key[len(prefix) :]
        applied: list[tuple[str, Mask]] = []
        try:
            line, counter = classify(key, frontmatter_of(Path(path)), today, resolver, applied)
        except BrokenMetadata as broken:
            line, counter = f'BROKEN {key} {broken.path}', 'broken'
        print(line)
        counts[counter] += 1
        for source_file, mask in applied:
            explanations.append(
                f'MASK {key} {source_file} {mask.declared_in} {mask.pattern} {mask.reason}'
            )

    if explain:
        for explanation in explanations:
            print(explanation)

    print(f'DOC_COUNT={len(doc_files)}')
    print(f'FRESH_COUNT={counts["fresh"]}')
    print(f'STALE_COUNT={counts["stale"]}')
    print(f'GONE_COUNT={counts["gone"]}')
    print(f'EXPIRED_COUNT={counts["expired"]}')
    print(f'BROKEN_COUNT={counts["broken"]}')

    # A broken subtree means some verdicts were not computed, so it outranks a
    # staleness the run may have only partly established.
    if counts['broken'] > 0:
        return BROKEN_METADATA
    if counts['stale'] + counts['gone'] + counts['expired'] > 0:
        return STALE_FOUND
    return 0


if __name__ == '__main__':
    rc.RESULT_CODES[STALE_FOUND] = 'STALE_FOUND'
    rc.RESULT_CODES[NO_MAP_DOCS] = 'NO_MAP_DOCS'
    rc.RESULT_CODES[BROKEN_METADATA] = 'BROKEN_METADATA'
    rc.install()
    rc.run(main)
