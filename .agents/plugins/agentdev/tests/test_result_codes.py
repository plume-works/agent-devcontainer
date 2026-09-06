#!/usr/bin/env python3

"""Behavior tests for the shared skill-script result-code helper."""

from __future__ import annotations

from pathlib import Path
import signal
import subprocess
import sys


def test_canonical_result_codes_preserve_terminating_signals(plugin_root: Path) -> None:
    """Name terminating signals while preserving their shell exit statuses."""
    # Arrange
    result_codes = plugin_root / 'bin/result-codes.sh'
    outcomes: dict[str, tuple[int, int, str]] = {}

    # Act
    for interrupt_signal in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        process = subprocess.run(
            [
                'bash',
                '-c',
                'source "$1"; kill -s "$2" "$$"',
                'bash',
                str(result_codes),
                interrupt_signal.name,
            ],
            cwd=plugin_root,
            capture_output=True,
            text=True,
            check=False,
        )
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


def run_python_helper(plugin_root: Path, body: str) -> subprocess.CompletedProcess[str]:
    """Run `body` as a script main() under the Python result-code helper."""
    indented = '\n'.join(f'    {line}' for line in body.split('\n'))
    source = (
        'import os, signal, sys\n'
        f'sys.path.insert(0, {str(plugin_root / "bin")!r})\n'
        'import result_codes as rc\n'
        'rc.install()\n'
        'def main():\n'
        f'{indented}\n'
        'rc.run(main)\n'
    )
    return subprocess.run(
        [sys.executable, '-c', source],
        cwd=plugin_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_python_result_codes_preserve_terminating_signals(plugin_root: Path) -> None:
    """The Python helper names terminating signals and re-raises them as the shell one does."""
    # Arrange
    outcomes: dict[str, tuple[int, int, str]] = {}

    # Act
    for interrupt_signal in (signal.SIGHUP, signal.SIGINT, signal.SIGTERM):
        process = run_python_helper(plugin_root, f'os.kill(os.getpid(), {interrupt_signal.value})')
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


def test_python_result_line_is_last_on_a_normal_exit(plugin_root: Path) -> None:
    """RESULT closes stdout after whatever the script printed."""
    # Act
    process = run_python_helper(plugin_root, 'print("verdict line")')

    # Assert
    assert process.returncode == 0
    assert process.stdout.splitlines() == ['verdict line', 'RESULT=SUCCESS']


def test_python_result_line_is_last_on_an_uncaught_exception(plugin_root: Path) -> None:
    """An uncaught exception still ends stdout with RESULT, exiting SCRIPT_FAILURE."""
    # Act
    process = run_python_helper(plugin_root, 'print("partial work")\nraise ValueError("boom")')

    # Assert
    assert process.returncode == 1
    assert process.stdout.splitlines() == ['partial work', 'RESULT=SCRIPT_FAILURE']
    assert 'ValueError: boom' in process.stderr


def test_python_bare_exit_is_named_like_the_shell_helper(plugin_root: Path) -> None:
    """A bare sys.exit inside the script body is named, as `$?` names it in bash."""
    # Act
    process = run_python_helper(plugin_root, 'sys.exit(2)')

    # Assert
    assert (process.returncode, process.stdout) == (2, 'RESULT=PREFLIGHT_ERROR\n')


def test_python_unknown_code_renders_as_unknown(plugin_root: Path) -> None:
    """A code with no registered name renders as UNKNOWN_CODE_<n>, as emit_result does."""
    # Act
    process = run_python_helper(plugin_root, 'rc.quit_by_code(7)')

    # Assert
    assert (process.returncode, process.stdout) == (7, 'RESULT=UNKNOWN_CODE_7\n')
