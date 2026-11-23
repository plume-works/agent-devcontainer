"""
The runtime's readiness and a status report, read from systemd's view of the image's units.

The image healthcheck and ``postStartCommand`` read the readiness; systemd supervises the
services, and this module only asks it. See ADR-0107. ``agentdev-runtime health ready|status``
exits 0 when ready.
"""

from __future__ import annotations

import subprocess
import sys

# Required for the editor to attach; Xpra is a convenience and only reported.
CORE_UNITS = ('agentdev-bootstrap.service', 'docker.service', 'agentdev-created.service')
OPTIONAL_USER_UNITS = ('agentdev-xpra.service',)
USAGE = 'usage: agentdev-runtime health ready|status'


def _run(command: list[str], timeout: float = 10) -> subprocess.CompletedProcess[str] | None:
    """Run a query; None when it timed out or its program is missing."""
    try:
        return subprocess.run(
            command, capture_output=True, text=True, timeout=timeout, check=False
        )
    except subprocess.TimeoutExpired:
        return None
    except OSError as error:
        print(f'{command[0]}: {error}', file=sys.stderr)
        return None


def unit_states(units: tuple[str, ...], user: bool = False) -> dict[str, str]:
    """Map each unit to its ``systemctl is-active`` word; ``unknown`` when systemd cannot say."""
    scope = ['--user'] if user else []
    result = _run(['systemctl', *scope, 'is-active', *units])
    words = result.stdout.split() if result is not None else []
    if len(words) != len(units):
        return dict.fromkeys(units, 'unknown')
    return dict(zip(units, words, strict=True))


def failed(units: tuple[str, ...] = CORE_UNITS) -> list[str]:
    """Return the core units systemd reports as failed."""
    return [unit for unit, state in unit_states(units).items() if state == 'failed']


def ready() -> int:
    """Pass only while every core unit is active and the engine answers."""
    for unit, state in unit_states(CORE_UNITS).items():
        if state != 'active':
            print(f'{unit}: {state}')
            return 1
    engine = _run(['docker', 'info', '--format', '{{.ServerVersion}}'])
    if engine is None or engine.returncode != 0:
        print('docker.service is active, but the engine does not answer')
        return 1
    return 0


def status() -> int:
    """Print each unit's state and how to read a failed one's log."""
    states = unit_states(CORE_UNITS)
    for unit, state in states.items():
        print(f'{unit}: {state}')
    for unit, state in unit_states(OPTIONAL_USER_UNITS, user=True).items():
        print(f'{unit} (user): {state}')
    broken = [unit for unit, state in states.items() if state == 'failed']
    for unit in broken:
        print(f'  log: journalctl -u {unit} -b --no-pager')
    return 0 if all(state == 'active' for state in states.values()) else 1


def main(argv: list[str]) -> int:
    """Dispatch ``agentdev-runtime health ready|status``."""
    if argv == ['ready']:
        return ready()
    if argv == ['status']:
        return status()
    print(USAGE, file=sys.stderr)
    return 2
