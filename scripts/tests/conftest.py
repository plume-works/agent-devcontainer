"""
Session hooks: the root-only tests, and the container acceptance suite.

Tests marked ``requires_root`` skip unless the run is root; ``scripts/run-root-tests`` runs them
as root and nothing else.

The acceptance suite runs against AGENTDEV_RUNTIME_TEST_IMAGE.
Every container, volume, and network the suite makes carries ``ACCEPTANCE_LABEL``; the session
removes them all when it ends, so an interrupted test leaves nothing behind. A run that names an
image but skips every acceptance test fails: it accepted nothing.
"""

from __future__ import annotations

import os
import subprocess

from acceptance_label import ACCEPTANCE_LABEL
import pytest

ACCEPTANCE_MODULE = 'test_agent_runtime_acceptance.py'
IMAGE_VARIABLE = 'AGENTDEV_RUNTIME_TEST_IMAGE'
# Removal order: containers hold volumes and networks.
RESOURCES = (
    (('ps', '-aq'), ('rm', '-f')),
    (('volume', 'ls', '-q'), ('volume', 'rm', '-f')),
    (('network', 'ls', '-q'), ('network', 'rm')),
)

ROOT_MARKER = 'requires_root'
LAUNCHER_VARIABLE = 'AGENTDEV_ROOT_TEST_LAUNCHER'

_outcomes = {'ran': 0, 'skipped': 0}


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.geteuid() == 0:
        return
    skip = pytest.mark.skip(reason='requires root; run scripts/run-root-tests')
    for item in items:
        if item.get_closest_marker(ROOT_MARKER):
            item.add_marker(skip)


def pytest_collection_finish(session: pytest.Session) -> None:
    """Under the root-test launcher, refuse a run that would execute anything else as root."""
    if os.geteuid() != 0 or os.environ.get(LAUNCHER_VARIABLE) != '1':
        return
    others = [item.nodeid for item in session.items if not item.get_closest_marker(ROOT_MARKER)]
    if others:
        raise pytest.UsageError(
            f'the root-test launcher runs only {ROOT_MARKER} tests; also selected: '
            + ', '.join(others[:5])
            + (' …' if len(others) > 5 else '')
        )


def remove_labelled_resources() -> None:
    for listing, removal in RESOURCES:
        listed = subprocess.run(
            ['docker', *listing, '--filter', f'label={ACCEPTANCE_LABEL}'],
            capture_output=True,
            text=True,
            check=False,
        )
        ids = listed.stdout.split()
        if ids:
            subprocess.run(['docker', *removal, *ids], capture_output=True, check=False)


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    if not report.nodeid.split('::', 1)[0].endswith(ACCEPTANCE_MODULE):
        return
    if report.skipped and report.when in ('setup', 'call'):
        _outcomes['skipped'] += 1
    elif report.when == 'call':
        _outcomes['ran'] += 1


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    # Under xdist only the controller acts, once every worker has finished.
    if hasattr(session.config, 'workerinput') or not os.environ.get(IMAGE_VARIABLE):
        return
    remove_labelled_resources()
    if _outcomes['skipped'] and not _outcomes['ran']:
        reporter = session.config.pluginmanager.get_plugin('terminalreporter')
        if reporter is not None:
            reporter.write_line('every acceptance test was skipped', red=True)
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
