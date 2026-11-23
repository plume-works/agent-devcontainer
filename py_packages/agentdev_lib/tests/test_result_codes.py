#!/usr/bin/env python3

"""Behavior tests for the shared skill-script result-code helper."""

from __future__ import annotations

import signal
import subprocess
import sys


def run_python_helper(body: str) -> subprocess.CompletedProcess[str]:
    """Run `body` as a script main() under the Python result-code helper."""
    indented = '\n'.join(f'    {line}' for line in body.split('\n'))
    source = (
        'import os, signal, sys\n'
        'from agentdev_lib import result_codes as rc\n'
        'rc.install()\n'
        'def main():\n'
        f'{indented}\n'
        'rc.run(main)\n'
    )
    return subprocess.run(
        [sys.executable, '-c', source],
        capture_output=True,
        text=True,
        check=False,
    )


def test_python_result_codes_preserve_terminating_signals() -> None:
    """The Python helper names terminating signals and re-raises them as the shell one does."""
    # Arrange
    outcomes: dict[str, tuple[int, int, str]] = {}

    # Act
    for interrupt_signal in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        process = run_python_helper(f'os.kill(os.getpid(), {interrupt_signal.value})')
        shell_status = 128 - process.returncode if process.returncode < 0 else process.returncode
        outcomes[interrupt_signal.name] = (
            process.returncode,
            shell_status,
            process.stdout,
        )

    # Assert
    assert outcomes == {
        signal.SIGHUP.name: (-signal.SIGHUP, 129, 'RESULT=SIGNAL_HUP\n'),
        signal.SIGINT.name: (-signal.SIGINT, 130, 'RESULT=SIGNAL_INT\n'),
        signal.SIGTERM.name: (-signal.SIGTERM, 143, 'RESULT=SIGNAL_TERM\n'),
    }


def test_python_result_line_is_last_on_a_normal_exit() -> None:
    """RESULT closes stdout after whatever the script printed."""
    # Act
    process = run_python_helper('print("verdict line")')

    # Assert
    assert process.returncode == 0
    assert process.stdout.splitlines() == ['verdict line', 'RESULT=SUCCESS']


def test_python_result_line_is_last_on_an_uncaught_exception() -> None:
    """An uncaught exception still ends stdout with RESULT, exiting SCRIPT_FAILURE."""
    # Act
    process = run_python_helper('print("partial work")\nraise ValueError("boom")')

    # Assert
    assert process.returncode == 1
    assert process.stdout.splitlines() == ['partial work', 'RESULT=SCRIPT_FAILURE']
    assert 'ValueError: boom' in process.stderr


def test_python_bare_exit_is_named_like_the_shell_helper() -> None:
    """A bare sys.exit inside the script body is named, as `$?` names it in bash."""
    # Act
    process = run_python_helper('sys.exit(2)')

    # Assert
    assert (process.returncode, process.stdout) == (2, 'RESULT=PREFLIGHT_ERROR\n')


def test_python_unknown_code_renders_as_unknown() -> None:
    """A code with no registered name renders as UNKNOWN_CODE_<n>, as emit_result does."""
    # Act
    process = run_python_helper('rc.quit_by_code(7)')

    # Assert
    assert (process.returncode, process.stdout) == (7, 'RESULT=UNKNOWN_CODE_7\n')


def test_python_uncaught_exception_prints_one_line_and_no_traceback() -> None:
    """An escaping exception is named in one stderr line; status and RESULT are unchanged."""
    # Act
    process = run_python_helper('raise ValueError("bad fixture input")')

    # Assert
    assert (process.returncode, process.stdout) == (1, 'RESULT=SCRIPT_FAILURE\n')
    assert process.stderr == 'ERROR: -c: ValueError: bad fixture input\n'


def test_python_failed_subprocess_prints_its_own_stderr() -> None:
    """A CalledProcessError names the command's failure and adds the command's stderr."""
    # Act
    process = run_python_helper(
        'import subprocess\n'
        "subprocess.run(['sh', '-c', 'echo fixture boom >&2; exit 3'],"
        ' check=True, capture_output=True, text=True)',
    )

    # Assert
    assert (process.returncode, process.stdout) == (1, 'RESULT=SCRIPT_FAILURE\n')
    assert 'Traceback' not in process.stderr
    assert process.stderr.splitlines() == [
        "ERROR: -c: CalledProcessError: Command '['sh', '-c', 'echo fixture boom >&2; exit 3']'"
        ' returned non-zero exit status 3.',
        'fixture boom',
    ]
