#!/usr/bin/env python3
"""
Reject line-number references and unresolved anchors in the knowledge graph and catalog.

Lists every violation as ``path:line [rule] message`` and exits 1 when there is any.
The anchor syntax, both checks, and their scopes: see ADR-0083.
"""

from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
import json
from pathlib import Path
import re
import sys
import tomllib

import json5
import yaml

SCAN_GLOBS = (
    'docs/knowledge/data/**/*.md',
    '.agents/plugins/agentdev/skills/**/*.md',
    '.agents/plugins/agentdev/agents/**/*.md',
)
DATA = Path('docs/knowledge/data')
OPEN_STAGES = frozenset({'pending', 'planned'})

LINE_NUMBER_FORMS = (
    re.compile(r'(?<![\w./:-])(?!//)[\w./-]*\.[A-Za-z][\w-]*:\d+'),
    re.compile(r'[\w./-]*(?:Dockerfile|Makefile|Containerfile)[\w.-]*:\d+'),
    re.compile(r'#L\d+'),
    re.compile(r'\blines? \d+', re.IGNORECASE),
)

ANCHOR = re.compile(
    r'`(?P<path>[\w.][\w./-]*)(?:(?P<sep>::|#)(?P<fragment>[^`\s]+))?'
    r'(?:\s+›\s+"(?P<quote>[^"`]+)")?`'
)
FRONTMATTER = re.compile(r'\A---\n(.*?)\n---\n', re.S)
STAGE = re.compile(r'^stage:\s*(\S+)', re.M)
HEADING = re.compile(r'^(?P<hashes>#{1,6})\s+(?P<title>.*?)\s*#*\s*$')
FENCE = re.compile(r'^\s*(?:```|~~~)')
KEY_REFERENCES = re.compile(r'^## Key references\s*$(?P<body>.*?)(?=^## |\Z)', re.M | re.S)
DATA_FORMATS = frozenset({'.yml', '.yaml', '.json', '.toml'})
PARSE_ERRORS = (UnicodeDecodeError, ValueError, SyntaxError, yaml.YAMLError)
BUILD_FILES = ('Makefile', 'Dockerfile', 'Containerfile')


@dataclass(frozen=True)
class Violation:
    """One rule breach in one scanned document."""

    path: Path
    line: int
    rule: str
    message: str

    def __str__(self) -> str:
        """Render as ``path:line [rule] message``."""
        return f'{self.path}:{self.line} [{self.rule}] {self.message}'


def scanned_files(root: Path) -> list[Path]:
    """Return every Markdown file the line-number gate scans, sorted."""
    return sorted({path for pattern in SCAN_GLOBS for path in root.glob(pattern)})


def line_number_violations(root: Path, path: Path) -> list[Violation]:
    """Return one violation per line-number reference in ``path``."""
    found = []
    for number, text in enumerate(path.read_text().splitlines(), start=1):
        matches = {m.end(): m.group(0) for form in LINE_NUMBER_FORMS for m in form.finditer(text)}
        found.extend(
            Violation(
                path.relative_to(root),
                number,
                'line-number',
                f'`{reference}` records a line number; use an anchor',
            )
            for _, reference in sorted(matches.items())
        )
    return found


def collapse(text: str) -> str:
    """Collapse every whitespace run to one space."""
    return ' '.join(text.split())


def heading_slug(title: str) -> str:
    """Return GitHub's anchor slug for a Markdown heading title."""
    text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', title).replace('`', '').replace('*', '')
    return re.sub(r'[^\w\- ]', '', text.lower()).replace(' ', '-')


def markdown_sections(text: str) -> dict[str, str]:
    """Map each heading's slug to its section text, up to the next heading of its level or higher."""
    lines = text.splitlines()
    headings = []
    in_fence = False
    for index, line in enumerate(lines):
        if FENCE.match(line):
            in_fence = not in_fence
        elif not in_fence and (match := HEADING.match(line)):
            headings.append((index, len(match['hashes']), heading_slug(match['title'])))
    sections: dict[str, str] = {}
    seen: dict[str, int] = {}
    for position, (index, level, slug) in enumerate(headings):
        end = next((i for i, lvl, _ in headings[position + 1 :] if lvl <= level), len(lines))
        count = seen.get(slug, 0)
        seen[slug] = count + 1
        sections[f'{slug}-{count}' if count else slug] = '\n'.join(lines[index:end])
    return sections


def python_symbol_exists(source: str, names: list[str]) -> bool:
    """Return whether the dotted ``names`` chain is defined in the Python ``source``."""
    body = ast.parse(source).body
    for name in names:
        found = None
        for node in body:
            if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef):
                if node.name == name:
                    found = node
            elif isinstance(node, ast.Assign | ast.AnnAssign):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                if any(isinstance(t, ast.Name) and t.id == name for t in targets):
                    found = node
        if found is None:
            return False
        body = getattr(found, 'body', [])
    return True


def words_in_order(text: str, names: list[str]) -> bool:
    """Return whether each name occurs as a whole word in ``text``, in order."""
    position = 0
    for name in names:
        match = re.compile(rf'(?<![\w-]){re.escape(name)}(?![\w-])').search(text, position)
        if match is None:
            return False
        position = match.end()
    return True


def load_data(path: Path) -> object:
    """Parse a YAML, JSON (JSONC accepted), or TOML file."""
    if path.suffix == '.json':
        text = path.read_text()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            # The stdlib parser is far faster; json5 only for JSONC files it rejects.
            return json5.loads(text)
    if path.suffix == '.toml':
        return tomllib.loads(path.read_text())
    return yaml.safe_load(path.read_text())


def key_path_exists(data: object, names: list[str]) -> bool:
    """Return whether the key path exists; a list segment matches an element's id or name."""
    for name in names:
        if isinstance(data, dict):
            # YAML 1.1 loads a bare `on:` key, as in GitHub workflows, as True.
            matches = [
                v for k, v in data.items() if str(k) == name or (k is True and name == 'on')
            ]
        elif isinstance(data, list):
            matches = [
                item
                for item in data
                if isinstance(item, dict) and name in (str(item.get('id')), str(item.get('name')))
            ]
        else:
            return False
        if not matches:
            return False
        data = matches[0]
    return True


def build_target_exists(path: Path, name: str) -> bool:
    """Return whether a Makefile target or a Dockerfile stage carries ``name``."""
    text = path.read_text()
    if 'Makefile' in path.name:
        return re.search(rf'^{re.escape(name)}\s*:', text, re.M) is not None
    return re.search(rf'^FROM\s.+\sAS\s+{re.escape(name)}\s*$', text, re.M | re.I) is not None


def resolve(root: Path, match: re.Match[str]) -> str | None:
    """Return why the anchor does not resolve, or None when it does."""
    path = root / match['path']
    if not path.is_file():
        return 'file not found'
    try:
        return resolve_in(path, match)
    except PARSE_ERRORS as error:
        reason = str(error).splitlines()[0] if str(error) else ''
        return f'cannot parse file ({type(error).__name__}: {reason})'


def resolve_in(path: Path, match: re.Match[str]) -> str | None:
    """Return why the anchor does not resolve in the existing file ``path``."""
    text = path.read_text()
    region = text
    separator, fragment = match['sep'], match['fragment']
    if separator == '::':
        names = fragment.split('.')
        found = (
            python_symbol_exists(text, names)
            if path.suffix == '.py'
            else words_in_order(text, names)
        )
        if not found:
            return f'symbol `{fragment}` not found'
    elif separator == '#':
        if path.suffix == '.md':
            sections = markdown_sections(text)
            if fragment not in sections:
                return f'heading `#{fragment}` not found'
            region = sections[fragment]
        elif path.suffix in DATA_FORMATS:
            if not key_path_exists(load_data(path), fragment.split('.')):
                return f'key path `{fragment}` not found'
        elif any(name in path.name for name in BUILD_FILES):
            if not build_target_exists(path, fragment):
                return f'target or stage `{fragment}` not found'
        else:
            return f'`#` anchors are not defined for `{path.suffix or path.name}` files'
    if match['quote'] and collapse(match['quote']) not in collapse(region):
        return f'quote "{match["quote"]}" not found'
    return None


def anchors(text: str, start: int = 0, end: int | None = None) -> Iterator[re.Match[str]]:
    """Yield every anchor in ``text[start:end]``; all-digit fragments are issue references."""
    for match in ANCHOR.finditer(text, start, len(text) if end is None else end):
        if match['quote'] or (match['sep'] and not match['fragment'].isdigit()):
            yield match


def resolver_spans(path: Path, text: str) -> list[tuple[int, int]]:
    """Return the spans of ``text`` whose anchors must resolve; empty when none must."""
    relative = path.as_posix()
    frontmatter = FRONTMATTER.match(text)
    stage_match = STAGE.search(frontmatter.group(1)) if frontmatter else None
    stage = stage_match.group(1) if stage_match else None
    if f'/{DATA.as_posix()}/plans/' in relative:
        if stage is not None:
            return []
        return [(m.start('body'), m.end('body')) for m in KEY_REFERENCES.finditer(text)]
    if f'/{DATA.as_posix()}/bugs/' in relative or f'/{DATA.as_posix()}/backlog/' in relative:
        return [(0, len(text))] if stage in OPEN_STAGES else []
    if f'/{DATA.as_posix()}/guides/' in relative:
        return [(0, len(text))]
    return []


def anchor_violations(root: Path, path: Path) -> list[Violation]:
    """Return one violation per anchor in the resolver scope that does not resolve."""
    text = path.read_text()
    found = []
    for start, end in resolver_spans(path, text):
        for match in anchors(text, start, end):
            reason = resolve(root, match)
            if reason:
                found.append(
                    Violation(
                        path.relative_to(root),
                        text.count('\n', 0, match.start()) + 1,
                        'anchor',
                        f'{match.group(0)!s} does not resolve: {reason}',
                    )
                )
    return found


def main(argv: list[str]) -> int:
    """Check the tree rooted at ``argv[0]`` (default: the current directory)."""
    root = Path(argv[0] if argv else '.').resolve()
    violations = []
    for path in scanned_files(root):
        violations += line_number_violations(root, path)
        violations += anchor_violations(root, path)
    for violation in violations:
        print(violation)
    return 1 if violations else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
