"""
Checks for the IWE scaffold the iwe-bootstrap skill ships under `assets/`.

The scaffold is laid out as a repository root and no live graph reads it.
Install behaviour (a normalized, schema-valid graph that carries what
`iwe-setup` needs) is covered by `test_iwe_bootstrap.py`.
"""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import tomllib

import pytest

PLUGIN_ROOT = Path(__file__).resolve().parents[1]
SCAFFOLD = PLUGIN_ROOT / 'skills' / 'iwe-bootstrap' / 'assets'
SEED_DATA = SCAFFOLD / 'docs' / 'knowledge' / 'data'
PUBLISHER_ROOT = PLUGIN_ROOT.parents[2]

# Knowledge-base support files the scaffold shares byte for byte with the
# publisher's own workspace; see the skill's references/scaffold.md.
SHARED_KNOWLEDGE_FILES = (
    'AGENTS.md',
    'CLAUDE.md',
    'README.md',
    'SCHEMA.md',
    'STRUCTURE.md',
    'CHANGELOG.md',
    'LICENSE.md',
    '.gitignore',
    '.markdownlint.yml',
)

# A markdown link on its own line is an inclusion link; anywhere else it is a
# soft reference. Both must resolve, so the check does not distinguish them.
MARKDOWN_LINK = re.compile(r'(?<!\!)\[[^\]]*\]\(([^)\s]+)\)')

requires_iwe = pytest.mark.skipif(
    shutil.which('iwe') is None,
    reason='the iwe CLI is not installed',
)


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a command with `cwd` as the working directory, capturing its output."""
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, check=False)


@requires_iwe
def test_seed_is_not_a_member_of_the_publisher_graph() -> None:
    """`iwe` at the publisher root must not see any scaffold document."""
    result = _run('iwe', 'find', '-f', 'keys', cwd=PUBLISHER_ROOT)
    assert result.returncode == 0, result.stderr
    keys = result.stdout.split()
    assert keys, 'the publisher graph listed no documents'
    assert not [key for key in keys if 'assets/' in key or key.endswith('.example')]


def test_scaffold_is_complete() -> None:
    """The package carries every file a workspace needs, schemas included."""
    config = tomllib.loads((SCAFFOLD / '.iwe' / 'config.toml').read_text(encoding='utf-8'))
    assert config['workspace']['path'] == 'docs/knowledge'
    missing = [
        f'.iwe/schemas/{name}.yaml'
        for name in config['schemas']
        if not (SCAFFOLD / '.iwe' / 'schemas' / f'{name}.yaml').is_file()
    ]
    missing += [
        f'docs/knowledge/{name}'
        for name in SHARED_KNOWLEDGE_FILES
        if not (SCAFFOLD / 'docs' / 'knowledge' / name).is_file()
    ]
    assert not missing, 'the packaged scaffold is missing:\n' + '\n'.join(missing)
    assert sorted(path.name for path in SCAFFOLD.iterdir()) == ['.iwe', 'docs']


def test_scaffold_support_files_match_the_publisher_workspace() -> None:
    """Schemas, config, and instructions stay the bytes the publisher uses."""
    tracked = subprocess.run(
        ['git', 'ls-files', '.iwe'],
        cwd=PUBLISHER_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    packaged = sorted(
        path.relative_to(SCAFFOLD).as_posix()
        for path in (SCAFFOLD / '.iwe').rglob('*')
        if path.is_file()
    )
    assert packaged == sorted(tracked)
    drifted = [
        name
        for name in tracked
        if (PUBLISHER_ROOT / name).read_bytes() != (SCAFFOLD / name).read_bytes()
    ]
    drifted += [
        f'docs/knowledge/{name}'
        for name in SHARED_KNOWLEDGE_FILES
        if (PUBLISHER_ROOT / 'docs' / 'knowledge' / name).read_bytes()
        != (SCAFFOLD / 'docs' / 'knowledge' / name).read_bytes()
    ]
    assert not drifted, 'copy these into the scaffold or back:\n' + '\n'.join(drifted)


def test_every_link_resolves(plugin_tmp_path: Path) -> None:
    """No seed document links to a path the consumer will not have."""
    workspace = plugin_tmp_path / 'consumer'
    shutil.copytree(SCAFFOLD, workspace)
    data = workspace / 'docs' / 'knowledge' / 'data'
    broken: list[str] = []
    for doc in sorted(data.rglob('*.md')):
        for target in MARKDOWN_LINK.findall(doc.read_text(encoding='utf-8')):
            if target.startswith(('http://', 'https://', '#', 'mailto:')):
                continue
            path = target.split('#', 1)[0]
            if not path:
                continue
            # Links are extension-less by convention, and `.example` is part of
            # the key rather than a suffix — so append `.md`, never replace.
            resolved = (doc.parent / path).resolve()
            candidates = (resolved, resolved.with_name(resolved.name + '.md'))
            if not any(candidate.exists() for candidate in candidates):
                broken.append(f'{doc.relative_to(data)} -> {target}')
    assert not broken, 'unresolvable links in the seed:\n' + '\n'.join(broken)


def test_seed_holds_no_publisher_paths() -> None:
    """The seed points at skills a consumer has, not the import source's."""
    offenders: list[str] = []
    for doc in sorted(SEED_DATA.rglob('*.md')):
        text = doc.read_text(encoding='utf-8')
        for marker in ('.claude/skills/', 'agent-devcontainer'):
            if marker in text:
                offenders.append(f'{doc.relative_to(SEED_DATA)}: {marker}')
    assert not offenders, 'publisher-specific references in the seed:\n' + '\n'.join(offenders)


def test_every_scaffold_file_is_tracked() -> None:
    """Catalog installs copy tracked files only, so an ignored asset never ships."""
    tracked = set(
        subprocess.run(
            ['git', 'ls-files', '--', str(SCAFFOLD)],
            cwd=PUBLISHER_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
    )
    on_disk = {
        path.relative_to(PUBLISHER_ROOT).as_posix()
        for path in SCAFFOLD.rglob('*')
        if path.is_file()
    }
    assert on_disk - tracked == set(), 'untracked or ignored scaffold files'
