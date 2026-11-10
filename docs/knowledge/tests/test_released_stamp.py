"""
Checks for the `released` stamp a release cut sets on each plan it takes.

The cut selects done plans without `released`, so a stamp must name a real release
and no plan older than the latest release may lack one; see openspec/specs/iwe-workflow-skills.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import re
import shutil
import subprocess
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SCAFFOLD = REPO_ROOT / '.agents/plugins/agentdev/skills/iwe-bootstrap/assets'
IWE_CONFIG = REPO_ROOT / '.iwe'
TMP_ROOT = Path('/tmp/agentdev-tests')
GRAPHS = {
    'workspace': REPO_ROOT / 'docs' / 'knowledge' / 'data',
    'scaffold': SCAFFOLD / 'docs' / 'knowledge' / 'data',
}
FRONTMATTER = re.compile(r'\A---\n(.*?)\n---\n', re.S)


def _field(front: str, name: str) -> str | None:
    """Return a top-level scalar frontmatter value, unquoted, or None."""
    match = re.search(rf'^{name}:\s*(\S+)\s*$', front, re.M)
    return match.group(1).strip('\'"') if match else None


def _fronts(directory: Path) -> Iterator[tuple[Path, str]]:
    """Yield each document under the directory with its frontmatter text."""
    for path in sorted(directory.glob('*.md')):
        match = FRONTMATTER.match(path.read_text())
        if match:
            yield path, match.group(1)


@pytest.mark.parametrize('data', GRAPHS.values(), ids=GRAPHS.keys())
def test_stamps_name_a_release_and_cover_every_older_plan(data: Path) -> None:
    """Each `released` names a release page; no plan done by the latest cut lacks one."""
    releases = {
        _field(front, 'version'): _field(front, 'date') for _, front in _fronts(data / 'releases')
    }
    latest = max(releases.values())
    unknown, unstamped = [], []
    for path, front in _fronts(data / 'plans'):
        if _field(front, 'stage') != 'done':
            continue
        released = _field(front, 'released')
        if released is None and _field(front, 'completed') < latest:
            unstamped.append(path.name)
        if released is not None and released not in releases:
            unknown.append(path.name)
    assert unknown == []
    assert unstamped == []


@pytest.fixture
def workspace() -> Iterator[Path]:
    """Copy the configuration and graph into a workspace private to this test."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'released-stamp-{uuid4().hex}'
    try:
        (root / 'docs' / 'knowledge').mkdir(parents=True)
        shutil.copytree(IWE_CONFIG, root / '.iwe')
        shutil.copytree(GRAPHS['workspace'], root / 'docs' / 'knowledge' / 'data')
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.mark.skipif(shutil.which('iwe') is None, reason='the iwe CLI is not installed')
@pytest.mark.parametrize(('value', 'valid'), [('2.0.0', True), ('v2', False), ('2.0', False)])
def test_released_must_be_a_version(workspace: Path, value: str, valid: bool) -> None:
    """The plan schema accepts `released` only as an X.Y.Z version."""
    data = workspace / 'docs' / 'knowledge' / 'data'
    path = next(p for p, f in _fronts(data / 'plans') if _field(f, 'released'))
    content = path.read_text()
    path.write_text(re.sub(r'^released: .*$', f"released: '{value}'", content, 1, re.M))
    result = subprocess.run(
        ['iwe', 'schema', 'validate'], cwd=workspace, capture_output=True, text=True, check=False
    )
    assert (result.returncode == 0) is valid, result.stdout + result.stderr
