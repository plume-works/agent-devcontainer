#!/usr/bin/env python3

"""Tests for the Depends on body check in bin/check_depends_on.py."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

RECORDED = '## Depends on\n\n- #591 — merged as d66fdf4d (head 7a8c22c2), reconnected\n- #600\n'


def check(
    plugin_root: Path, tmp: Path, body: str, *arguments: str, current: str | None = None
) -> tuple[int, str]:
    """Run the check on `body` via stdin; return (exit code, last stdout line)."""
    extra = list(arguments)
    if current is not None:
        current_file = tmp / 'current.md'
        current_file.write_text(current, encoding='utf-8')
        extra += ['--current', str(current_file)]
    completed = subprocess.run(
        [sys.executable, '-S', str(plugin_root / 'bin/check_depends_on.py'), '-', *extra],
        input=body, check=False, capture_output=True, text=True,
    )  # fmt: skip
    return completed.returncode, completed.stdout.splitlines()[-1]


def test_a_body_without_a_section_passes_when_none_is_required(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    assert check(plugin_root, plugin_tmp_path, '## Summary\n\nText.\n') == (0, 'RESULT=SUCCESS')


def test_a_required_section_that_is_missing_fails(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    body = '## Summary\n\nText.\n'
    assert check(plugin_root, plugin_tmp_path, body, '--depends-on', '5') == (
        3,
        'RESULT=NO_SECTION',
    )
    assert check(plugin_root, plugin_tmp_path, body, current=RECORDED) == (3, 'RESULT=NO_SECTION')


@pytest.mark.parametrize(
    'section',
    [
        '## Depends on\n\nNothing yet.\n',
        '## Depends on\n\n- #5\n- PR 6\n',
        '## Depends on\n\n- #5\n- #5\n',
    ],
)
def test_an_unparseable_section_fails(
    plugin_root: Path, plugin_tmp_path: Path, section: str
) -> None:
    assert check(plugin_root, plugin_tmp_path, f'## Summary\n\nText.\n\n{section}') == (
        4,
        'RESULT=UNPARSEABLE',
    )


def test_a_regenerated_body_keeps_the_recorded_section(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    current = f'## Summary\n\nOld.\n\n{RECORDED}\n## Related\n\n- #1\n'
    regenerated = f'## Summary\n\nNew text.\n\n{RECORDED}'
    assert check(plugin_root, plugin_tmp_path, regenerated, current=current) == (
        0,
        'RESULT=SUCCESS',
    )
    rewritten = regenerated.replace('reconnected', 'reconnected again')
    assert check(plugin_root, plugin_tmp_path, rewritten, current=current)[0] in (4, 5)
    dropped = regenerated.replace(' — merged as d66fdf4d (head 7a8c22c2), reconnected', '')
    assert check(plugin_root, plugin_tmp_path, dropped, current=current) == (
        5,
        'RESULT=SECTION_CHANGED',
    )


def test_entries_must_match_the_dependencies(plugin_root: Path, plugin_tmp_path: Path) -> None:
    body = '## Depends on\n\n- #3\n- #5\n'
    assert check(
        plugin_root, plugin_tmp_path, body, '--depends-on', '3', '--depends-on', '#5'
    ) == (
        0,
        'RESULT=SUCCESS',
    )
    assert check(plugin_root, plugin_tmp_path, body, '--depends-on', '5', '--depends-on', '3') == (
        6,
        'RESULT=ENTRIES_MISMATCH',
    )
