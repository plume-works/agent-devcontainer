#!/usr/bin/env python3

"""Behavior tests for the extract-github-actions-logs URL parser."""

from __future__ import annotations

from pathlib import Path
import subprocess

from git_fixtures import outcome
import pytest

SCRIPT_PATH = 'skills/extract-github-actions-logs/agent-code/parse-actions-url.py'
RUN = 'https://github.com/octo/repo/actions/runs/12345678901'
JOB = f'{RUN}/job/23456789012?pr=42'
FAILURES = r'FAILED\|FAILURES\|AssertionError\|ERROR:\|Segmentation\ fault\|test_'


def run_script(plugin_root: Path, *arguments: str) -> subprocess.CompletedProcess[str]:
    """Run the parser."""
    return subprocess.run(
        [str(plugin_root / SCRIPT_PATH), *arguments],
        check=False,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    ('url', 'lines'),
    [
        (RUN, ['REPO=octo/repo', 'RUN_ID=12345678901']),
        (f'{RUN}/', None),
        (JOB, ['REPO=octo/repo', 'RUN_ID=12345678901', 'JOB_ID=23456789012']),
        (f'{RUN}/attempts/2/job/7#step:3:1', ['REPO=octo/repo', 'RUN_ID=12345678901', 'JOB_ID=7']),
        ('https://github.com/o-1/r.x/actions/runs/5?check_suite_focus=true',
         ['REPO=o-1/r.x', 'RUN_ID=5']),
    ],
)  # fmt: skip
def test_fields(plugin_root: Path, url: str, lines: list[str] | None) -> None:
    """A run or job URL yields REPO, RUN_ID, and JOB_ID for a job."""
    completed = run_script(plugin_root, '--url', url)

    if lines is None:
        assert outcome(completed) == (3, 'RESULT=UNSUPPORTED_URL')
    else:
        assert outcome(completed) == (0, 'RESULT=SUCCESS')
        assert completed.stdout.splitlines()[:-1] == lines


@pytest.mark.parametrize(
    ('url', 'flags', 'command'),
    [
        (RUN, [], 'gh run view 12345678901 --repo octo/repo'),
        (JOB, ['--log'], 'gh run view 12345678901 --repo octo/repo --job 23456789012 --log'),
        (JOB, ['--log', '--grep-failures'],
         f'gh run view 12345678901 --repo octo/repo --job 23456789012 --log | grep -nE {FAILURES}'),
        ("https://github.com/o'q/r$x/actions/runs/1", [],
         "gh run view 1 --repo o\\'q/r\\$x"),
    ],
)  # fmt: skip
def test_command(plugin_root: Path, url: str, flags: list[str], command: str) -> None:
    """--format command prints one shell-quoted gh command line."""
    completed = run_script(plugin_root, '--url', url, '--format', 'command', *flags)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert completed.stdout.splitlines()[:-1] == [command]


def test_fields_are_shell_quoted(plugin_root: Path) -> None:
    """Field values are printed shell-quoted, as printf %q renders them."""
    completed = run_script(plugin_root, '--url', 'https://github.com/a b/c/actions/runs/1')

    assert completed.stdout.splitlines()[0] == 'REPO=a\\ b/c'


@pytest.mark.parametrize(
    ('arguments', 'message'),
    [
        ([], 'Missing required --url argument'),
        (['--url'], 'Missing value for --url'),
        (['--url', RUN, '--format', 'json'], 'Unsupported --format value: json'),
        (['--url', RUN, '--grep-failures'], '--grep-failures requires --format command'),
        (['--bogus'], 'Unknown argument: --bogus'),
    ],
)
def test_usage_errors(plugin_root: Path, arguments: list[str], message: str) -> None:
    """Usage errors are preflight errors."""
    completed = run_script(plugin_root, *arguments)

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert f'ERROR: {message}' in completed.stderr


def test_other_urls_are_unsupported(plugin_root: Path) -> None:
    """A pull request URL is not an Actions URL."""
    completed = run_script(plugin_root, '--url', 'https://github.com/octo/repo/pull/1')

    assert outcome(completed) == (3, 'RESULT=UNSUPPORTED_URL')


def test_help(plugin_root: Path) -> None:
    """--help prints the usage and succeeds."""
    completed = run_script(plugin_root, '--help')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert completed.stdout.startswith('Parse a GitHub Actions run or job URL')
