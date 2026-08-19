#!/usr/bin/env python3

"""Behavior tests for the pr-discover-ai-responder skill script."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

SCRIPT_PATH = 'skills/pr-discover-ai-responder/scripts/discover-ai-responder.sh'


def install_runtime_commands(path: Path) -> Path:
    """Create a hermetic PATH containing only the script's runtime commands."""
    stub_directory = path / 'stub-bin'
    stub_directory.mkdir(parents=True, exist_ok=True)
    for command in ('bash', 'basename', 'cat', 'dirname', 'sort'):
        executable = shutil.which(command)
        assert executable is not None
        (stub_directory / command).symlink_to(executable)
    return stub_directory


def install_gh_stub(path: Path, workflows: list[dict[str, str]]) -> Path:
    """
    Create a stub `gh` that answers `workflow list` from fixed workflow data.

    The stub applies the `--jq` filter with the real `gh` absent, so it
    implements the one filter shape the script sends: select on a
    case-insensitive name match, emit the path.
    """
    stub_directory = install_runtime_commands(path)
    payload = json.dumps(workflows)
    stub = stub_directory / 'gh'
    stub.write_text(
        f'#!{sys.executable}\n'
        'import json, os, re, sys\n'
        f'workflows = json.loads({payload!r})\n'
        'arguments = sys.argv[1:]\n'
        'if arguments[:2] != ["workflow", "list"]:\n'
        '    sys.exit(1)\n'
        'expression = arguments[arguments.index("--jq") + 1]\n'
        'if "--arg" in arguments:\n'
        '    arg_index = arguments.index("--arg")\n'
        '    pattern = arguments[arg_index + 2]\n'
        'elif "env.NAME_PATTERN" in expression:\n'
        '    pattern = os.environ["NAME_PATTERN"]\n'
        'else:\n'
        '    literal = re.search(r\'test\\(("(?:\\\\.|[^"\\\\])*")\', expression)\n'
        '    pattern = json.loads(literal.group(1))\n'
        'try:\n'
        '    re.search(pattern, "", re.IGNORECASE)\n'
        'except re.error:\n'
        '    if \'try ("" | test($pattern; "i"))\' not in expression:\n'
        '        raise\n'
        '    print("__AGENTDEV_INVALID_RESPONDER_NAME_PATTERN__")\n'
        '    sys.exit(0)\n'
        'for workflow in workflows:\n'
        '    if re.search(pattern, workflow["name"], re.IGNORECASE):\n'
        '        print(workflow["path"])\n'
    )
    stub.chmod(0o755)
    return stub_directory


def install_failing_gh_stub(path: Path) -> Path:
    """Create a `gh` stub that simulates an API or tool invocation failure."""
    stub_directory = install_runtime_commands(path)
    stub = stub_directory / 'gh'
    stub.write_text(
        f'#!{sys.executable}\n'
        'import sys\n'
        'print("simulated gh failure", file=sys.stderr)\n'
        'sys.exit(1)\n'
    )
    stub.chmod(0o755)
    return stub_directory


def run_script(
    plugin_root: Path,
    stub_directory: Path,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    """Run the discovery script with `PATH` limited to the supplied stubs."""
    environment = dict(os.environ)
    environment['PATH'] = str(stub_directory)
    return subprocess.run(
        [str(plugin_root / SCRIPT_PATH), *arguments],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )


def test_single_matching_workflow_reports_success(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """Exactly one matching workflow must resolve to its filename."""
    # Arrange
    stub_directory = install_gh_stub(
        plugin_tmp_path,
        [
            {'name': 'AI Responder', 'path': '.github/workflows/ai-responder.yml'},
            {'name': 'CI', 'path': '.github/workflows/ci.yml'},
        ],
    )

    # Act
    completed = run_script(plugin_root, stub_directory)

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        0,
        'RESULT=SUCCESS',
    )
    assert 'RESPONDER_WORKFLOW=ai-responder.yml' in completed.stdout


def test_no_matching_workflow_reports_declared_result(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A repository without a responder workflow must say so distinctly."""
    # Arrange
    stub_directory = install_gh_stub(
        plugin_tmp_path,
        [{'name': 'CI', 'path': '.github/workflows/ci.yml'}],
    )

    # Act
    completed = run_script(plugin_root, stub_directory)

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        3,
        'RESULT=NO_RESPONDER_WORKFLOW',
    )


def test_several_matching_workflows_refuse_to_guess(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """Ambiguity must be reported with candidates rather than silently resolved."""
    # Arrange
    stub_directory = install_gh_stub(
        plugin_tmp_path,
        [
            {'name': 'AI Responder', 'path': '.github/workflows/ai-responder.yml'},
            {'name': 'Claude Review', 'path': '.github/workflows/claude-review.yml'},
        ],
    )

    # Act
    completed = run_script(plugin_root, stub_directory)

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        4,
        'RESULT=AMBIGUOUS_WORKFLOW',
    )
    assert 'ai-responder.yml' in completed.stderr
    assert 'claude-review.yml' in completed.stderr


def test_missing_gh_reports_declared_result(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """An absent GitHub CLI must be distinguishable from an absent workflow."""
    # Arrange
    stub_directory = install_runtime_commands(plugin_tmp_path)

    # Act
    completed = run_script(plugin_root, stub_directory)

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        5,
        'RESULT=GH_UNAVAILABLE',
    )


def test_gh_failure_reports_unavailable_result(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A failed GitHub CLI call must remain eligible for the documented fallback."""
    # Arrange
    stub_directory = install_failing_gh_stub(plugin_tmp_path)

    # Act
    completed = run_script(plugin_root, stub_directory)

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        5,
        'RESULT=GH_UNAVAILABLE',
    )
    assert 'simulated gh failure' in completed.stderr


def test_workflow_override_skips_discovery(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """An explicit filename must be emitted without consulting the GitHub CLI."""
    # Arrange
    stub_directory = install_runtime_commands(plugin_tmp_path)

    # Act
    completed = run_script(
        plugin_root,
        stub_directory,
        '--workflow',
        '.github/workflows/known-responder.yml',
    )

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        0,
        'RESULT=SUCCESS',
    )
    assert 'RESPONDER_WORKFLOW=known-responder.yml' in completed.stdout


def test_unknown_argument_reports_preflight_error(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """A usage error must use the shared preflight result."""
    # Arrange
    stub_directory = install_runtime_commands(plugin_tmp_path)

    # Act
    completed = run_script(plugin_root, stub_directory, '--not-a-flag')

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        2,
        'RESULT=PREFLIGHT_ERROR',
    )


@pytest.mark.parametrize(
    ('pattern', 'workflows', 'expected_workflow'),
    [
        pytest.param(
            r'ai\-responder',
            [
                {'name': 'AI-Responder', 'path': '.github/workflows/ai-responder.yml'},
                {'name': 'CI', 'path': '.github/workflows/ci.yml'},
            ],
            'ai-responder.yml',
            id='escaped-hyphen',
        ),
        pytest.param(
            r'claude\b',
            [
                {'name': 'Claude Review', 'path': '.github/workflows/claude-review.yml'},
                {
                    'name': 'ClaudeCode Review',
                    'path': '.github/workflows/claude-code-review.yml',
                },
            ],
            'claude-review.yml',
            id='word-boundary',
        ),
    ],
)
def test_pattern_is_passed_as_regex_data(
    plugin_root: Path,
    plugin_tmp_path: Path,
    pattern: str,
    workflows: list[dict[str, str]],
    expected_workflow: str,
) -> None:
    """Regex escapes in a user pattern must reach the matcher unchanged."""
    # Arrange
    stub_directory = install_gh_stub(plugin_tmp_path, workflows)

    # Act
    completed = run_script(plugin_root, stub_directory, '--pattern', pattern)

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        0,
        'RESULT=SUCCESS',
    )
    assert f'RESPONDER_WORKFLOW={expected_workflow}' in completed.stdout


def test_invalid_pattern_reports_one_final_preflight_result(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """An invalid caller regex must be a preflight error, not a GitHub failure."""
    # Arrange
    stub_directory = install_gh_stub(
        plugin_tmp_path,
        [{'name': 'AI Responder', 'path': '.github/workflows/ai-responder.yml'}],
    )

    # Act
    completed = run_script(plugin_root, stub_directory, '--pattern', '[')

    # Assert
    result_lines = [line for line in completed.stdout.splitlines() if line.startswith('RESULT=')]
    assert (completed.returncode, result_lines) == (2, ['RESULT=PREFLIGHT_ERROR'])
    assert completed.stdout.splitlines()[-1] == 'RESULT=PREFLIGHT_ERROR'
    assert 'Invalid workflow name pattern: [' in completed.stderr
