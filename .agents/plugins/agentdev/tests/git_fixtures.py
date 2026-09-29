#!/usr/bin/env python3

"""Shared helpers for tests of the git skill scripts: identity, git runner, stubs."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

FIXTURE_ENV = {
    'GIT_AUTHOR_NAME': 'Fixture Author',
    'GIT_AUTHOR_EMAIL': 'fixture@example.invalid',
    'GIT_COMMITTER_NAME': 'Fixture Author',
    'GIT_COMMITTER_EMAIL': 'fixture@example.invalid',
}


def git(cwd: Path, *args: str) -> str:
    """Run a fixture git command and return its stripped stdout."""
    completed = subprocess.run(
        ['git', *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, **FIXTURE_ENV},
    )
    return completed.stdout.strip()


def outcome(completed: subprocess.CompletedProcess[str]) -> tuple[int, str]:
    """Return the (exit code, last stdout line) contract pair."""
    return completed.returncode, completed.stdout.splitlines()[-1]


def stub_gh(directory: Path, script_body: str) -> Path:
    """Install a fake `gh` whose arguments are recorded next to it."""
    directory.mkdir()
    gh = directory / 'gh'
    gh.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{directory}/gh-args"\n{script_body}\n')
    gh.chmod(0o755)
    return directory
