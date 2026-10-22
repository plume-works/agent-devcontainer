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
from typing import NamedTuple

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import result_codes as rc  # noqa: E402  (path set above so the plugin's bin/ resolves)

USAGE = """\
Classify every codebase-map doc (data/codebase/**/*.md) by whether the code it
describes changed after the source fingerprint it was read at.

Usage:
  stale-map-docs.py [--library <path>] [--explain]
  stale-map-docs.py [--library <path>] --replay [--since <YYYY-MM-DD>]

Options:
  --library <path>  IWE library directory, relative to the repository root.
                    Default: [workspace].path (config version 4) or
                    [library].path (earlier) from .iwe/config.toml, or "." when
                    the key is absent.
  --explain         After the verdicts, print one MASK line per applied digest
                    mask, naming the doc, the source file, the metadata file
                    that declared it, the pattern, and its reason.
  --replay          Prove the working-tree masks against history instead of
                    classifying: replay every first-parent change of the files
                    they reach, and say which non-fresh doc the masks explain.
  --since <date>    Also inspect masked-file commits on or after this date.
                    Verdict-required ancestry is always included.
  -h, --help        Show this help text.

Output:
  One line per map doc, then the counts, then RESULT:
    FRESH <key>                          the source digest is current
    STALE <key> source_digest <digest>   tracked source content changed
    GONE <key> <source>                  a source path no longer exists
    EXPIRED <key> <stale_after>          fresh, but stale_after has passed
    NO_DIGEST <key>                      frontmatter has no source_digest (treated as stale)
    BROKEN <key> <metadata-path>         a .agent.metadata.json could not be read
  With --explain, one line per applied mask:
    MASK <key> <source> <metadata-path> <pattern> <reason>
  Keys: MAP_DIR, DOC_COUNT, FRESH_COUNT, STALE_COUNT, GONE_COUNT, EXPIRED_COUNT,
        BROKEN_COUNT

Replay output, then the counts, then RESULT:
    ABSORBED <commit|WORKTREE> <path>  the masks hide every changed byte
    MOVED <commit|WORKTREE> <path>     the masked content still changed
    HIDDEN <metadata-path> <pattern> <value>   one distinct value a mask hid,
                                   as a JSON string
    RESTAMP <key> <digest>         only masked content moved; record <digest>
    REFRESH <key>                  the masks do not explain the change
    BROKEN <key> <metadata-path>   a .agent.metadata.json could not be read
  A non-fresh doc is RESTAMP when its recorded digest equals the digest under
  the metadata committed at HEAD, or when every first-parent commit after the
  commit that set its digest, and every uncommitted edit, is absorbed.
  Keys: MAP_DIR, DOC_COUNT, SINCE, ABSORBED_COUNT, MOVED_COUNT, RESTAMP_COUNT,
        REFRESH_COUNT, BROKEN_COUNT
  Replay ends SUCCESS when it ran to completion, whatever it found.

Content designated machine-managed by an `iwe-map.digest_ignore` rule in a
`.agent.metadata.json` is replaced with a fixed placeholder before the source
fingerprint is computed, so an automerged pin bump does not mark a doc stale. The
`.agent.metadata.json` files themselves are excluded from the fingerprint; a
rule enters a doc's digest only where it applies.

Results (RESULT / exit code):
  SUCCESS          0  Every map doc is fresh, or --replay ran to completion
  STALE_FOUND      3  At least one doc is STALE, GONE, NO_DIGEST, or EXPIRED
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


def blob_bytes(revision: str, path: str) -> bytes | None:
    """Return `path` as committed in `revision`, or None when that tree lacks it."""
    completed = subprocess.run(
        ['git', 'cat-file', 'blob', f'{revision}:{path}'], check=False, capture_output=True
    )
    return completed.stdout if completed.returncode == 0 else None


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


def verified_at(frontmatter: list[str]) -> str:
    """Return the `at` of a block or flow `verified` mapping, or '' when absent."""
    for index, line in enumerate(frontmatter):
        if not line.startswith('verified:'):
            continue
        value = line[len('verified:') :].strip()
        if value.startswith('{'):
            match = re.search(r'\bat:\s*([^,}]+)', value)
            return strip_quotes(match.group(1)) if match else ''
        for entry in frontmatter[index + 1 :]:
            if not entry.startswith((' ', '\t')):
                break
            match = re.match(r'^\s+at:\s*(.*)$', entry)
            if match:
                return strip_quotes(match.group(1))
        return ''
    return ''


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


def read_metadata(path: Path, text: str | bytes | None = None) -> list[tuple[str, list[Mask]]]:
    """Read one metadata file's digest_ignore rules, or raise BrokenMetadata."""
    declared_in = str(path)
    try:
        document = json.loads(path.read_text() if text is None else text)
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
    """
    Resolves the masks applying to a file, caching each directory's walk.

    Metadata is read from the working tree, or from the tree of `revision` when
    one is given; the files the masks apply to are always the caller's.
    """

    def __init__(self, revision: str | None = None) -> None:
        self._by_directory: dict[str, list[tuple[str, str, list[Mask]]]] = {}
        self._revision = revision

    def _declared(self, candidate: Path) -> list[tuple[str, list[Mask]]]:
        """Read `candidate`'s rules from this resolver's view, [] when it has none."""
        if self._revision is None:
            return read_metadata(candidate) if candidate.is_file() else []
        content = blob_bytes(self._revision, str(candidate))
        return [] if content is None else read_metadata(candidate, content)

    def _for_directory(self, directory: Path) -> list[tuple[str, str, list[Mask]]]:
        """Accumulate (declaring dir, glob, masks) from the root down to `directory`."""
        key = str(directory)
        if key in self._by_directory:
            return self._by_directory[key]

        parent = directory.parent
        inherited = [] if directory in (parent, Path('.')) else self._for_directory(parent)
        resolved = list(inherited)
        for glob, masks in self._declared(directory / METADATA_FILENAME):
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


def apply_masks(
    content: str,
    masks: list[Mask],
    hidden: dict[tuple[str, str], set[str]] | None = None,
) -> str:
    """Apply `masks` in resolution order, collecting each one's matches into `hidden`."""
    for mask in masks:
        if hidden is not None:
            values = hidden.setdefault((mask.declared_in, mask.pattern), set())
            values.update(match.group(0) for match in mask.expression.finditer(content))
        try:
            content = mask.expression.sub(mask.replace, content)
        except re.error as error:
            raise BrokenMetadata(mask.declared_in) from error
    return content


def universal_newlines(text: str) -> str:
    """Translate line endings as `Path.read_text` does, so blobs digest like the working tree."""
    return text.replace('\r\n', '\n').replace('\r', '\n')


def masked_hash(relative_path: str, masks: list[Mask]) -> str:
    """Hash `relative_path` with each mask applied in resolution order."""
    try:
        content = Path(relative_path).read_text()
    except (OSError, UnicodeError) as error:
        raise BrokenMetadata(masks[0].declared_in) from error
    return hashlib.sha256(apply_masks(content, masks).encode()).hexdigest()


def source_digest_for_paths(
    sources: list[str],
    resolver: MetadataResolver | None = None,
    applied: list[tuple[str, Mask]] | None = None,
    revision: str | None = None,
) -> str:
    """
    Fingerprint the tracked content under `sources`.

    An unmasked file contributes its `git hash-object` value, so a repository
    declaring no masks produces exactly the digests the unmasked script did.
    A masked file contributes the sha256 of its masked content instead, and the
    masks that applied are folded in by the caller.

    A `.agent.metadata.json` contributes nothing. It describes how this digest
    is computed rather than the code a map doc claims, and the rules that reach
    a doc already enter its digest through `fold_in_masks`.
    """
    if not sources:
        return f'sha256:{hashlib.sha256(b"").hexdigest()}'

    command = (
        ['git', 'ls-tree', '-rz', '--name-only', revision, '--', *sources]
        if revision is not None
        else ['git', 'ls-files', '-z', '--', *sources]
    )
    listed = subprocess.run(
        command,
        check=True,
        capture_output=True,
    ).stdout
    digest = hashlib.sha256()
    for raw_path in sorted({path for path in listed.split(b'\0') if path}):
        relative = os.fsdecode(raw_path)
        if Path(relative).name == METADATA_FILENAME:
            continue
        content = blob_bytes(revision, relative) if revision is not None else None
        if revision is None and not Path(relative).exists():
            digest.update(raw_path + b'\0' + b'MISSING' + b'\0')
            continue
        masks = resolver.masks_for(relative) if resolver is not None else []
        if masks:
            if revision is None:
                content_hash = masked_hash(relative, masks)
            else:
                try:
                    decoded = universal_newlines(content.decode()) if content is not None else ''
                except UnicodeError as error:
                    raise BrokenMetadata(masks[0].declared_in) from error
                content_hash = hashlib.sha256(apply_masks(decoded, masks).encode()).hexdigest()
            if applied is not None:
                applied.extend((relative, mask) for mask in masks)
        else:
            content_hash = (
                git('rev-parse', f'{revision}:{relative}')
                if revision is not None
                else git('hash-object', '--', relative)
            )
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
    """Read [workspace].path, or pre-v4 [library].path, from an IWE config; '' when absent."""
    in_library = False
    for line in config_file.read_text().splitlines():
        if line.startswith('['):
            in_library = line.strip() in ('[workspace]', '[library]')
            continue
        if in_library and line.split('=', 1)[0].strip() == 'path' and '=' in line:
            return line.split('=', 1)[1].strip().replace('"', '').replace("'", '')
    return ''


class Options(NamedTuple):
    """The parsed command line."""

    library: str
    explain: bool
    replay: bool
    since: str


def parse_arguments(argv: list[str]) -> Options | None:
    """Return the parsed options, or None to stop with usage."""
    library_override = ''
    explain = False
    replay = False
    since = ''
    index = 0
    while index < len(argv):
        argument = argv[index]
        if argument in ('-h', '--help'):
            print(USAGE)
            rc.quit_by_code(0)
        elif argument == '--explain':
            explain = True
            index += 1
        elif argument == '--replay':
            replay = True
            index += 1
        elif argument in ('--library', '--since'):
            if index + 1 >= len(argv):
                print_error(f'Missing value for {argument}.')
                return None
            if argument == '--library':
                library_override = argv[index + 1]
            else:
                since = argv[index + 1]
            index += 2
        else:
            print_error(f'Unknown argument: {argument}')
            print(USAGE, file=sys.stderr)
            return None
    if since and not replay:
        print_error('--since applies only to --replay.')
        return None
    if since and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', since):
        print_error(f'--since takes a YYYY-MM-DD date, not {since}.')
        return None
    if explain and replay:
        print_error('--explain and --replay cannot be combined.')
        return None
    return Options(library_override, explain, replay, since)


def classify(
    key: str,
    frontmatter: list[str],
    today: str,
    resolver: MetadataResolver,
    applied: list[tuple[str, Mask]],
) -> tuple[str, str]:
    """Return the verdict line and its counter name for one map doc."""
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

    if not recorded_digest:
        return f'NO_DIGEST {key}', 'stale'

    current_digest = fold_in_masks(source_digest_for_paths(sources, resolver, applied), applied)
    if current_digest != recorded_digest:
        return f'STALE {key} source_digest {current_digest}', 'stale'
    return expired_or_fresh()


EMPTY_TREE = '4b825dc642cb6eb9a060e54bf8d69288fbee4904'


def doc_key(path: str, library_path: str) -> str:
    """Return the IWE key of the map doc at `path`."""
    key = path[: -len('.md')]
    prefix = f'{library_path}/'
    return key[len(prefix) :] if key.startswith(prefix) else key


class Replayer:
    """Compares masked file contents across revisions, caching what it computed."""

    def __init__(self, resolver: MetadataResolver) -> None:
        self.resolver = resolver
        self.hidden: dict[tuple[str, str], set[str]] = {}
        self._parents: dict[str, str] = {}
        self._absorbed: dict[tuple[str, str | None, str], bool] = {}

    def parent(self, commit: str) -> str:
        """Return `commit`'s first parent, or the empty tree for a root commit."""
        if commit not in self._parents:
            completed = subprocess.run(
                ['git', 'rev-parse', '--verify', '--quiet', f'{commit}^1'],
                check=False,
                capture_output=True,
                text=True,
            )
            self._parents[commit] = (
                completed.stdout.strip() if completed.returncode == 0 else EMPTY_TREE
            )
        return self._parents[commit]

    def changes(
        self, since: str, paths: list[str], *, ancestry: bool = False
    ) -> list[tuple[str, list[str]]]:
        """Return first-parent commits after an ancestor or date, oldest first."""
        if not paths:
            return []
        arguments = ['log', '--first-parent', '--reverse', '--format=%H']
        if since:
            arguments.append(f'{since}..HEAD' if ancestry else f'--since={since}')
        commits = git(*arguments, '--', *paths).split()
        return [(commit, self.changed(self.parent(commit), commit, paths)) for commit in commits]

    @staticmethod
    def changed(before: str, after: str | None, paths: list[str]) -> list[str]:
        """Return the tracked files under `paths` that differ, the working tree when `after` is None."""
        revisions = [before] if after is None else [before, after]
        listed = subprocess.run(
            ['git', 'diff', '--name-only', '-z', '--no-renames', *revisions, '--', *paths],
            check=True,
            capture_output=True,
        ).stdout
        return [
            os.fsdecode(path)
            for path in listed.split(b'\0')
            if path and Path(os.fsdecode(path)).name != METADATA_FILENAME
        ]

    def masked(self, revision: str | None, path: str, collect: bool) -> str | None:
        """Return `path` at `revision` (working tree for None) with its masks applied."""
        if revision is None:
            raw = Path(path).read_bytes() if Path(path).is_file() else None
        else:
            raw = blob_bytes(revision, path)
        if raw is None:
            return None
        masks = self.resolver.masks_for(path)
        if not masks:
            return raw.decode(errors='surrogateescape')
        try:
            content = raw.decode()
        except UnicodeError as error:
            raise BrokenMetadata(masks[0].declared_in) from error
        return apply_masks(content, masks, self.hidden if collect else None)

    def absorbed(self, before: str, after: str | None, path: str, collect: bool = False) -> bool:
        """Say whether the masks hide every byte `path` changed between the revisions."""
        key = (before, after, path)
        if collect or key not in self._absorbed:
            old = self.masked(before, path, collect)
            new = self.masked(after, path, collect)
            self._absorbed[key] = old is not None and old == new
        return self._absorbed[key]

    def explains(self, sources: list[str], since: str, *, ancestry: bool = False) -> bool:
        """Say whether every change to `sources` since `since`, uncommitted included, is absorbed."""
        if not since:
            return False
        for commit, paths in self.changes(since, sources, ancestry=ancestry):
            parent = self.parent(commit)
            if not all(self.absorbed(parent, commit, path) for path in paths):
                return False
        return all(
            self.absorbed('HEAD', None, path) for path in self.changed('HEAD', None, sources)
        )


def digest_under(
    sources: list[str], resolver: MetadataResolver, revision: str | None = None
) -> str:
    """Return the digest `sources` would record under `resolver`'s metadata."""
    applied: list[tuple[str, Mask]] = []
    return fold_in_masks(
        source_digest_for_paths(sources, resolver, applied, revision=revision), applied
    )


def digest_commit(path: str, recorded: str) -> str:
    """Return the commit that began the current first-parent run of `recorded`."""
    boundary = ''
    for commit in git('log', '--first-parent', '--format=%H', '--', path).split():
        raw = blob_bytes(commit, path)
        if raw is None:
            break
        lines = raw.decode(errors='surrogateescape').splitlines()
        frontmatter = (
            lines[1 : lines[1:].index('---') + 1]
            if lines and lines[0] == '---' and '---' in lines[1:]
            else []
        )
        if scalar_field(frontmatter, 'source_digest') != recorded:
            break
        boundary = commit
    return boundary


def replay_verdict(
    key: str,
    path: str,
    frontmatter: list[str],
    replayer: Replayer,
    head_resolver: MetadataResolver,
) -> tuple[str, str] | None:
    """Return the RESTAMP or REFRESH line and its counter, or None for a fresh doc."""
    recorded = scalar_field(frontmatter, 'source_digest')
    sources = source_paths(frontmatter)
    replayer.resolver.verify(sources)
    head_resolver.verify(sources)
    if not recorded or not all(Path(source).exists() for source in sources):
        return f'REFRESH {key}', 'refresh'
    current = digest_under(sources, replayer.resolver)
    at_head = digest_under(sources, head_resolver)
    if current == recorded:
        return None
    boundary = digest_commit(path, recorded)
    start = boundary or verified_at(frontmatter)
    if boundary and digest_under(sources, MetadataResolver(boundary), boundary) != recorded:
        return f'REFRESH {key}', 'refresh'
    if at_head == recorded or replayer.explains(sources, start, ancestry=bool(boundary)):
        return f'RESTAMP {key} {current}', 'restamp'
    return f'REFRESH {key}', 'refresh'


def replay(doc_files: list[str], library_path: str, since: str) -> int:
    """Prove the working-tree masks against history and print the replay report."""
    docs = [(doc_key(path, library_path), frontmatter_of(Path(path))) for path in doc_files]
    if not since:
        stamps = [verified_at(frontmatter) for _, frontmatter in docs]
        since = min((stamp for stamp in stamps if stamp), default='')

    replayer = Replayer(MetadataResolver())
    head_resolver = MetadataResolver('HEAD')
    counts = {'absorbed': 0, 'moved': 0, 'restamp': 0, 'refresh': 0, 'broken': 0}
    verdicts: list[str] = []
    readable_sources: list[str] = []
    evidence_windows: list[tuple[str, bool, list[str]]] = []
    for (key, frontmatter), path in zip(docs, doc_files, strict=True):
        try:
            outcome = replay_verdict(key, path, frontmatter, replayer, head_resolver)
        except BrokenMetadata as broken:
            outcome = (f'BROKEN {key} {broken.path}', 'broken')
        else:
            sources = [source for source in source_paths(frontmatter) if Path(source).exists()]
            readable_sources.extend(sources)
            recorded = scalar_field(frontmatter, 'source_digest')
            boundary = digest_commit(path, recorded) if recorded else ''
            evidence_windows.append(
                (boundary or verified_at(frontmatter), bool(boundary), sources)
            )
        if outcome is not None:
            verdicts.append(outcome[0])
            counts[outcome[1]] += 1

    tracked_output = (
        subprocess.run(
            ['git', 'ls-files', '-z', '--', *readable_sources],
            check=True,
            capture_output=True,
        ).stdout
        if readable_sources
        else b''
    )
    tracked = [os.fsdecode(path) for path in tracked_output.split(b'\0') if path]
    masked_files = sorted(
        path
        for path in set(tracked)
        if Path(path).name != METADATA_FILENAME and replayer.resolver.masks_for(path)
    )
    evidence: set[tuple[str, str]] = set()
    source_keys = [(key, source_paths(frontmatter)) for key, frontmatter in docs]

    def keys_for(source_path: str) -> list[str]:
        """Return docs whose sources contain `source_path`."""
        return [
            key
            for key, sources in source_keys
            if any(
                source_path == source or source_path.startswith(f'{source}/') for source in sources
            )
        ]

    broken_keys = {line.split()[1] for line in verdicts if line.startswith('BROKEN ')}

    def record_broken(source_path: str, broken: BrokenMetadata) -> None:
        """Record evidence failures against every doc that owns the source path."""
        for key in keys_for(source_path):
            if key not in broken_keys:
                for line in list(verdicts):
                    if line.startswith((f'RESTAMP {key} ', f'REFRESH {key}')):
                        verdicts.remove(line)
                        counts['restamp' if line.startswith('RESTAMP ') else 'refresh'] -= 1
                verdicts.append(f'BROKEN {key} {broken.path}')
                counts['broken'] += 1
                broken_keys.add(key)

    windows = [*evidence_windows, (since, False, readable_sources)] if since else evidence_windows
    for start, ancestry, sources in windows:
        source_files = [
            path
            for path in masked_files
            if any(path == source or path.startswith(f'{source}/') for source in sources)
        ]
        for commit, paths in replayer.changes(start, source_files, ancestry=ancestry):
            evidence.update((commit, path) for path in paths)
    for commit, path in sorted(evidence):
        try:
            absorbed = replayer.absorbed(replayer.parent(commit), commit, path, collect=True)
        except BrokenMetadata as broken:
            record_broken(path, broken)
            continue
        print(f'{"ABSORBED" if absorbed else "MOVED"} {commit} {path}')
        counts['absorbed' if absorbed else 'moved'] += 1
    for path in replayer.changed('HEAD', None, masked_files):
        try:
            absorbed = replayer.absorbed('HEAD', None, path, collect=True)
        except BrokenMetadata as broken:
            record_broken(path, broken)
            continue
        print(f'{"ABSORBED" if absorbed else "MOVED"} WORKTREE {path}')
        counts['absorbed' if absorbed else 'moved'] += 1
    for path in masked_files:
        try:
            replayer.masked(None, path, collect=True)
        except BrokenMetadata as broken:
            record_broken(path, broken)
    for (declared_in, pattern), values in sorted(replayer.hidden.items()):
        for value in sorted(values):
            print(f'HIDDEN {declared_in} {pattern} {json.dumps(value)}')
    for line in verdicts:
        print(line)

    print(f'DOC_COUNT={len(doc_files)}')
    print(f'SINCE={since}')
    print(f'ABSORBED_COUNT={counts["absorbed"]}')
    print(f'MOVED_COUNT={counts["moved"]}')
    print(f'RESTAMP_COUNT={counts["restamp"]}')
    print(f'REFRESH_COUNT={counts["refresh"]}')
    print(f'BROKEN_COUNT={counts["broken"]}')
    return BROKEN_METADATA if counts['broken'] else 0


def main() -> int:
    """Scan the library's map docs and report each one's freshness."""
    options = parse_arguments(sys.argv[1:])
    if options is None:
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

    library_path = options.library or library_from_config(config_file) or '.'
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
    if options.replay:
        return replay(doc_files, library_path, options.since)

    today = dt.date.today().isoformat()
    counts = {'fresh': 0, 'stale': 0, 'gone': 0, 'expired': 0, 'broken': 0}
    resolver = MetadataResolver()
    explanations: list[str] = []

    for path in doc_files:
        key = doc_key(path, library_path)
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

    if options.explain:
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
