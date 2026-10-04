#!/usr/bin/env python3

"""Behavior tests for the remote Codespace session scripts."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess


def test_codespace_exec_separates_metadata_from_unterminated_remote_stdout(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """Remote output without a newline must not absorb the exit-code key."""
    # Arrange
    script = plugin_root / 'skills/remote-codespace-session/agent-code/codespace-exec.sh'
    mock_bin = plugin_tmp_path / 'bin'
    mock_bin.mkdir()
    mock_repository = plugin_tmp_path / 'repository'
    (mock_repository / '.tmp').mkdir(parents=True)
    (mock_repository / '.tmp' / 'codespace-name').write_text('fixture-codespace\n')

    mock_git = mock_bin / 'git'
    mock_git.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "${MOCK_REPOSITORY_ROOT}"
"""
    )
    mock_git.chmod(0o755)

    mock_gh = mock_bin / 'gh'
    mock_gh.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
case "${1:-} ${2:-}" in
  'codespace list')
    ;;
  'repo view')
    printf '%s\n' 'fixture-repository'
    ;;
  'codespace ssh')
    printf 'foo'
    ;;
  *)
    exit 64
    ;;
esac
"""
    )
    mock_gh.chmod(0o755)

    environment = os.environ.copy()
    environment['MOCK_REPOSITORY_ROOT'] = str(mock_repository)
    environment['PATH'] = f'{mock_bin}:{environment["PATH"]}'

    # Act
    completed = subprocess.run(
        [str(script), 'printf', 'foo'],
        cwd=plugin_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    # Assert
    assert completed.returncode == 0
    assert completed.stdout == 'foo\nREMOTE_EXIT_CODE=0\nRESULT=SUCCESS\n'
