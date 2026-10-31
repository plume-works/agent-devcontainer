"""Tests for `agentdev-runtime coder start`: each step warns on failure, then Remote Control."""

import os
from pathlib import Path
import subprocess
import sys

CODER_START = [sys.executable, '-m', 'agentdev_runtime', 'coder', 'start']
IMAGE_PRUNE = 'agentdev-runtime docker prune'
HELPER_SETUP = 'setup-gh-credential-helper.sh'
OPENCODE_WEB = 'agentdev-runtime opencode coder-start'
REMOTE_CONTROL = 'agentdev-runtime remote-control start'


def run_agent_start(
    tmp_path: Path,
    *,
    prune_exit: int = 0,
    helper_exit: int = 0,
    opencode_exit: int = 0,
    env: dict[str, str] | None = None,
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    """Run the start with a fake CLI on PATH and fake scripts in the runtime root."""
    root = tmp_path / 'runtime'
    bin_dir = tmp_path / 'bin'
    root.mkdir()
    bin_dir.mkdir()
    log = tmp_path / 'calls.log'
    fakes = {
        bin_dir / 'agentdev-runtime': f'echo "agentdev-runtime $* '
        f'password=${{OPENCODE_SERVER_PASSWORD:-}}" >> "{log}"\n'
        f'case "$1" in docker) exit {prune_exit} ;; opencode) exit {opencode_exit} ;; esac\n',
        root / HELPER_SETUP: f'echo "{HELPER_SETUP} token=${{GITHUB_TOKEN:-}}" >> "{log}"\n'
        f'exit {helper_exit}\n',
    }
    for fake, body in fakes.items():
        fake.write_text('#!/usr/bin/env bash\n' + body)
        fake.chmod(0o755)
    result = subprocess.run(
        CODER_START,
        env={
            'PATH': f'{bin_dir}:{os.environ["PATH"]}',
            'AGENTDEV_RUNTIME_ROOT': str(root),
            **(env or {}),
        },
        text=True,
        capture_output=True,
    )
    calls = log.read_text().splitlines() if log.exists() else []
    return result, calls


def first_words(calls: list[str]) -> list[str]:
    """Name each call by its command, without the environment it logged."""
    return [call.split(' password=')[0].split(' token=')[0] for call in calls]


def test_prune_helper_and_opencode_run_before_remote_control(tmp_path):
    result, calls = run_agent_start(tmp_path)
    assert result.returncode == 0, result.stderr
    assert first_words(calls) == [
        IMAGE_PRUNE,
        HELPER_SETUP,
        OPENCODE_WEB,
        REMOTE_CONTROL,
    ]


def test_remote_control_starts_when_prune_fails(tmp_path):
    result, calls = run_agent_start(tmp_path, prune_exit=3)
    assert result.returncode == 0, result.stderr
    assert first_words(calls) == [
        IMAGE_PRUNE,
        HELPER_SETUP,
        OPENCODE_WEB,
        REMOTE_CONTROL,
    ]
    assert result.stderr.strip()


def test_remote_control_starts_when_helper_setup_fails(tmp_path):
    result, calls = run_agent_start(tmp_path, helper_exit=3)
    assert result.returncode == 0, result.stderr
    assert first_words(calls)[-1] == REMOTE_CONTROL
    assert result.stderr.strip()


def test_helper_setup_sees_caller_environment(tmp_path):
    result, calls = run_agent_start(tmp_path, env={'GITHUB_TOKEN': 'from-coder-secret'})
    assert result.returncode == 0, result.stderr
    assert calls[1] == f'{HELPER_SETUP} token=from-coder-secret'


def test_remote_control_starts_when_opencode_web_fails(tmp_path):
    result, calls = run_agent_start(tmp_path, opencode_exit=3)
    assert result.returncode == 0, result.stderr
    assert first_words(calls)[-1] == REMOTE_CONTROL
    assert result.stderr.strip()


def test_opencode_web_sees_caller_environment(tmp_path):
    result, calls = run_agent_start(
        tmp_path, env={'OPENCODE_SERVER_PASSWORD': 'from-coder-secret'}
    )
    assert result.returncode == 0, result.stderr
    assert calls[2] == f'{OPENCODE_WEB} password=from-coder-secret'
