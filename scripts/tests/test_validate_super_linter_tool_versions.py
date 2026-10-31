"""Tests for scripts/validate-super-linter-tool-versions.py against a stubbed container runtime."""

from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = 'scripts/validate-super-linter-tool-versions.py'
DEFAULTS_MODULE = '.agents/plugins/agentdev/bin/super_linter.py'

PRE_COMMIT = """\
repos:
  - repo: https://github.com/pre-commit/mirrors-clang-format
    rev: v21.1.2
  - repo: https://github.com/ansible/ansible-lint
    rev: v26.4.0
  - repo: https://github.com/hadolint/hadolint
    rev: v2.14.0
    hooks:
      - id: hadolint-docker
        entry: ghcr.io/hadolint/hadolint:v2.14.0 hadolint
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.17
  - repo: https://github.com/shellcheck-py/shellcheck-py
    rev: v0.11.0.1
  - repo: local
    hooks:
      - id: prettier
        entry: bunx prettier@3.8.4
"""

DEV_TOOLS = """\
dev_tools_pinned_tools:
  - name: gitleaks
    version: 8.30.1
  - name: actionlint
    version: 1.7.12
  - name: zizmor
    version: 1.25.2
"""

WORKFLOW = 'steps:\n  - uses: super-linter/super-linter/slim@v8.7.0 # pinned\n'

IMAGE_VERSIONS = {
    'prettier': '3.8.4',
    'clang-format': '21.1.2',
    'ansible-lint': '26.4.0',
    'hadolint': '2.14.0',
    'ruff': '0.15.17',
    'shellcheck': '0.11.0',
    'gitleaks': '8.30.1',
    'actionlint': '1.7.12',
    'zizmor': 'v1.25.2',
}


@pytest.fixture
def checkout() -> Iterator[Path]:
    """Lay out the script, the catalog's defaults module, and fixture configs."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'validate-super-linter-{uuid4().hex}'
    for relative in (SCRIPT, DEFAULTS_MODULE):
        (root / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO_ROOT / relative, root / relative)
    (root / '.pre-commit-config.yaml').write_text(PRE_COMMIT)
    (root / 'ansible/roles/dev_tools/defaults').mkdir(parents=True)
    (root / 'ansible/roles/dev_tools/defaults/main.yml').write_text(DEV_TOOLS)
    (root / '.github/workflows').mkdir(parents=True)
    (root / '.github/workflows/reformat.yml').write_text(WORKFLOW)
    try:
        yield root
    finally:
        shutil.rmtree(root)


def run_validator(
    checkout: Path, versions: dict[str, str], *arguments: str
) -> subprocess.CompletedProcess[str]:
    """Run the validator with a docker stub that reports `versions` and logs its image."""
    stubs = checkout / 'stubs'
    stubs.mkdir(exist_ok=True)
    report = ''.join(f'{tool}={version}\n' for tool, version in versions.items())
    docker = stubs / 'docker'
    docker.write_text(
        f'#!/bin/sh\nprintf "%s\\n" "$@" > "{stubs}/docker-args"\nprintf "%s" "{report}"\n'
    )
    docker.chmod(0o755)
    return subprocess.run(
        [sys.executable, '-S', str(checkout / SCRIPT), *arguments],
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, 'PATH': str(stubs)},
    )


def test_matching_versions_pass(checkout: Path) -> None:
    """Every tool matching the image prints an OK line and the closing summary."""
    completed = run_validator(checkout, IMAGE_VERSIONS)

    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.splitlines() == [
        'OK prettier       3.8.4',
        'OK clang-format   21.1.2',
        'OK ansible-lint   26.4.0',
        'OK hadolint       2.14.0',
        'OK ruff           0.15.17',
        'OK shellcheck     0.11.0',
        'OK gitleaks       8.30.1',
        'OK actionlint     1.7.12',
        'OK zizmor         1.25.2',
        'OK hadolint entry 2.14.0',
        'All pre-commit and local tool versions match '
        'ghcr.io/super-linter/super-linter:slim-v8.7.0.',
    ]
    assert 'ghcr.io/super-linter/super-linter:slim-v8.7.0' in (
        (checkout / 'stubs' / 'docker-args').read_text().splitlines()
    )


def test_a_version_mismatch_fails(checkout: Path) -> None:
    """A tool drifting from the image is named on stderr and fails the run."""
    completed = run_validator(checkout, {**IMAGE_VERSIONS, 'ruff': '0.0.1'})

    assert completed.returncode == 1
    assert completed.stderr == (
        'Version mismatch for ruff: configured 0.15.17, Super-Linter 0.0.1\n'
    )


def test_a_missing_tool_version_fails(checkout: Path) -> None:
    """A tool the image does not report cannot be compared and fails the run."""
    versions = {tool: version for tool, version in IMAGE_VERSIONS.items() if tool != 'gitleaks'}

    completed = run_validator(checkout, versions)

    assert completed.returncode == 1
    assert completed.stderr == 'Could not determine the gitleaks version.\n'


def test_an_image_other_than_the_workflow_pin_fails(checkout: Path) -> None:
    """An --image whose tag the workflow does not use is reported as drift."""
    completed = run_validator(
        checkout, IMAGE_VERSIONS, '--image', 'example.invalid/sl:slim-v9.0.0'
    )

    assert completed.returncode == 1
    assert completed.stderr == (
        'Version mismatch for Super-Linter: local image slim-v9.0.0, workflow slim-v8.7.0\n'
    )
