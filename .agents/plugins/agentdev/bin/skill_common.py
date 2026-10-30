#!/usr/bin/env python3

"""
Shared helpers for agentdev skill scripts written in Python.

Imported through the same ``sys.path`` entry that reaches ``result_codes``, so a
skill script ships no copy of its own. Standard library only.
"""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

PREFLIGHT_ERROR = 2


class Stop(Exception):
    """End the run with a declared result after the diagnostic was printed."""

    def __init__(self, code: int) -> None:
        super().__init__(code)
        self.code = code


def print_error(message: str) -> None:
    """Report a failure on stderr in the shared ERROR: form."""
    print(f'ERROR: {message}', file=sys.stderr)


def run_tool(*arguments: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run a command, capturing its output, without raising on failure."""
    return subprocess.run(list(arguments), check=False, capture_output=True, text=True, cwd=cwd)


def run_to_stderr(*arguments: str, cwd: Path | None = None) -> int:
    """Run a command with its stdout sent to stderr, keeping stdout for KEY=value lines."""
    sys.stdout.flush()
    return subprocess.run(list(arguments), check=False, stdout=sys.stderr, cwd=cwd).returncode


def run_inherited(*arguments: str, cwd: Path | None = None) -> int:
    """Run a command on this process's own stdout and stderr."""
    sys.stdout.flush()
    return subprocess.run(list(arguments), check=False, cwd=cwd).returncode


def require_git_repo() -> Path:
    """Return the repository's top level, or stop with a preflight error outside one."""
    completed = run_tool('git', 'rev-parse', '--show-toplevel')
    if completed.returncode != 0:
        print_error('This script must be run inside a Git repository.')
        raise Stop(PREFLIGHT_ERROR)
    return Path(completed.stdout.strip())


def current_branch() -> str:
    """Return the checked-out branch name, or HEAD when detached."""
    return run_tool('git', 'rev-parse', '--abbrev-ref', 'HEAD').stdout.strip()


def main_checkout_dir() -> Path | None:
    """Return the main checkout, which owns the Git directory linked worktrees share."""
    completed = run_tool('git', 'rev-parse', '--path-format=absolute', '--git-common-dir')
    if completed.returncode != 0:
        return None
    return Path(completed.stdout.strip()).parent


def skill_root(script: str) -> Path:
    """Return the skill directory of a script under ``<skill>/agent-code/``."""
    return Path(script).resolve().parents[1]


def help_header(description: str, script: str) -> str:
    """Return the description and skill root lines every script's help starts with."""
    return f'{description}\n\nSkill root: {skill_root(script)}\n'
