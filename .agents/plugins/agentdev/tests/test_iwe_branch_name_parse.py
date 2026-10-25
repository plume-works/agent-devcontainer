#!/usr/bin/env python3

"""Behavior tests for iwe-branch-name.py parse and its result contract."""

from __future__ import annotations

from pathlib import Path
import sys

from git_fixtures import outcome
from iwe_branch_fixtures import run_script
import pytest


@pytest.mark.parametrize(
    ('branch', 'phase', 'slug', 'iteration'),
    [
        ('impl/focus-timer/iteration-1', 'impl', 'focus-timer', '1'),
        ('ship/focus-timer/iteration-2', 'ship', 'focus-timer', '2'),
        ('impl/focus-timer/iteration-12', 'impl', 'focus-timer', '12'),
    ],
)
def test_parse_splits_a_work_branch(
    plugin_root: Path, plugin_tmp_path: Path, branch: str, phase: str, slug: str, iteration: str
) -> None:
    """A name of the shape reports its phase, slug, and iteration."""
    completed, values = run_script(plugin_root, plugin_tmp_path, 'parse', branch)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert (values['PHASE'], values['SLUG'], values['ITERATION']) == (phase, slug, iteration)


@pytest.mark.parametrize(
    'branch',
    [
        'focus-timer',
        'impl/focus-timer',
        'impl/focus-timer/iteration-0',
        'impl/focus-timer/iteration-01',
        'review/focus-timer/iteration-1',
    ],
)
def test_parse_rejects_a_name_off_the_shape(
    plugin_root: Path, plugin_tmp_path: Path, branch: str
) -> None:
    """A bare slug, a missing suffix, iteration 0, or an unknown phase is not a work branch."""
    completed, values = run_script(plugin_root, plugin_tmp_path, 'parse', branch)

    assert outcome(completed) == (3, 'RESULT=NOT_A_WORK_BRANCH')
    assert not {'PHASE', 'SLUG', 'ITERATION'} & values.keys()


def test_help_prints_the_results_table(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """--help is the run's product and lists every declared result with its code."""
    completed, _ = run_script(plugin_root, plugin_tmp_path, '--help')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    for row in (
        'NOT_A_WORK_BRANCH  3',
        'AMBIGUOUS_PLAN     4',
        'FETCH_FAILED       5',
        'PREFLIGHT_ERROR    2',
    ):
        assert row in completed.stdout


def test_usage_error_is_a_preflight_error(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A missing subcommand argument stops before any lookup."""
    completed, _ = run_script(plugin_root, plugin_tmp_path, 'parse')

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')


def test_script_imports_only_the_standard_library(plugin_root: Path) -> None:
    """The script runs from a consumer's plugin cache with nothing installed."""
    source = (plugin_root / 'skills/iwe-branch-name/agent-code/iwe-branch-name.py').read_text()
    imports = {
        line.split()[1].split('.')[0]
        for line in source.splitlines()
        if line.startswith(('import ', 'from '))
    }

    assert imports - {'result_codes'} <= sys.stdlib_module_names
