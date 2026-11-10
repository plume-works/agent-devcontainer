"""Tests for .claude/startup.py, the Claude Code cloud session setup script."""

from collections.abc import Iterator
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import ModuleType
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

REPO_ROOT = Path(__file__).parents[2]
STARTUP = REPO_ROOT / '.claude/startup.py'
STUBBED = ('claude', 'bash', 'ansible-playbook', 'uv')


def load_startup() -> ModuleType:
    """Import startup.py, which lives outside any package."""
    spec = importlib.util.spec_from_file_location('cloud_startup', STARTUP)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


startup = load_startup()


@pytest.fixture
def scratch() -> Iterator[Path]:
    """Yield a fresh scratch directory under real /tmp."""
    path = TMP_ROOT / f'cloud-startup-{uuid4().hex}'
    path.mkdir(parents=True)
    yield path
    shutil.rmtree(path)


def run_startup(
    scratch: Path, *args: str, failing: str = ''
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    """Run startup.py with stubs that log each call; the stub named by failing exits 1."""
    bin_dir = scratch / 'bin'
    bin_dir.mkdir()
    calls = scratch / 'calls'
    for name in STUBBED:
        stub = bin_dir / name
        stub.write_text(
            f'#!/bin/sh\necho {name} "$@" ANSIBLE_LOG_PATH="${{ANSIBLE_LOG_PATH-unset}}"'
            f' >> {calls}\nexit {1 if name == failing else 0}\n'
        )
        stub.chmod(0o755)
    result = subprocess.run(
        [sys.executable, str(STARTUP), *args],
        env={'PATH': f'{bin_dir}:/usr/bin:/bin', 'HOME': str(scratch)},
        capture_output=True,
        text=True,
        check=False,
    )
    lines = calls.read_text().splitlines() if calls.exists() else []
    return result, [line.removesuffix(' ANSIBLE_LOG_PATH=unset') for line in lines]


@pytest.mark.parametrize('args', [(), ('setup',)], ids=['default', 'explicit'])
def test_setup_provisions_the_host_then_installs_the_hooks(
    scratch: Path, args: tuple[str, ...]
) -> None:
    """Setup registers the plugin, provisions the toolchain, syncs, and installs every hook."""
    result, calls = run_startup(scratch, *args)
    assert result.returncode == 0, result.stderr
    hook_types = ' '.join(f'--hook-type {hook}' for hook in startup.HOOK_TYPES)
    assert calls == [
        'claude plugin marketplace add ./',
        'claude plugin install agentdev@agent-devcontainer',
        'bash docker/ansible/setup-ansible.sh',
        'ansible-playbook ansible/playbooks/setup-dev.yml --tags dev_tools,uv_setup'
        ' ANSIBLE_LOG_PATH=',
        'uv sync',
        f'uv run pre-commit install --install-hooks {hook_types}',
    ]


def test_setup_installs_the_cloud_instructions(scratch: Path) -> None:
    """The cloud-session instructions become the session's user-level CLAUDE.md."""
    result, _ = run_startup(scratch)
    assert result.returncode == 0, result.stderr
    installed = (scratch / '.claude/CLAUDE.md').read_text()
    assert installed == (REPO_ROOT / '.claude/CLAUDE.cloud.md').read_text()


def test_setup_adds_the_session_env_to_existing_user_settings(scratch: Path) -> None:
    """The user-level settings gain SESSION_ENV and keep everything they already held."""
    settings = scratch / '.claude/settings.json'
    settings.parent.mkdir()
    settings.write_text(json.dumps({'model': 'x', 'env': {'KEEP': '1'}}))
    result, _ = run_startup(scratch)
    assert result.returncode == 0, result.stderr
    assert json.loads(settings.read_text()) == {
        'model': 'x',
        'env': {'KEEP': '1', **startup.SESSION_ENV},
    }


def test_a_failing_step_fails_setup_and_stops_it(scratch: Path) -> None:
    """A failed provisioning step fails the script before the project is synced."""
    result, calls = run_startup(scratch, failing='ansible-playbook')
    assert result.returncode == 1
    assert 'startup: error:' in result.stderr
    assert not [line for line in calls if line.startswith('uv ')]


def test_resume_is_no_longer_a_mode(scratch: Path) -> None:
    """Nothing survives a host restart that needs restoring, so resume is a usage error."""
    result, calls = run_startup(scratch, 'resume')
    assert result.returncode == 2
    assert calls == []
