"""
Session hooks for the container acceptance suite run against AGENTDEV_RUNTIME_TEST_IMAGE.

Every container, volume, and network the suite makes carries ``ACCEPTANCE_LABEL``; the session
removes them all when it ends, so an interrupted test leaves nothing behind. A run that names an
image but skips every acceptance test fails: it accepted nothing.
"""

from __future__ import annotations

import os
import subprocess

import pytest

ACCEPTANCE_LABEL = 'agentdev.test=acceptance'
ACCEPTANCE_MODULE = 'test_agent_runtime_acceptance.py'
IMAGE_VARIABLE = 'AGENTDEV_RUNTIME_TEST_IMAGE'
# Removal order: containers hold volumes and networks.
RESOURCES = (
    (('ps', '-aq'), ('rm', '-f')),
    (('volume', 'ls', '-q'), ('volume', 'rm', '-f')),
    (('network', 'ls', '-q'), ('network', 'rm')),
)

_outcomes = {'ran': 0, 'skipped': 0}


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
