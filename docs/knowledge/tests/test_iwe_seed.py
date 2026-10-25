"""
Consumer-workspace checks for the IWE scaffold the iwe-bootstrap skill ships.

The scaffold under the skill's `assets/` is laid out as a repository root, and
no live graph reads it: `.iwe/config.toml` here points the library at
`docs/knowledge`. These tests copy that tree alone into a throwaway workspace
under the repo-root `.tmp/` and run the same gates a consumer's first session
runs, so a file missing from the package fails here rather than being borrowed
from this repository.

Requiring the packaged scaffold to equal `iwe normalize`'s output is what keeps
a consumer's first `git status` clean.
"""

from __future__ import annotations

import filecmp
from pathlib import Path
import re
import shutil
import subprocess
import tomllib

import frontmatter
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCAFFOLD = REPO_ROOT / '.agents' / 'plugins' / 'agentdev' / 'skills' / 'iwe-bootstrap' / 'assets'
SEED_DATA = SCAFFOLD / 'docs' / 'knowledge' / 'data'
SEED_LICENSE = SCAFFOLD / 'docs' / 'knowledge' / 'LICENSE.md'
TMP_ROOT = REPO_ROOT / '.tmp'

# Knowledge-base support files the scaffold shares byte for byte with this
# repository's own workspace; see the skill's references/scaffold.md.
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

# The keys `/agentdev:iwe-setup` closes in its "Close the loop" step. Renaming
# either one silently breaks that step, which no schema can catch.
ONBOARDING_KEYS = ('fill-product-doc', 'capture-current-architecture')

# A markdown link on its own line is an inclusion link; anywhere else it is a
# soft reference. Both must resolve, so the check does not distinguish them.
MARKDOWN_LINK = re.compile(r'(?<!\!)\[[^\]]*\]\(([^)\s]+)\)')

pytestmark = pytest.mark.skipif(
    shutil.which('iwe') is None,
    reason='the iwe CLI is not installed',
)


def _run_iwe(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run `iwe` with `cwd` as the working directory, capturing its output."""
    return subprocess.run(
        ['iwe', *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.fixture(scope='module')
def consumer_workspace() -> Path:
    """Copy the packaged scaffold, and nothing else, into an isolated directory."""
    TMP_ROOT.mkdir(exist_ok=True)
    workspace = TMP_ROOT / 'iwe-seed-consumer'
    if workspace.exists():
        shutil.rmtree(workspace)
    shutil.copytree(SCAFFOLD, workspace)
    return workspace


def test_seed_is_not_a_member_of_the_publisher_graph() -> None:
    """`iwe` at the repository root must not see any scaffold document."""
    result = _run_iwe('find', '-f', 'keys', cwd=REPO_ROOT)
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
    """Schemas, config, and instructions stay the bytes this repository uses."""
    tracked = subprocess.run(
        ['git', 'ls-files', '.iwe'],
        cwd=REPO_ROOT,
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
        if (REPO_ROOT / name).read_bytes() != (SCAFFOLD / name).read_bytes()
    ]
    drifted += [
        f'docs/knowledge/{name}'
        for name in SHARED_KNOWLEDGE_FILES
        if (REPO_ROOT / 'docs' / 'knowledge' / name).read_bytes()
        != (SCAFFOLD / 'docs' / 'knowledge' / name).read_bytes()
    ]
    assert not drifted, 'copy these into the scaffold or back:\n' + '\n'.join(drifted)


def test_seed_carries_its_license() -> None:
    """The seed keeps the MIT notice it was imported under."""
    text = SEED_LICENSE.read_text(encoding='utf-8')
    assert 'MIT License' in text
    assert 'WITHOUT WARRANTY OF ANY KIND' in text


def test_schema_validation_passes(consumer_workspace: Path) -> None:
    """Every seed document validates against the shipped schemas."""
    result = _run_iwe('schema', 'validate', cwd=consumer_workspace)
    assert result.returncode == 0, f'{result.stdout}\n{result.stderr}'
    assert 'required property' not in result.stdout


def test_checked_in_seed_matches_normalized_output(consumer_workspace: Path) -> None:
    """`iwe normalize` is a no-op, so a consumer's first commit is clean."""
    result = _run_iwe('normalize', cwd=consumer_workspace)
    assert result.returncode == 0, f'{result.stdout}\n{result.stderr}'

    comparison = filecmp.dircmp(str(SCAFFOLD), str(consumer_workspace))
    differences: list[str] = []

    def collect(node: filecmp.dircmp, prefix: str = '') -> None:
        """Accumulate every differing, added, or removed path under `node`."""
        for name in node.diff_files:
            differences.append(f'{prefix}{name}: normalize rewrote it')
        for name in node.left_only:
            differences.append(f'{prefix}{name}: removed by normalize')
        for name in node.right_only:
            differences.append(f'{prefix}{name}: added by normalize')
        for name, sub in node.subdirs.items():
            collect(sub, f'{prefix}{name}/')

    collect(comparison)
    assert not differences, 'run `iwe normalize` on the packaged scaffold:\n' + '\n'.join(
        differences
    )


def test_onboarding_tasks_are_present_and_open(consumer_workspace: Path) -> None:
    """The tasks iwe-setup closes exist and start unfinished."""
    backlog = consumer_workspace / 'docs' / 'knowledge' / 'data' / 'backlog'
    for key in ONBOARDING_KEYS:
        doc = backlog / f'{key}.md'
        assert doc.exists(), f'{key} is missing; iwe-setup closes it by key'
        post = frontmatter.load(doc)
        assert post['type'] == 'task'
        assert post['stage'] == 'planned', f'{key} must start open'


def test_product_doc_still_has_placeholders(consumer_workspace: Path) -> None:
    """The seed hands the consumer a blank product doc for setup to fill."""
    product = consumer_workspace / 'docs' / 'knowledge' / 'data' / 'product.md'
    assert '✏️' in product.read_text(encoding='utf-8')


def test_every_link_resolves(consumer_workspace: Path) -> None:
    """No seed document links to a path the consumer will not have."""
    data = consumer_workspace / 'docs' / 'knowledge' / 'data'
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
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.split()
    )
    on_disk = {
        path.relative_to(REPO_ROOT).as_posix() for path in SCAFFOLD.rglob('*') if path.is_file()
    }
    assert on_disk - tracked == set(), 'untracked or ignored scaffold files'
