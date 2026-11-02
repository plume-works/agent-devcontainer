"""
Rejection checks for the OKF shapes of the reserved `data/index.md` and `data/log.md`.

Each test copies the graph into `/tmp`, breaks one reserved file, and asserts that
`iwe schema validate` refuses it and names the file.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA = REPO_ROOT / 'docs' / 'knowledge' / 'data'
IWE_CONFIG = REPO_ROOT / '.iwe'
TMP_ROOT = Path('/tmp/agentdev-tests')

pytestmark = pytest.mark.skipif(
    shutil.which('iwe') is None,
    reason='the iwe CLI is not installed',
)


def _validate(workspace: Path) -> subprocess.CompletedProcess[str]:
    """Run `iwe schema validate` at the workspace root."""
    return subprocess.run(
        ['iwe', 'schema', 'validate'],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )


def _undated_heading(content: str) -> str:
    """Rename the log's first date group to a heading that is not a date."""
    return content.replace('\n## 20', '\n## Recent changes\n\n## 20', 1)


def _extra_frontmatter(content: str) -> str:
    """Give the index a frontmatter key beyond `okf_version`."""
    return content.replace("okf_version: '0.2'\n", "okf_version: '0.2'\ntype: hub\n", 1)


@pytest.fixture(scope='module')
def workspace() -> Iterator[Path]:
    """Copy the configuration and graph into a workspace private to this run."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'reserved-file-shapes-{uuid4().hex}'
    try:
        (root / 'docs' / 'knowledge').mkdir(parents=True)
        shutil.copytree(IWE_CONFIG, root / '.iwe')
        shutil.copytree(DATA, root / 'docs' / 'knowledge' / 'data')
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_unmodified_graph_validates(workspace: Path) -> None:
    """The copied graph passes, so a failure below comes from the mutation."""
    result = _validate(workspace)
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    ('name', 'mutate'),
    [('log', _undated_heading), ('index', _extra_frontmatter)],
    ids=['log-undated-heading', 'index-extra-frontmatter'],
)
def test_broken_reserved_file_is_rejected(
    workspace: Path, name: str, mutate: Callable[[str], str]
) -> None:
    """A reserved file that leaves its OKF shape fails validation, named by key."""
    path = workspace / 'docs' / 'knowledge' / 'data' / f'{name}.md'
    original = path.read_text()
    broken = mutate(original)
    assert broken != original, 'the mutation changed nothing'
    try:
        path.write_text(broken)
        result = _validate(workspace)
    finally:
        path.write_text(original)
    assert result.returncode != 0
    assert f'data/{name}' in result.stdout
