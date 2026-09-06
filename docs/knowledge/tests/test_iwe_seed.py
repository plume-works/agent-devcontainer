"""
Consumer-workspace checks for the IWE seed in `templates/iwe/`.

The seed is not a member of this repository's graph — `.iwe/config.toml` points
the library at `docs/knowledge`, so `iwe` at the repository root never reads it.
These tests give it the only validation it can get: assemble a throwaway
consumer workspace under the repo-root `.tmp/` from the repository's own `.iwe/`
plus the seed at the consumer's `docs/knowledge/data/` layout, and run the same
gates a consumer's first session runs.

Requiring the checked-in seed to equal `iwe normalize`'s output is what keeps a
consumer's first `git status` clean.
"""

from __future__ import annotations

import filecmp
from pathlib import Path
import re
import shutil
import subprocess

import frontmatter
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_DATA = REPO_ROOT / 'templates' / 'iwe' / 'data'
SEED_LICENSE = REPO_ROOT / 'templates' / 'iwe' / 'LICENSE.md'
IWE_CONFIG = REPO_ROOT / '.iwe'
TMP_ROOT = REPO_ROOT / '.tmp'

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
    """Assemble the seed at a consumer's layout in an isolated directory."""
    TMP_ROOT.mkdir(exist_ok=True)
    workspace = TMP_ROOT / 'iwe-seed-consumer'
    if workspace.exists():
        shutil.rmtree(workspace)
    (workspace / 'docs' / 'knowledge').mkdir(parents=True)
    shutil.copytree(IWE_CONFIG, workspace / '.iwe')
    shutil.copytree(SEED_DATA, workspace / 'docs' / 'knowledge' / 'data')
    return workspace


def test_seed_is_not_a_member_of_the_publisher_graph() -> None:
    """`iwe` at the repository root must not see any seed document."""
    result = _run_iwe('find', '--roots', '-f', 'keys', cwd=REPO_ROOT)
    assert result.returncode == 0, result.stderr
    keys = _run_iwe('stats', cwd=REPO_ROOT)
    assert 'templates/' not in result.stdout
    assert 'templates/' not in keys.stdout


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

    normalized = consumer_workspace / 'docs' / 'knowledge' / 'data'
    comparison = filecmp.dircmp(str(SEED_DATA), str(normalized))
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
    assert not differences, 'run `iwe normalize` on the seed fixture:\n' + '\n'.join(differences)


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
