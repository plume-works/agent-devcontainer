"""Tests for scripts/link-knowledge-support.py run in test repository trees that each test makes."""

from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/link-knowledge-support.py'
SCAFFOLD = Path('.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge')
KNOWLEDGE = Path('docs/knowledge')
SUPPORT = {
    'AGENTS.md': '# Agents\n',
    '.markdownlint.yml': 'default: false\n',
    'schema/adrs.md': '# ADRs\n',
}
OWNED = {
    'LICENSE.md': '# License\n',
    '.gitignore': 'iwe.log\n',
    'data/index.md': '# Index\n',
}


@pytest.fixture
def tree() -> Iterator[Path]:
    """Yield a repository root whose scaffold holds support files and owned files."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'link-knowledge-support-{uuid4().hex}'
    for relative, text in {**SUPPORT, **OWNED}.items():
        write(root / SCAFFOLD / relative, text)
    (root / KNOWLEDGE).mkdir(parents=True)
    yield root
    shutil.rmtree(root)


def write(path: Path, text: str) -> None:
    """Make the parent directories of path, then write text at path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def link(root: Path, relative: str, target: Path) -> Path:
    """Make docs/knowledge/<relative> a relative link to target, a path from the root."""
    path = root / KNOWLEDGE / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.symlink_to(os.path.relpath(root / target, path.parent))
    return path


def link_all(root: Path) -> None:
    """Link each support file to its scaffold copy."""
    for relative in SUPPORT:
        link(root, relative, SCAFFOLD / relative)


def run(root: Path) -> subprocess.CompletedProcess[str]:
    """Run the script from the repository root."""
    return subprocess.run(
        [sys.executable, str(SCRIPT)],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )


def resolves_to_scaffold(root: Path, relative: str) -> bool:
    """Return whether docs/knowledge/<relative> is a relative link to its scaffold copy."""
    path = root / KNOWLEDGE / relative
    return (
        path.is_symlink()
        and not os.path.isabs(os.readlink(path))
        and path.resolve() == (root / SCAFFOLD / relative).resolve()
    )


@pytest.mark.parametrize('relative', ['AGENTS.md', 'schema/adrs.md'])
def test_missing_link_is_made(tree: Path, relative: str) -> None:
    link_all(tree)
    (tree / KNOWLEDGE / relative).unlink()

    result = run(tree)

    assert result.returncode == 1
    assert str(KNOWLEDGE / relative) in result.stdout
    assert resolves_to_scaffold(tree, relative)
    schema = tree / KNOWLEDGE / 'schema'
    assert schema.is_dir() and not schema.is_symlink()


def test_missing_schema_directory_is_made_real(tree: Path) -> None:
    result = run(tree)

    assert result.returncode == 1
    assert all(resolves_to_scaffold(tree, relative) for relative in SUPPORT)
    schema = tree / KNOWLEDGE / 'schema'
    assert schema.is_dir() and not schema.is_symlink()


def test_same_copy_becomes_a_link(tree: Path) -> None:
    link_all(tree)
    copy = tree / KNOWLEDGE / 'schema/adrs.md'
    copy.unlink()
    write(copy, SUPPORT['schema/adrs.md'])

    result = run(tree)

    assert result.returncode == 1
    assert str(KNOWLEDGE / 'schema/adrs.md') in result.stdout
    assert resolves_to_scaffold(tree, 'schema/adrs.md')


def test_different_copy_is_reported(tree: Path) -> None:
    link_all(tree)
    copy = tree / KNOWLEDGE / 'AGENTS.md'
    copy.unlink()
    write(copy, '# Agents, edited here\n')

    result = run(tree)

    assert result.returncode == 1
    assert f'different: {KNOWLEDGE / "AGENTS.md"} vs {SCAFFOLD / "AGENTS.md"}' in result.stdout
    assert not copy.is_symlink()
    assert copy.read_text() == '# Agents, edited here\n'


def test_link_to_other_target_is_reported(tree: Path) -> None:
    link_all(tree)
    (tree / KNOWLEDGE / 'AGENTS.md').unlink()
    other = link(tree, 'AGENTS.md', SCAFFOLD / 'schema/adrs.md')

    result = run(tree)

    assert result.returncode == 1
    assert str(KNOWLEDGE / 'AGENTS.md') in result.stdout
    assert other.resolve() == (tree / SCAFFOLD / 'schema/adrs.md').resolve()


def test_dangling_link_is_reported(tree: Path) -> None:
    link_all(tree)
    dangling = link(tree, 'schema/bugs.md', SCAFFOLD / 'schema/bugs.md')

    result = run(tree)

    assert result.returncode == 1
    assert str(KNOWLEDGE / 'schema/bugs.md') in result.stdout
    assert dangling.is_symlink()


def test_repository_only_schema_file_is_reported(tree: Path) -> None:
    link_all(tree)
    extra = tree / KNOWLEDGE / 'schema/bugs.md'
    write(extra, '# Bugs\n')

    result = run(tree)

    assert result.returncode == 1
    assert f'{KNOWLEDGE / "schema/bugs.md"}: belongs in the scaffold' in result.stdout
    assert extra.read_text() == '# Bugs\n'


def test_owned_files_are_ignored(tree: Path) -> None:
    link_all(tree)
    owned = {**OWNED, 'data/index.md': '# Our index\n', 'tests/test_x.py': 'x = 1\n'}
    for relative, text in owned.items():
        write(tree / KNOWLEDGE / relative, text)

    result = run(tree)

    assert (result.returncode, result.stdout) == (0, '')
    for relative, text in owned.items():
        path = tree / KNOWLEDGE / relative
        assert not path.is_symlink() and path.read_text() == text


def test_linked_tree_passes(tree: Path) -> None:
    link_all(tree)

    result = run(tree)

    assert (result.returncode, result.stdout, result.stderr) == (0, '', '')


def test_copy_under_a_linked_directory_is_reported(tree: Path) -> None:
    link(tree, 'AGENTS.md', SCAFFOLD / 'AGENTS.md')
    link(tree, '.markdownlint.yml', SCAFFOLD / '.markdownlint.yml')
    link(tree, 'schema', SCAFFOLD / 'schema')

    result = run(tree)

    assert result.returncode == 1
    assert str(KNOWLEDGE / 'schema/adrs.md') in result.stdout
    scaffold_copy = tree / SCAFFOLD / 'schema/adrs.md'
    assert not scaffold_copy.is_symlink()
    assert scaffold_copy.read_text() == SUPPORT['schema/adrs.md']
