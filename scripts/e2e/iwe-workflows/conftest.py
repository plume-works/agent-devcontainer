"""Fixtures for the IWE workflow e2e suite: the fixture repository and per-test clones."""

from collections.abc import Callable, Iterator
import os
from pathlib import Path
import re
import subprocess

from clone import build_fixture_repo, Clone, FixtureRepo, make_clone, make_main_clone
from harness_opencode import CATALOG_TIMEOUT, OpenCodeServer, READY_TIMEOUT, start_server
import opencode_credential
import pytest
from scenarios import OPENCODE_BUDGET

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
def main_clone(fixture_repo: FixtureRepo, request: pytest.FixtureRequest) -> Clone:
    """Provide a ``base`` clone on ``main`` with a bare ``origin`` and a stub ``gh``."""
    parent = WORK / work_dir_name(request.node.nodeid)
    return make_main_clone(fixture_repo, parent, fixture_repo.base)


@pytest.fixture
def open_question_clone(clone_at: Callable[[str], Clone], fixture_repo: FixtureRepo) -> Clone:
    """Provide a clone at the ``open_question`` commit."""
    return clone_at(fixture_repo.open_question)


@pytest.fixture
def implement_all_clone(clone_at: Callable[[str], Clone], fixture_repo: FixtureRepo) -> Clone:
    """Provide a clone at the ``implement_all`` commit, where the loop and pair plans are active."""
    return clone_at(fixture_repo.implement_all)


@pytest.fixture
def stub_evaluator_clone(clone_at: Callable[[str], Clone], fixture_repo: FixtureRepo) -> Clone:
    """Provide a clone whose catalog evaluator rejects every revision."""
    return clone_at(fixture_repo.stub_evaluator)


@pytest.fixture
def stub_planner_clone(clone_at: Callable[[str], Clone], fixture_repo: FixtureRepo) -> Clone:
    """Provide a clone whose catalog planner always drafts the revise plan's narrowing."""
    return clone_at(fixture_repo.stub_planner)


@pytest.fixture(scope='session')
def opencode_source() -> opencode_credential.Server:
    """Locate the web UI's OpenCode 2.x server, or skip the OpenCode tests."""
    try:
        source = opencode_credential.source_from_environment()
        opencode_credential.require_v2(source)
    except opencode_credential.SourceUnavailable as error:
        pytest.skip(str(error))
    return source


@pytest.fixture
def opencode_login(opencode_source: opencode_credential.Server) -> dict:
    """Return the source's ChatGPT login, valid through server startup and this test's budget."""
    life = READY_TIMEOUT + CATALOG_TIMEOUT + OPENCODE_BUDGET
    return opencode_credential.fresh_credential(opencode_source, life)


@pytest.fixture
def opencode(opencode_login: dict) -> Iterator[Callable[[Clone], OpenCodeServer]]:
    """Start isolated OpenCode servers for this test's clone; kill each at teardown."""
    started: list[OpenCodeServer] = []

    def start(clone: Clone) -> OpenCodeServer:
        server = start_server(clone, opencode_login, os.environ.get('OPENCODE_BIN') or 'opencode')
        started.append(server)
        return server

    yield start
    for server in started:
        server.stop()
