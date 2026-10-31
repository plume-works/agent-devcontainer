#!/usr/bin/env python3

"""Validate that pre-commit and local tool versions match the pinned Super-Linter image."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT_DIR / '.agents' / 'plugins' / 'agentdev' / 'bin'))

from super_linter import SUPER_LINTER_DEFAULT_IMAGE  # noqa: E402  (path set above)

PRE_COMMIT_CONFIG = ROOT_DIR / '.pre-commit-config.yaml'
DEV_TOOLS_DEFAULTS = ROOT_DIR / 'ansible' / 'roles' / 'dev_tools' / 'defaults' / 'main.yml'
REFORMAT_WORKFLOW = ROOT_DIR / '.github' / 'workflows' / 'reformat.yml'

USAGE = """\
Usage: scripts/validate-super-linter-tool-versions.py [--image IMAGE]

Validates that the versions used by pre-commit and local hooks match the
versions installed in the pinned Super-Linter image. Super-Linter is the
source of truth.

Options:
  --image IMAGE  Override the Super-Linter image to inspect.
  -h, --help     Show this help.

Environment:
  SUPER_LINTER_IMAGE  Override the Super-Linter image to inspect.
"""

TOOLS = (
    'prettier',
    'clang-format',
    'ansible-lint',
    'hadolint',
    'ruff',
    'shellcheck',
    'gitleaks',
    'actionlint',
    'zizmor',
)

PRE_COMMIT_REPOSITORIES = {
    'clang-format': 'https://github.com/pre-commit/mirrors-clang-format',
    'ansible-lint': 'https://github.com/ansible/ansible-lint',
    'hadolint': 'https://github.com/hadolint/hadolint',
    'ruff': 'https://github.com/astral-sh/ruff-pre-commit',
    'shellcheck': 'https://github.com/shellcheck-py/shellcheck-py',
}
PINNED_TOOLS = ('gitleaks', 'actionlint', 'zizmor')

PROBE = r"""
set -euo pipefail
printf "prettier=%s\n" "$(prettier --version)"
printf "clang-format=%s\n" "$(clang-format --version | sed -nE "s/.*version ([0-9.]+).*/\\1/p")"
printf "ansible-lint=%s\n" "$(ansible-lint --version | awk "NR == 1 { print \$2 }")"
printf "hadolint=%s\n" "$(hadolint --version | awk "NR == 1 { print \$NF }")"
printf "ruff=%s\n" "$(ruff --version | awk "NR == 1 { print \$2 }")"
printf "shellcheck=%s\n" "$(shellcheck --version | sed -nE "s/^version: ([0-9.]+).*/\\1/p")"
printf "gitleaks=%s\n" "$(gitleaks version | awk "NR == 1 { print \$1 }")"
printf "actionlint=%s\n" "$(actionlint --version | head -n 1)"
printf "zizmor=%s\n" "$(zizmor --version | awk "NR == 1 { print \$2 }")"
"""


def first_match(pattern: str, text: str) -> str:
    """Return group 1 of the first line `pattern` matches in full, or ''."""
    for line in text.splitlines():
        if match := re.fullmatch(pattern, line):
            return match.group(1)
    return ''


def pre_commit_rev(config: str, repository: str) -> str:
    """Return the rev pinned for `repository` in the pre-commit config, or ''."""
    found = False
    for line in config.splitlines():
        if line.startswith('  - repo: '):
            if found:
                return ''
            fields = line.split()
            found = len(fields) > 2 and fields[2] == repository
            continue
        if found and line.startswith('    rev: '):
            fields = line.split()
            return fields[1] if len(fields) > 1 else ''
    return ''


def pinned_tool_version(defaults: str, tool: str) -> str:
    """Return the version of the dev_tools entry named `tool`, or ''."""
    found = False
    for line in defaults.splitlines():
        found = found or f'- name: {tool}' in line
        if found and 'version:' in line:
            return re.sub(r'.*version: ', '', line)
    return ''


def normalize_configured_version(tool: str, version: str) -> str:
    """Drop a leading v and, for the ShellCheck wrapper, its fourth version component."""
    version = version.removeprefix('v')
    if tool == 'shellcheck' and '.' in version:
        version = version.rsplit('.', 1)[0]
    return version


def check_version(tool: str, configured: str, super_linter: str, label: str = '') -> bool:
    """Print OK or the mismatch for one tool; an empty side is a failure unless labelled."""
    configured = normalize_configured_version(tool, configured)
    super_linter = super_linter.removeprefix('v')
    if not label and (not configured or not super_linter):
        print(f'Could not determine the {tool} version.', file=sys.stderr)
        return False
    name = label or tool
    if configured != super_linter:
        print(
            f'Version mismatch for {name}: configured {configured}, Super-Linter {super_linter}',
            file=sys.stderr,
        )
        return False
    print(f'OK {name:<14} {super_linter}')
    return True


def workflow_super_linter_tags(workflow: str) -> list[str]:
    """Return the Super-Linter tag each reformat workflow action reference names."""
    tags = []
    for line in workflow.splitlines():
        if match := re.fullmatch(r'.*super-linter/super-linter/slim@(v[0-9.]+).*', line):
            tags.append(f'slim-{match.group(1)}')
        elif match := re.fullmatch(r'.*super-linter/super-linter@(v[0-9.]+).*', line):
            tags.append(match.group(1))
    return tags


def main(arguments: list[str]) -> int:
    """Compare every configured tool version with the one in the Super-Linter image."""
    image = os.environ.get('SUPER_LINTER_IMAGE') or SUPER_LINTER_DEFAULT_IMAGE
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument == '--image':
            if not remaining:
                print('--image requires a value.', file=sys.stderr)
                return 2
            image = remaining.pop(0)
        elif argument in ('-h', '--help'):
            print(USAGE, end='')
            return 0
        else:
            print(f'Unknown argument: {argument}', file=sys.stderr)
            print(USAGE, end='', file=sys.stderr)
            return 2

    runtime = shutil.which('docker') and 'docker' or shutil.which('podman') and 'podman'
    if not runtime:
        print('Docker or Podman is required to inspect Super-Linter.', file=sys.stderr)
        return 1

    probe = subprocess.run(
        [runtime, 'run', '--rm', '--entrypoint', '/bin/bash', image, '-c', PROBE],
        check=False,
        stdout=subprocess.PIPE,
        text=True,
    )
    if probe.returncode != 0:
        return probe.returncode
    super_linter_versions = dict(
        (line.split('=', 1) + [''])[:2] for line in probe.stdout.splitlines()
    )

    pre_commit = PRE_COMMIT_CONFIG.read_text()
    defaults = DEV_TOOLS_DEFAULTS.read_text()
    configured_versions = {
        'prettier': first_match(r'.*prettier@v?([0-9.]+).*', pre_commit),
        **{
            tool: pre_commit_rev(pre_commit, repo)
            for tool, repo in PRE_COMMIT_REPOSITORIES.items()
        },
        **{tool: pinned_tool_version(defaults, tool) for tool in PINNED_TOOLS},
    }

    validation_failed = False
    for tool in TOOLS:
        if not check_version(tool, configured_versions[tool], super_linter_versions.get(tool, '')):
            validation_failed = True

    hadolint_entry = first_match(r'.*ghcr\.io/hadolint/hadolint:v?([0-9.]+).*', pre_commit)
    if not check_version(
        'hadolint', hadolint_entry, super_linter_versions.get('hadolint', ''), 'hadolint entry'
    ):
        validation_failed = True

    super_linter_tag = image.rsplit(':', 1)[-1]
    tags = workflow_super_linter_tags(REFORMAT_WORKFLOW.read_text())
    if not tags:
        print(
            'Could not find a recognized Super-Linter version tag in the workflow.',
            file=sys.stderr,
        )
        validation_failed = True
    for configured_tag in tags:
        if configured_tag != super_linter_tag:
            print(
                f'Version mismatch for Super-Linter: local image {super_linter_tag}, '
                f'workflow {configured_tag}',
                file=sys.stderr,
            )
            validation_failed = True

    if validation_failed:
        return 1
    print(f'All pre-commit and local tool versions match {image}.')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
