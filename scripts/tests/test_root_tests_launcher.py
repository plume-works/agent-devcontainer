"""The requires_root marker, the root-test launcher, and the guard that keeps it to those tests."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[2]
LAUNCHER = REPO / 'scripts/run-root-tests'
MARKED = f'{Path(__file__).relative_to(REPO)}::test_a_marked_test_runs_only_as_root'
UNMARKED = f'{Path(__file__).relative_to(REPO)}::test_an_unmarked_test_runs_for_anyone'
NOBODY = 65534


def pytest_run(*args: str, env: dict[str, str], user: int | None = None):
    command = [sys.executable, '-m', 'pytest', '-p', 'no:cacheprovider', *args]
    if user is not None:
        command = ['setpriv', f'--reuid={user}', f'--regid={user}', '--clear-groups', *command]
    return subprocess.run(
        command, cwd=REPO, env=env, capture_output=True, text=True, timeout=120, check=False
    )


def clean_env(**extra: str) -> dict[str, str]:
    return {'PATH': os.environ['PATH'], 'PYTHONDONTWRITEBYTECODE': '1', **extra}


@pytest.mark.requires_root
def test_a_marked_test_runs_only_as_root():
    assert os.geteuid() == 0


def test_an_unmarked_test_runs_for_anyone():
    assert True


def test_a_marked_test_skips_without_root():
    user = NOBODY if os.geteuid() == 0 else None
    result = pytest_run('-rs', MARKED, env=clean_env(), user=user)
    assert result.returncode == 0, result.stdout + result.stderr
    assert '1 skipped' in result.stdout
    assert 'requires root; run scripts/run-root-tests' in result.stdout


@pytest.mark.requires_root
def test_the_launcher_guard_rejects_an_unmarked_test():
    env = clean_env(AGENTDEV_ROOT_TEST_LAUNCHER='1')
    result = pytest_run('--collect-only', MARKED, UNMARKED, env=env)
    assert result.returncode == pytest.ExitCode.USAGE_ERROR, result.stdout + result.stderr
    assert 'the root-test launcher runs only requires_root tests' in result.stderr
    assert UNMARKED in result.stderr


@pytest.mark.requires_root
def test_root_without_the_launcher_runs_any_test():
    result = pytest_run(MARKED, UNMARKED, env=clean_env())
    assert result.returncode == 0, result.stdout + result.stderr
    assert '2 passed' in result.stdout


@pytest.mark.requires_root
def test_the_launcher_refuses_to_run_as_root():
    result = subprocess.run(
        [str(LAUNCHER)], env=clean_env(), capture_output=True, text=True, check=False
    )
    assert result.returncode == 2
    assert 'already root' in result.stderr
