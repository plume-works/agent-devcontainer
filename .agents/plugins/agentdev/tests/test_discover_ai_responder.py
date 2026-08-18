#!/usr/bin/env python3

"""Behavior tests for the pr-discover-ai-responder skill script."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess

SCRIPT_PATH = 'skills/pr-discover-ai-responder/scripts/discover-ai-responder.sh'


def install_gh_stub(path: Path, workflows: list[dict[str, str]]) -> Path:
    """
    Create a stub `gh` that answers `workflow list` from fixed workflow data.

    The stub applies the `--jq` filter with the real `gh` absent, so it
    implements the one filter shape the script sends: select on a
    case-insensitive name match, emit the path.
    """
    stub_directory = path / 'stub-bin'
    stub_directory.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(workflows)
    stub = stub_directory / 'gh'
    stub.write_text(
        '#!/usr/bin/env python3\n'
        'import json, re, sys\n'
        f'workflows = json.loads({payload!r})\n'
        'arguments = sys.argv[1:]\n'
        'if arguments[:2] != ["workflow", "list"]:\n'
        '    sys.exit(1)\n'
        'expression = arguments[arguments.index("--jq") + 1]\n'
        'pattern = re.search(r\'test\\("(.+?)"\', expression).group(1)\n'
        'for workflow in workflows:\n'
        '    if re.search(pattern, workflow["name"], re.IGNORECASE):\n'
        '        print(workflow["path"])\n'
    )
    stub.chmod(0o755)
    return stub_directory


def run_script(
    plugin_root: Path,
    stub_directory: Path | None,
    *arguments: str,
) -> subprocess.CompletedProcess[str]:
    """Run the discovery script with `PATH` limited to the supplied stubs."""
    environment = dict(os.environ)
    base_path = '/usr/bin:/bin'
    environment['PATH'] = f'{stub_directory}:{base_path}' if stub_directory else base_path
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
    # Act
    completed = run_script(plugin_root, None)

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        5,
        'RESULT=GH_UNAVAILABLE',
    )


def test_workflow_override_skips_discovery(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """An explicit filename must be emitted without consulting the GitHub CLI."""
    # Act
    completed = run_script(
        plugin_root,
        None,
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
    # Act
    completed = run_script(plugin_root, None, '--not-a-flag')

    # Assert
    assert (completed.returncode, completed.stdout.splitlines()[-1]) == (
        2,
        'RESULT=PREFLIGHT_ERROR',
    )
