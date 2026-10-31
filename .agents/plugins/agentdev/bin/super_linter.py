#!/usr/bin/env python3

"""
Super-Linter defaults, the environment the reformat workflow passes it, and a local run.

  super_linter.py env [--autofix] [--enable_all_checks]   print the GITHUB_ENV lines
  super_linter.py local [--all] [--image IMAGE] [--log-level LEVEL]

This ships in the `agentdev` plugin, so the repository being worked on is
resolved from the working directory, never from this file's location. Standard
library only.
"""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

# Callers may override the image with SUPER_LINTER_IMAGE or their own --image.
SUPER_LINTER_DEFAULT_IMAGE = 'ghcr.io/super-linter/super-linter:slim-v8.7.0'

USAGE = """\
Usage:
  super_linter.py env [--autofix] [--enable_all_checks]
  super_linter.py local [--all] [--image IMAGE] [--log-level LEVEL]
"""

ENV_USAGE = """\
Usage: super_linter.py env [--autofix]

Generate env file for Super-Linter autofix pass and check pass

Options:
  --autofix            Run autofixes.
  --enable_all_checks  Enable all checks, including those that don't support autofix.
"""

LOCAL_USAGE = """\
Usage: super_linter.py local [--all] [--image IMAGE] [--log-level LEVEL]

Runs one local Super-Linter pass with all checks enabled and available
autofixes applied. CI keeps its autofix and check passes separate so it can
publish formatter patches without failing the validation job.

Options:
  --all              Set VALIDATE_ALL_CODEBASE=true.
  --image IMAGE      Override the Super-Linter container image.
  --log-level LEVEL  Override Super-Linter LOG_LEVEL.
  -h, --help         Show this help.

Environment:
  SUPER_LINTER_IMAGE     Container image to run.
  VALIDATE_ALL_CODEBASE  true or false. Defaults to false.
  LOG_LEVEL              Super-Linter log level. Defaults to INFO.
"""

# Linters without an autofix; only the check pass enables them.
CHECK_ONLY = (
    'VALIDATE_BASH',
    'VALIDATE_DOCKERFILE_HADOLINT',
    'VALIDATE_GITHUB_ACTIONS',
    'VALIDATE_GITLEAKS',
)
VALIDATE = (
    'VALIDATE_MARKDOWN_PRETTIER',
    'VALIDATE_YAML_PRETTIER',
    'VALIDATE_JSON_PRETTIER',
    'VALIDATE_JSONC_PRETTIER',
    'VALIDATE_GITHUB_ACTIONS_ZIZMOR',
    'VALIDATE_CLANG_FORMAT',
    'VALIDATE_ANSIBLE',
)
FIX = (
    'FIX_MARKDOWN_PRETTIER',
    'FIX_YAML_PRETTIER',
    'FIX_JSON_PRETTIER',
    'FIX_JSONC_PRETTIER',
    'FIX_GITHUB_ACTIONS_ZIZMOR',
    'FIX_CLANG_FORMAT',
    'FIX_ANSIBLE',
    'FIX_PYTHON_RUFF',
    'FIX_PYTHON_RUFF_FORMAT',
)


def env_lines(autofix: str, enable_all_checks: bool) -> list[str]:
    """Return the KEY=value lines for one pass; `autofix` is the literal true or false."""
    lines = [
        'LINTER_RULES_PATH=.',
        'GITHUB_ACTIONS_CONFIG_FILE=.github/actionlint.yml',
        'FILTER_REGEX_EXCLUDE=(^|/)(\\.venv|\\.tmp|node_modules|\\.git)/',
    ]
    if autofix == 'false' or enable_all_checks:
        lines += [f'{name}=true' for name in CHECK_ONLY]
    lines += [f'{name}=true' for name in VALIDATE]
    lines += [
        'ANSIBLE_DIRECTORY=ansible',
        'VALIDATE_PYTHON_RUFF=true',
        'VALIDATE_PYTHON_RUFF_FORMAT=true',
    ]
    lines += [f'{name}={autofix}' for name in FIX]
    lines.append('SAVE_SUPER_LINTER_SUMMARY=true')
    return lines


def env_command(arguments: list[str]) -> int:
    """Print the environment for the autofix or the check pass."""
    autofix = os.environ.get('SUPER_LINTER_AUTOFIX', 'false')
    enable_all_checks = False
    for argument in arguments:
        if argument == '--autofix':
            autofix = 'true'
        elif argument == '--enable_all_checks':
            enable_all_checks = True
        elif argument in ('-h', '--help'):
            print(ENV_USAGE, end='')
            return 0
        else:
            print(f'Unknown argument: {argument}', file=sys.stderr)
            print(ENV_USAGE, end='', file=sys.stderr)
            return 2
    print('\n'.join(env_lines(autofix, enable_all_checks)))
    return 0


def repository_root() -> Path:
    """Return the working directory's repository top level, or the directory itself."""
    try:
        completed = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'], check=False, capture_output=True, text=True
        )
    except OSError:
        return Path.cwd()
    return Path(completed.stdout.strip()) if completed.returncode == 0 else Path.cwd()


def _git_output(root: Path, *arguments: str) -> tuple[int, str]:
    completed = subprocess.run(
        ['git', '-C', str(root), *arguments], check=False, capture_output=True, text=True
    )
    return completed.returncode, completed.stdout.strip()


def local_command(arguments: list[str]) -> int:
    """Run one local Super-Linter pass with every check and available autofix."""
    image = os.environ.get('SUPER_LINTER_IMAGE') or SUPER_LINTER_DEFAULT_IMAGE
    validate_all_codebase = os.environ.get('VALIDATE_ALL_CODEBASE') or 'false'
    log_level = os.environ.get('LOG_LEVEL') or 'INFO'
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument == '--all':
            validate_all_codebase = 'true'
        elif argument in ('--image', '--log-level'):
            if not remaining:
                print(f'{argument} requires a value.', file=sys.stderr)
                return 2
            value = remaining.pop(0)
            if argument == '--image':
                image = value
            else:
                log_level = value
        elif argument in ('-h', '--help'):
            print(LOCAL_USAGE, end='')
            return 0
        else:
            print(f'Unknown argument: {argument}', file=sys.stderr)
            print(LOCAL_USAGE, end='', file=sys.stderr)
            return 2

    runtime = shutil.which('docker') and 'docker' or shutil.which('podman') and 'podman'
    if not runtime:
        print('Docker or Podman is required to run Super-Linter locally.', file=sys.stderr)
        return 1

    root = repository_root()
    (root / '.tmp').mkdir(parents=True, exist_ok=True)

    status, symref = _git_output(
        root, 'symbolic-ref', '--quiet', '--short', 'refs/remotes/origin/HEAD'
    )
    default_branch = (symref if status == 0 else '').removeprefix('origin/') or 'main'

    status, git_common_dir = _git_output(
        root, 'rev-parse', '--path-format=absolute', '--git-common-dir'
    )
    if status != 0:
        return status
    mounts = ['-v', f'{root}:/tmp/lint']
    if git_common_dir != f'{root}/.git':
        mounts += ['-v', f'{git_common_dir}:{git_common_dir}']

    env_file = root / '.tmp' / 'super-linter.env'
    env_file.write_text('\n'.join(env_lines('true', True)) + '\n')
    completed = subprocess.run(
        [
            runtime, 'run', '--rm',
            '-e', 'RUN_LOCAL=true',
            '-e', f'DEFAULT_BRANCH={default_branch}',
            '-e', f'VALIDATE_ALL_CODEBASE={validate_all_codebase}',
            '-e', f'LOG_LEVEL={log_level}',
            '-e', 'SAVE_SUPER_LINTER_OUTPUT=true',
            '-e', 'SUPER_LINTER_OUTPUT_DIRECTORY_NAME=log',
            '--env-file', str(env_file),
            *mounts,
            '--platform', 'linux/amd64',
            image,
        ],
        check=False,
    )  # fmt: skip
    if completed.returncode != 0:
        return completed.returncode

    print(f'Super-Linter output saved to {root}/log/super-linter-summary.md')
    return 0


def main(arguments: list[str]) -> int:
    """Dispatch to the env or local command."""
    if arguments and arguments[0] == 'env':
        return env_command(arguments[1:])
    if arguments and arguments[0] == 'local':
        return local_command(arguments[1:])
    if arguments in (['-h'], ['--help']):
        print(USAGE, end='')
        return 0
    print(USAGE, end='', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
