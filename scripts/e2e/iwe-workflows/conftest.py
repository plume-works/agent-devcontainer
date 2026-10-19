"""Fixtures for the IWE workflow e2e suite: the fixture repository and per-test clones."""

from collections.abc import Callable
from pathlib import Path
import re
import subprocess

from clone import build_fixture_repo, Clone, FixtureRepo, make_clone
import pytest

SUITE = Path(__file__).parent
REPO_ROOT = Path(
    subprocess.run(
        ['git', '-C', str(SUITE), 'rev-parse', '--show-toplevel'],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
)
WORK = REPO_ROOT / '.tmp/e2e/iwe-workflows'
# Every test shares the model provider's rate limits.
MAX_WORKERS = 3


def work_dir_name(nodeid: str) -> str:
    """Name a test's work directory after its module and test, safe as a path."""
    path, test = nodeid.split('::', 1)
    return re.sub(r'[^A-Za-z0-9_.-]+', '_', f'{Path(path).stem}-{test}')


@pytest.fixture(scope='session')
def fixture_repo(worker_id: str, pytestconfig: pytest.Config) -> FixtureRepo:
    """Build the fixture repository once per xdist worker, refusing too many workers."""
    workers = getattr(pytestconfig, 'workerinput', {}).get('workercount', 1)
    if workers > MAX_WORKERS:
        pytest.fail(f'the iwe-workflows suite runs at most -n {MAX_WORKERS}, not {workers}')
    return build_fixture_repo(REPO_ROOT, WORK / f'_fixture-{worker_id}')


@pytest.fixture
def clone_at(fixture_repo: FixtureRepo, request: pytest.FixtureRequest) -> Callable[[str], Clone]:
    """Clone the fixture repository for this test at a commit it names."""

    def make(start: str) -> Clone:
        return make_clone(fixture_repo, WORK / work_dir_name(request.node.nodeid), start)

    return make


@pytest.fixture
def base_clone(clone_at: Callable[[str], Clone], fixture_repo: FixtureRepo) -> Clone:
    """Provide a clone at the fixture plans' ``base`` commit."""
    return clone_at(fixture_repo.base)


@pytest.fixture
def open_question_clone(clone_at: Callable[[str], Clone], fixture_repo: FixtureRepo) -> Clone:
    """Provide a clone at the ``open_question`` commit."""
    return clone_at(fixture_repo.open_question)
