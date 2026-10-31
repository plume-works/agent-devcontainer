#!/usr/bin/env python3

"""Tests for the GitHub issue helpers in bin/github_issue.py."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT_PATH = 'bin/github_issue.py'


def run_helper(
    plugin_root: Path, cwd: Path, *arguments: str, path: str | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the helper's command line with only the standard library."""
    environment = dict(os.environ)
    if path is not None:
        environment['PATH'] = path
    return subprocess.run(
        [sys.executable, '-S', str(plugin_root / SCRIPT_PATH), *arguments],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def install_gh(directory: Path, view_exit: int, view_output: str, close_exit: int = 0) -> Path:
    """Create a fake `gh` that answers `issue view` and logs `issue close` arguments."""
    directory.mkdir()
    stub = directory / 'gh'
    stub.write_text(
        f'#!{sys.executable}\n'
        'import sys\n'
        'arguments = sys.argv[1:]\n'
        'if arguments[:2] == ["issue", "view"]:\n'
        f'    print({view_output!r})\n'
        f'    sys.exit({view_exit})\n'
        'if arguments[:2] == ["issue", "close"]:\n'
        f'    open({str(directory / "close.log")!r}, "a").write(" ".join(arguments) + "\\n")\n'
        '    print("closed")\n'
        f'    sys.exit({close_exit})\n'
        'sys.exit(1)\n'
    )
    stub.chmod(0o755)
    return directory


@pytest.mark.parametrize(
    ('ref', 'repo', 'number'),
    [
        ('https://github.com/octo/repo/issues/42', 'octo/repo', '42'),
        ('https://github.com/octo/re.po/issues/42/#issuecomment-1', 'octo/re.po', '42'),
        ('octo/repo#7', 'octo/repo', '7'),
        ('#9', '', '9'),
        ('11', '', '11'),
    ],
)
def test_parse_accepts_every_reference_form(
    plugin_root: Path, plugin_tmp_path: Path, ref: str, repo: str, number: str
) -> None:
    """URLs, OWNER/REPO#N, #N, and N must all parse; the bare forms leave the repo empty."""
    completed = run_helper(plugin_root, plugin_tmp_path, 'parse', ref)

    assert completed.returncode == 0
    assert completed.stdout == f'ISSUE_REPO={repo}\nISSUE_NUMBER={number}\n'


@pytest.mark.parametrize('ref', ['octo#1', 'https://github.com/octo/repo/pull/1', 'x', ''])
def test_parse_rejects_other_text(plugin_root: Path, plugin_tmp_path: Path, ref: str) -> None:
    """Anything else must be rejected with exit 1 and no output."""
    completed = run_helper(plugin_root, plugin_tmp_path, 'parse', ref)

    assert (completed.returncode, completed.stdout) == (1, '')


def test_close_open_issue_comments_and_closes(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """An open issue must be closed once with the comment, gh's chatter kept off stdout."""
    stubs = install_gh(
        plugin_tmp_path / 'stubs',
        0,
        'ISSUE_URL=https://github.com/octo/repo/issues/42\nISSUE_STATE=OPEN',
    )

    completed = run_helper(
        plugin_root, plugin_tmp_path, 'close', 'octo/repo', '42', 'Done.', path=str(stubs)
    )

    assert completed.returncode == 0
    assert completed.stdout == (
        'ISSUE_REPO=octo/repo\nISSUE_NUMBER=42\n'
        'ISSUE_URL=https://github.com/octo/repo/issues/42\nISSUE_STATE=CLOSED\n'
    )
    assert 'closed' in completed.stderr
    assert (stubs / 'close.log').read_text() == (
        'issue close 42 --repo octo/repo --comment Done.\n'
    )


def test_close_already_closed_issue_posts_nothing(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A closed issue must return 5 without a comment."""
    stubs = install_gh(
        plugin_tmp_path / 'stubs', 0, 'ISSUE_URL=https://x/issues/42\nISSUE_STATE=CLOSED'
    )

    completed = run_helper(
        plugin_root, plugin_tmp_path, 'close', 'octo/repo', '42', 'Done.', path=str(stubs)
    )

    assert completed.returncode == 5
    assert completed.stdout.endswith('ISSUE_STATE=CLOSED\n')
    assert 'already closed; no comment posted' in completed.stderr
    assert not (stubs / 'close.log').exists()


@pytest.mark.parametrize(
    ('view_output', 'expected'),
    [
        ('GraphQL: Could not resolve to an issue or pull request', 4),
        ('HTTP 502: Bad Gateway', 3),
    ],
)
def test_close_view_failure_maps_to_its_code(
    plugin_root: Path, plugin_tmp_path: Path, view_output: str, expected: int
) -> None:
    """A missing issue must return 4 and any other view failure 3, printing no key lines."""
    stubs = install_gh(plugin_tmp_path / 'stubs', 1, view_output)

    completed = run_helper(
        plugin_root, plugin_tmp_path, 'close', 'octo/repo', '42', 'Done.', path=str(stubs)
    )

    assert (completed.returncode, completed.stdout) == (expected, '')
    assert view_output in completed.stderr


def test_close_failure_returns_three(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A failing gh issue close must return 3 and not claim the issue closed."""
    stubs = install_gh(
        plugin_tmp_path / 'stubs', 0, 'ISSUE_URL=https://x\nISSUE_STATE=OPEN', close_exit=1
    )

    completed = run_helper(
        plugin_root, plugin_tmp_path, 'close', 'octo/repo', '42', 'Done.', path=str(stubs)
    )

    assert completed.returncode == 3
    assert 'ISSUE_STATE' not in completed.stdout
    assert 'ERROR: gh issue close failed for octo/repo#42.' in completed.stderr
