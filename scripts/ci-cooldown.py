#!/usr/bin/env python3
"""
Hold a Primary checks run on main for the cooldown before any build job starts.

A newer push cancels the waiting run, so a burst of merges builds once. The wait never runs past
the cap, measured from the oldest push run since the newest one that was not cancelled.
See ADR-0046.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
import os
import sys
import time

import ci_runs

DEFAULTS = {'MAIN_COOLDOWN_SECONDS': 600, 'MAIN_COOLDOWN_MAX_SECONDS': 1800}
BRANCH = 'main'


class SettingError(Exception):
    """A cooldown variable that is not a non-negative integer."""


def _setting(env: Mapping[str, str], name: str) -> int:
    """Return a non-negative integer variable, or its default when unset or empty."""
    raw = env.get(name, '').strip()
    if not raw:
        return DEFAULTS[name]
    try:
        value = int(raw)
    except ValueError as error:
        raise SettingError(f'{name} must be a non-negative integer, got {raw!r}') from error
    if value < 0:
        raise SettingError(f'{name} must be a non-negative integer, got {raw!r}')
    return value


def _timestamp(value: str) -> float:
    """Return the epoch seconds of an API timestamp."""
    return datetime.fromisoformat(value).timestamp()


def _anchor(env: Mapping[str, str]) -> tuple[int, float]:
    """Return the id and start of the oldest push run since the newest one not cancelled."""
    own = ci_runs.current_run(env)
    runs = ci_runs.push_runs(env, own['workflow_id'], BRANCH)
    ids = [run['id'] for run in runs]
    older = runs[ids.index(own['id']) + 1 :] if own['id'] in ids else runs
    anchor = own
    for run in older:
        if run.get('conclusion') != 'cancelled':
            break
        anchor = run
    return anchor['id'], _timestamp(anchor['created_at'])


def main(
    env: Mapping[str, str] | None = None,
    now: Callable[[], float] = time.time,
    sleep: Callable[[float], None] = time.sleep,
) -> int:
    """Sleep for the cooldown, cut short at the cap."""
    env = os.environ if env is None else env
    try:
        cooldown = _setting(env, 'MAIN_COOLDOWN_SECONDS')
        cap = _setting(env, 'MAIN_COOLDOWN_MAX_SECONDS')
    except SettingError as error:
        print(f'ci-cooldown: {error}', file=sys.stderr)
        return 2
    try:
        run_id, started = _anchor(env)
    except (ci_runs.CIRunsError, KeyError, ValueError) as error:
        print(f'::warning::Could not read the run history ({error}); waiting the full cooldown.')
        wait = float(cooldown)
    else:
        wait = max(0.0, min(cooldown, started + cap - now()))
        print(f'ci-cooldown: anchor run {run_id} started at {started:.0f}')
    print(f'ci-cooldown: waiting {wait:.0f}s (cooldown {cooldown}s, cap {cap}s)')
    sleep(wait)
    return 0


if __name__ == '__main__':
    sys.exit(main())
