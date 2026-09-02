#!/usr/bin/env python3

"""File discovery and parsing helpers for validation."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import re
import subprocess
from typing import Dict, List, Set, Tuple

import yaml

logger = logging.getLogger(__name__)

DEFAULT_EXCLUDED_DIRS = {'test', 'tests', '.pytest_cache', '__pycache__', '.git', 'node_modules'}

GIT_DIR = '.git'


def _in_work_tree(root: str) -> bool:
    """Return whether ``root`` lies inside a git work tree, degrading to False on any error."""
    try:
        result = subprocess.run(
            ['git', '-C', str(root), 'rev-parse', '--is-inside-work-tree'],
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError) as exc:
        logger.debug('git rev-parse failed for %s: %s', root, exc)
        return False

    return result.returncode == 0 and result.stdout.strip() == 'true'


def _git_ignored(root: str, candidates: List[str]) -> Set[str]:
    """
    Return the subset of ``candidates`` git reports as ignored, as absolute paths.

    Feeds every candidate to one ``git check-ignore --stdin -z`` invocation. Any
    subprocess failure degrades to an empty set so discovery falls back rather
    than aborting.
    """
    if not candidates:
        return set()

    absolute = [os.path.abspath(candidate) for candidate in candidates]
    stdin_data = '\0'.join(absolute) + '\0'
    try:
        result = subprocess.run(
            ['git', '-C', str(root), 'check-ignore', '--stdin', '-z'],
            input=stdin_data,
            capture_output=True,
            text=True,
            check=False,
        )
    except (OSError, ValueError) as exc:
        logger.debug('git check-ignore failed for %s: %s', root, exc)
        return set()

    if result.returncode not in (0, 1):
        logger.debug('git check-ignore returned %s for %s', result.returncode, root)
        return set()

    ignored = {entry for entry in result.stdout.split('\0') if entry}
    return ignored


def _kept_subdirs(root: str, dirs: List[str], in_repo: bool, excluded_dirs: Set[str]) -> List[str]:
    """
    Return the subdirectories to keep walking, always pruning ``.git``.

    Inside a work tree, prune every directory ``git check-ignore`` flags;
    otherwise prune those whose basename is in ``excluded_dirs``.
    """
    named = [name for name in dirs if name != GIT_DIR]
    if not in_repo:
        return [name for name in named if name not in excluded_dirs]

    ignored = _git_ignored(root, [os.path.join(root, name) for name in named])
    return [name for name in named if os.path.abspath(os.path.join(root, name)) not in ignored]


@dataclass
class CustomFileContent:
    """Parsed contents for an agent or prompt markdown file."""

    frontmatter: dict
    body: str
    body_start_line: int
    has_frontmatter: bool


def find_skill_files(path: str, excluded_dirs: Set[str] = DEFAULT_EXCLUDED_DIRS) -> List[str]:
    """Find all SKILL.md files in a directory or return a single matching file."""
    path = str(path)

    if os.path.isfile(path):
        return [path] if path.endswith('SKILL.md') else []

    if not os.path.exists(path):
        return []

    in_repo = _in_work_tree(path)
    skill_files = []
    for root, dirs, files in os.walk(path):
        dirs[:] = _kept_subdirs(root, dirs, in_repo, excluded_dirs)
        matches = [os.path.join(root, 'SKILL.md')] if 'SKILL.md' in files else []
        if in_repo:
            ignored = _git_ignored(root, matches)
            matches = [match for match in matches if os.path.abspath(match) not in ignored]
        skill_files.extend(matches)

    return sorted(skill_files)


def safe_load_frontmatter(file_path: str) -> Tuple[Dict, str]:
    """Safely load YAML frontmatter and body from a file."""
    file_mode = os.stat(file_path).st_mode
    if file_mode & 0o444 == 0:
        raise PermissionError(f"Permission denied: '{file_path}'")

    with open(file_path, 'r', encoding='utf-8') as stream:
        content = stream.read()

    frontmatter, body, _ = _parse_frontmatter_content(content)
    return frontmatter, body


def safe_load_frontmatter_with_body_line(file_path: str) -> Tuple[Dict, str, int]:
    """Safely load YAML frontmatter, body, and the body start line from a file."""
    file_mode = os.stat(file_path).st_mode
    if file_mode & 0o444 == 0:
        raise PermissionError(f"Permission denied: '{file_path}'")

    with open(file_path, 'r', encoding='utf-8') as stream:
        content = stream.read()

    return _parse_frontmatter_content(content)


def _parse_frontmatter_content(content: str) -> Tuple[Dict, str, int]:
    """Parse frontmatter content and return the body start line."""
    if content.startswith('\ufeff'):
        content = content[1:]

    if not content.startswith('---'):
        return {}, content, 1

    parts = content.split('---', 2)
    if len(parts) < 3:
        raise yaml.YAMLError('Incomplete frontmatter delimiters in file')

    frontmatter_str = parts[1]
    body_with_leading_newlines = parts[2]
    body = body_with_leading_newlines.lstrip('\n')
    stripped_newlines = len(body_with_leading_newlines) - len(body)
    body_start_prefix = f'---{frontmatter_str}---{body_with_leading_newlines[:stripped_newlines]}'
    body_start_line = body_start_prefix.count('\n') + 1

    frontmatter_str = _normalize_frontmatter(frontmatter_str)

    try:
        frontmatter = yaml.safe_load(frontmatter_str) or {}
    except yaml.YAMLError as exc:
        raise yaml.YAMLError(f'Failed to parse frontmatter YAML: {exc}')

    return frontmatter, body, body_start_line


def _normalize_frontmatter(frontmatter_str: str) -> str:
    """Normalize common frontmatter formatting issues."""
    lines = frontmatter_str.splitlines()
    normalized_lines: List[str] = []

    for line in lines:
        match = re.match(r'^(name|description):\s*(.*)$', line)
        if not match:
            normalized_lines.append(line)
            continue

        key = match.group(1)
        value = match.group(2)

        if not value:
            normalized_lines.append(line)
            continue

        stripped = value.strip()
        if key == 'description' and stripped.count(':') > 1:
            normalized_lines.append(line)
            continue

        if stripped.startswith(('"', "'")):
            if stripped.startswith('"') and stripped.endswith('"'):
                inner = stripped[1:-1]
                escaped = inner.replace('"', '\\"')
                normalized_lines.append(f'{key}: "{escaped}"')
                continue

            normalized_lines.append(line)
            continue

        if ':' in value or '"' in value:
            escaped = value.replace('"', '\\"')
            normalized_lines.append(f'{key}: "{escaped}"')
            continue

        normalized_lines.append(line)

    return '\n'.join(normalized_lines)


def load_all_skills(skill_files: List[str]) -> Dict[str, Dict]:
    """Load multiple skill files for cross-validation."""
    skills = {}

    for file_path in skill_files:
        try:
            frontmatter, body = safe_load_frontmatter(file_path)
            skills[file_path] = {
                'frontmatter': frontmatter,
                'body': body,
            }
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            logger.warning(f'Failed to load skill {file_path}: {exc}')

    return skills


class SkillFileLoader:
    """Loads and parses skill files."""

    def find_skill_files(
        self, path: str, excluded_dirs: Set[str] = DEFAULT_EXCLUDED_DIRS
    ) -> List[str]:
        """Find all SKILL.md files under a path."""
        return find_skill_files(path, excluded_dirs=excluded_dirs)

    def load_skill(self, path: str) -> Tuple[Dict, str]:
        """Load a single skill file."""
        return safe_load_frontmatter(path)


def _find_matching_files(
    path: str, suffix: str, excluded_dirs: Set[str] = DEFAULT_EXCLUDED_DIRS
) -> List[str]:
    candidate = Path(path)
    if candidate.is_file():
        return [str(candidate)] if candidate.name.endswith(suffix) else []
    if not candidate.exists():
        return []

    in_repo = _in_work_tree(str(candidate))
    matches: List[str] = []
    for root, dirs, files in os.walk(candidate):
        dirs[:] = _kept_subdirs(root, dirs, in_repo, excluded_dirs)
        found = [str(Path(root) / name) for name in files if name.endswith(suffix)]
        if in_repo:
            ignored = _git_ignored(root, found)
            found = [match for match in found if os.path.abspath(match) not in ignored]
        matches.extend(found)

    return sorted(matches)


def find_agent_files(path: str, excluded_dirs: Set[str] = DEFAULT_EXCLUDED_DIRS) -> List[str]:
    """Find all .agent.md files under a path."""
    return _find_matching_files(path, '.agent.md', excluded_dirs=excluded_dirs)


def find_prompt_files(path: str, excluded_dirs: Set[str] = DEFAULT_EXCLUDED_DIRS) -> List[str]:
    """Find all .prompt.md files under a path."""
    return _find_matching_files(path, '.prompt.md', excluded_dirs=excluded_dirs)


def load_custom_file(file_path: str) -> CustomFileContent:
    """Load frontmatter and body for an agent or prompt markdown file."""
    raw_content = Path(file_path).read_text(encoding='utf-8')
    normalized = raw_content[1:] if raw_content.startswith('\ufeff') else raw_content
    has_frontmatter = normalized.startswith('---')

    frontmatter, body, body_start_line = safe_load_frontmatter_with_body_line(file_path)
    return CustomFileContent(
        frontmatter=frontmatter,
        body=body,
        body_start_line=body_start_line,
        has_frontmatter=has_frontmatter,
    )


def agent_identifier(file_path: str) -> str:
    """Return the identifier implied by an agent file name."""
    path = Path(file_path)
    return path.name.removesuffix('.agent.md')
