"""The ``E2E_RUN_LIVE`` gate skips every ``e2e`` test unless it opts in."""

import importlib.util
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

import pytest
from scratch import TMP_ROOT

REPO_ROOT = Path(__file__).parents[2]
GATE = REPO_ROOT / 'scripts/e2e/conftest.py'
_spec = importlib.util.spec_from_file_location('e2e_live_gate', GATE)
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)
LIVE_OPT_IN_ENV = gate.LIVE_OPT_IN_ENV
LIVE_OPT_OUT_VALUES = gate.LIVE_OPT_OUT_VALUES

TEST_MODULE = """
import pytest

@pytest.mark.e2e
def test_live():
    pass
"""


@pytest.fixture
def suite():
    """Provide a throwaway suite under /tmp guarded by the real gate."""
    path = TMP_ROOT / f'e2e-live-gate-{uuid.uuid4().hex}'
    path.mkdir(parents=True)
    shutil.copy(GATE, path / 'conftest.py')
    (path / 'test_gated.py').write_text(TEST_MODULE)
    (path / 'pytest.ini').write_text('[pytest]\nmarkers =\n    e2e: live\n')
    yield path
    shutil.rmtree(path)


def run(suite: Path, value: str | None, *args: str) -> str:
    """Run the throwaway suite with the opt-in variable set to ``value``."""
    env = {k: v for k, v in os.environ.items() if k != LIVE_OPT_IN_ENV}
    if value is not None:
        env[LIVE_OPT_IN_ENV] = value
    result = subprocess.run(
        [sys.executable, '-m', 'pytest', '-p', 'no:cacheprovider', '-rs', *args],
        cwd=suite,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout


SELECTIONS = [(), ('test_gated.py::test_live',), ('-m', 'e2e')]


@pytest.mark.parametrize('args', SELECTIONS, ids=['path', 'node-id', 'marker'])
@pytest.mark.parametrize('value', [None, *LIVE_OPT_OUT_VALUES, ' OFF '])
def test_skipped_unless_opted_in(suite, value, args):
    """Every off value skips the test however it is selected."""
    out = run(suite, value, *args)
    assert '1 skipped' in out, out
    assert LIVE_OPT_IN_ENV in out, out


@pytest.mark.parametrize('args', SELECTIONS, ids=['path', 'node-id', 'marker'])
def test_runs_when_opted_in(suite, args):
    """``E2E_RUN_LIVE=1`` runs the marked test."""
    out = run(suite, '1', *args)
    assert '1 passed' in out, out
