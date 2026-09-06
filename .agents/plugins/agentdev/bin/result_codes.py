#!/usr/bin/env python3

"""
Shared result-code helpers for agentdev skill scripts written in Python.

The Python counterpart of ``bin/result-codes.sh``: the same code-to-name table,
the same ``RESULT=<NAME>`` line as the last thing on stdout for every exit path,
and terminating signals named and then re-raised so a shell caller still
observes signal death rather than a normal exit.

Codes 0, 1, 2, 129, 130, and 143 are shared. Scripts declare outcomes from 3
through 125; a later assignment overrides an earlier name for the same code.
"""

from __future__ import annotations

import atexit
from collections.abc import Callable
import os
import signal
import sys
from types import FrameType

RESULT_CODES: dict[int, str] = {
    0: 'SUCCESS',
    1: 'SCRIPT_FAILURE',
    2: 'PREFLIGHT_ERROR',
    129: 'SIGNAL_HUP',
    130: 'SIGNAL_INT',
    143: 'SIGNAL_TERM',
}

_SIGNAL_CODES = {signal.SIGHUP: 129, signal.SIGINT: 130, signal.SIGTERM: 143}

_result_emitted = False
_previous_excepthook = sys.excepthook


def emit_result(code: int) -> None:
    """Print the RESULT line for `code`, at most once per process."""
    global _result_emitted
    if _result_emitted:
        return
    _result_emitted = True
    print(f'RESULT={RESULT_CODES.get(code, f"UNKNOWN_CODE_{code}")}')
    sys.stdout.flush()


def quit_by_code(code: int) -> None:
    """Exit with `code` after naming it, keeping RESULT the last line of stdout."""
    emit_result(code)
    sys.exit(code)


# `$?` has no Python equivalent readable from atexit, so the status is captured
# as it is produced: SystemExit carries its own code, and any other escaping
# exception is the interpreter's exit status 1.
_exit_status = 0


def _record_exit(exception: BaseException) -> None:
    """Remember the status `exception` will terminate the interpreter with."""
    global _exit_status
    if isinstance(exception, SystemExit):
        code = exception.code
        _exit_status = 0 if code is None else code if isinstance(code, int) else 1
    else:
        _exit_status = 1


def _report_unhandled_exit() -> None:
    """Keep the RESULT line total when a script exits without quit_by_code."""
    emit_result(_exit_status)


def _report_signal(signal_number: int, _frame: FrameType | None) -> None:
    """Name a terminating signal, restore its default action, then re-raise it."""
    emit_result(_SIGNAL_CODES[signal.Signals(signal_number)])
    signal.signal(signal_number, signal.SIG_DFL)
    os.kill(os.getpid(), signal_number)


def _excepthook(kind: type[BaseException], value: BaseException, traceback: object) -> None:
    """Record the exit status an escaping exception implies, then report it."""
    _record_exit(value)
    _previous_excepthook(kind, value, traceback)  # type: ignore[arg-type]


def run(main: Callable[[], int | None]) -> None:
    """
    Run `main` as the script body, then exit naming the status it produced.

    The entry point every Python skill script uses. ``SystemExit`` bypasses
    ``sys.excepthook``, so a bare ``sys.exit(2)`` inside `main` is only
    observable by catching it here — this is what keeps the RESULT name and the
    exit status agreeing on every path, as ``$?`` does for the bash helper.
    """
    try:
        code = main() or 0
    except SystemExit as requested:
        _record_exit(requested)
        code = _exit_status
    quit_by_code(code)


def install() -> None:
    """Install the exit hook, the exception hook, and the signal handlers."""
    global _previous_excepthook
    _previous_excepthook = sys.excepthook
    sys.excepthook = _excepthook
    atexit.register(_report_unhandled_exit)
    for terminating_signal in _SIGNAL_CODES:
        signal.signal(terminating_signal, _report_signal)
