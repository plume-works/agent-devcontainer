"""
Checks for the `release` field the plan schema requires on active plans.

Each test copies the graph into `/tmp`, rewrites the release
declaration of one active plan, and runs `iwe schema validate` against it.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import re
import shutil
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA = REPO_ROOT / 'docs' / 'knowledge' / 'data'
IWE_CONFIG = REPO_ROOT / '.iwe'
TMP_ROOT = Path('/tmp/agentdev-tests')

FRONTMATTER = re.compile(r'\A---\n(.*?)\n---\n', re.S)
RELEASE = re.compile(r'^release:.*\n(?:- .*\n)*', re.M)

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


def _with_release(content: str, release: str | None) -> str:
    """Replace the frontmatter's `release` declaration; None removes it."""
    match = FRONTMATTER.match(content)
    assert match is not None, 'plan has no frontmatter'
    head = RELEASE.sub('', match.group(1) + '\n')
    if release is not None:
        head += release + '\n'
    return f'---\n{head.rstrip()}\n---\n' + content[match.end() :]


@pytest.fixture(scope='module')
def workspace() -> Path:
    """Copy the configuration and graph into an isolated workspace."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / 'plan-release-schema'
    if root.exists():
        shutil.rmtree(root)
    (root / 'docs' / 'knowledge').mkdir(parents=True)
    shutil.copytree(IWE_CONFIG, root / '.iwe')
    shutil.copytree(DATA, root / 'docs' / 'knowledge' / 'data')
    return root


def _plan(workspace: Path, done: bool) -> Iterator[Path]:
    """Yield the first active or done plan, restored after the test."""
    plans = sorted((workspace / 'docs' / 'knowledge' / 'data' / 'plans').glob('*.md'))
    path = next(p for p in plans if ('\nstage: done\n' in p.read_text()) == done)
    original = path.read_text()
    yield path
    path.write_text(original)


@pytest.fixture
def active_plan(workspace: Path) -> Iterator[Path]:
    """Yield an active plan, restored after the test."""
    yield from _plan(workspace, done=False)


@pytest.fixture
def done_plan(workspace: Path) -> Iterator[Path]:
    """Yield a done plan, restored after the test."""
    yield from _plan(workspace, done=True)


@pytest.mark.parametrize(
    'release',
    [
        None,
        'release: internal-ish',
        'release: []',
        'release:\n- plans/20260101-other',
        'release:\n- features/Upper-Case',
    ],
    ids=['missing', 'other-string', 'empty-list', 'plan-key', 'bad-slug'],
)
def test_active_plan_without_valid_release_is_rejected(
    workspace: Path, active_plan: Path, release: str | None
) -> None:
    """An active plan must declare `internal` or feature and bug keys."""
    active_plan.write_text(_with_release(active_plan.read_text(), release))
    result = _validate(workspace)
    assert result.returncode != 0
    assert active_plan.stem in result.stdout
    assert 'release' in result.stdout


@pytest.mark.parametrize(
    'release',
    [
        'release: internal',
        'release:\n- features/some-feature\n- bugs/some-bug',
        'release:\n- features/streak-widget.example',
    ],
    ids=['internal', 'feature-and-bug', 'example-key'],
)
def test_active_plan_with_valid_release_passes(
    workspace: Path, active_plan: Path, release: str
) -> None:
    """Both declaration forms validate."""
    active_plan.write_text(_with_release(active_plan.read_text(), release))
    result = _validate(workspace)
    assert result.returncode == 0, result.stdout + result.stderr


def test_done_plan_without_release_passes(workspace: Path, done_plan: Path) -> None:
    """A shipped plan predating the field stays valid."""
    done_plan.write_text(_with_release(done_plan.read_text(), None))
    result = _validate(workspace)
    assert result.returncode == 0, result.stdout + result.stderr
