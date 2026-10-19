"""
The live gate every e2e suite under ``scripts/e2e`` shares.

Tests marked ``e2e`` drive real agent sessions and spend model usage, so they
are skipped unless ``E2E_RUN_LIVE`` opts in.
"""

import os

import pytest

LIVE_MARKER = 'e2e'
LIVE_OPT_IN_ENV = 'E2E_RUN_LIVE'
# Without these, `E2E_RUN_LIVE=0` would be truthy and spend model usage like `=1`.
LIVE_OPT_OUT_VALUES = ('', '0', 'false', 'no', 'off')


def live_opt_in() -> bool:
    """Whether the caller asked for the model-consuming tests to run."""
    value = os.environ.get(LIVE_OPT_IN_ENV, '').strip()
    return value.lower() not in LIVE_OPT_OUT_VALUES


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """
    Skip live tests unless the opt-in variable is set.

    The guard is at collection so that naming a node id or passing ``-m``,
    which replace any ``addopts`` filter, still cannot start a paid session.
    """
    if live_opt_in():
        return
    skip = pytest.mark.skip(
        reason=f'live e2e test spends model usage; set {LIVE_OPT_IN_ENV}=1 to run it'
    )
    for item in items:
        if item.get_closest_marker(LIVE_MARKER) is not None:
            item.add_marker(skip)
