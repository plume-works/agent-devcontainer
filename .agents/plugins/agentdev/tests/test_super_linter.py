#!/usr/bin/env python3

"""Tests for the Super-Linter environment and local-run entry points in bin/super_linter.py."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

from git_fixtures import git
import pytest

SCRIPT_PATH = 'bin/super_linter.py'

CHECK_ONLY = [
    'VALIDATE_BASH=true',
    'VALIDATE_DOCKERFILE_HADOLINT=true',
    'VALIDATE_GITHUB_ACTIONS=true',
    'VALIDATE_GITLEAKS=true',
]


def run_super_linter(
    plugin_root: Path, cwd: Path, *arguments: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the entry point with only the standard library."""
    return subprocess.run(
        [sys.executable, '-S', str(plugin_root / SCRIPT_PATH), *arguments],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, **(env or {})},
    )


def expected_env(autofix: str, check_only: bool) -> list[str]:
    """Return the lines the reformat workflow appends to GITHUB_ENV for one pass."""
    return [
        'LINTER_RULES_PATH=.',
        'GITHUB_ACTIONS_CONFIG_FILE=.github/actionlint.yml',
        'FILTER_REGEX_EXCLUDE=(^|/)(\\.venv|\\.tmp|node_modules|\\.git)/',
        *(CHECK_ONLY if check_only else []),
        'VALIDATE_MARKDOWN_PRETTIER=true',
        'VALIDATE_YAML_PRETTIER=true',
        'VALIDATE_JSON_PRETTIER=true',
        'VALIDATE_JSONC_PRETTIER=true',
        'VALIDATE_GITHUB_ACTIONS_ZIZMOR=true',
        'VALIDATE_CLANG_FORMAT=true',
        'VALIDATE_ANSIBLE=true',
        'ANSIBLE_DIRECTORY=ansible',
        'VALIDATE_PYTHON_RUFF=true',
        'VALIDATE_PYTHON_RUFF_FORMAT=true',
        f'FIX_MARKDOWN_PRETTIER={autofix}',
        f'FIX_YAML_PRETTIER={autofix}',
        f'FIX_JSON_PRETTIER={autofix}',
        f'FIX_JSONC_PRETTIER={autofix}',
        f'FIX_GITHUB_ACTIONS_ZIZMOR={autofix}',
        f'FIX_CLANG_FORMAT={autofix}',
        f'FIX_ANSIBLE={autofix}',
        f'FIX_PYTHON_RUFF={autofix}',
        f'FIX_PYTHON_RUFF_FORMAT={autofix}',
        'SAVE_SUPER_LINTER_SUMMARY=true',
    ]


@pytest.mark.parametrize(
    ('arguments', 'env', 'autofix', 'check_only'),
    [
        ([], {}, 'false', True),
        (['--autofix'], {}, 'true', False),
        (['--autofix', '--enable_all_checks'], {}, 'true', True),
        ([], {'SUPER_LINTER_AUTOFIX': 'true'}, 'true', False),
    ],
)
def test_env_prints_the_pass_settings(
    plugin_root: Path,
    plugin_tmp_path: Path,
    arguments: list[str],
    env: dict[str, str],
    autofix: str,
    check_only: bool,
) -> None:
    """The check pass enables the check-only linters; the autofix pass turns fixes on."""
    completed = run_super_linter(plugin_root, plugin_tmp_path, 'env', *arguments, env=env)

    assert completed.returncode == 0
    assert completed.stdout.splitlines() == expected_env(autofix, check_only)


def test_env_rejects_an_unknown_argument(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """An unknown option must exit 2 with usage on stderr and nothing on stdout."""
    completed = run_super_linter(plugin_root, plugin_tmp_path, 'env', '--bogus')

    assert (completed.returncode, completed.stdout) == (2, '')
    assert completed.stderr.startswith('Unknown argument: --bogus\nUsage:')


@pytest.fixture
def docker_stub(plugin_tmp_path: Path) -> Path:
    """Put a fake docker that records its arguments ahead of git on PATH."""
    stubs = plugin_tmp_path / 'stubs'
    stubs.mkdir()
    docker = stubs / 'docker'
    docker.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{stubs}/docker-args"\n')
    docker.chmod(0o755)
    git_path = shutil.which('git')
    assert git_path is not None
    (stubs / 'git').symlink_to(git_path)
    return stubs


def test_local_runs_one_pass_with_every_check_and_autofix(
    plugin_root: Path, unrelated_repository: Path, docker_stub: Path
) -> None:
    """The local run mounts the repository and passes the combined pass's env file."""
    git(unrelated_repository, 'add', 'README.md')
    git(unrelated_repository, 'commit', '--quiet', '-m', 'Initial commit')

    completed = run_super_linter(
        plugin_root,
        unrelated_repository,
        'local',
        '--all',
        '--image',
        'example.invalid/linter:v1',
        env={'PATH': str(docker_stub)},
    )

    root = unrelated_repository.resolve()
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == f'Super-Linter output saved to {root}/log/super-linter-summary.md\n'
    assert (docker_stub / 'docker-args').read_text().splitlines() == [
        'run', '--rm',
        '-e', 'RUN_LOCAL=true',
        '-e', 'DEFAULT_BRANCH=main',
        '-e', 'VALIDATE_ALL_CODEBASE=true',
        '-e', 'LOG_LEVEL=INFO',
        '-e', 'SAVE_SUPER_LINTER_OUTPUT=true',
        '-e', 'SUPER_LINTER_OUTPUT_DIRECTORY_NAME=log',
        '--env-file', f'{root}/.tmp/super-linter.env',
        '-v', f'{root}:/tmp/lint',
        '--platform', 'linux/amd64',
        'example.invalid/linter:v1',
    ]  # fmt: skip
    env_file = (root / '.tmp' / 'super-linter.env').read_text().splitlines()
    assert env_file == expected_env('true', True)


def test_local_without_a_container_runtime_fails(
    plugin_root: Path, unrelated_repository: Path, plugin_tmp_path: Path
) -> None:
    """Without docker or podman the local run must exit 1 and say what is missing."""
    empty = plugin_tmp_path / 'empty'
    empty.mkdir()

    completed = run_super_linter(
        plugin_root, unrelated_repository, 'local', env={'PATH': str(empty)}
    )

    assert completed.returncode == 1
    assert completed.stderr == 'Docker or Podman is required to run Super-Linter locally.\n'


def test_local_option_without_a_value_is_a_usage_error(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """--image with no value must exit 2 before looking for a runtime."""
    completed = run_super_linter(plugin_root, plugin_tmp_path, 'local', '--image')

    assert (completed.returncode, completed.stderr) == (2, '--image requires a value.\n')
