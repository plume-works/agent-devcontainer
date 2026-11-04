"""Tests for .claude/startup.py, the Claude Code cloud session startup and resume script."""

from collections.abc import Iterator
import importlib.util
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import time
from types import ModuleType
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

REPO_ROOT = Path(__file__).parents[2]
STARTUP = REPO_ROOT / '.claude/startup.py'
STUBBED = ('docker', 'dockerd', 'devcontainer', 'bun', 'claude')


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


def free_port() -> int:
    """Return a TCP port nothing listens on right now."""
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def run_resume(scratch: Path, **env: str) -> tuple[subprocess.CompletedProcess[str], Path]:
    """Run `startup.py resume` with stubs that record every call, and return the call log."""
    bin_dir = scratch / 'bin'
    bin_dir.mkdir()
    calls = scratch / 'calls'
    for name in STUBBED:
        stub = bin_dir / name
        stub.write_text(f'#!/bin/sh\necho {name} "$@" >> {calls}\nexit 1\n')
        stub.chmod(0o755)
    result = subprocess.run(
        [sys.executable, str(STARTUP), 'resume'],
        env={
            'PATH': f'{bin_dir}:/usr/bin:/bin',
            'HOME': str(scratch),
            'AGENTDEV_STARTUP_LOG_DIR': str(scratch),
            **env,
        },
        capture_output=True,
        text=True,
        check=False,
    )
    return result, calls


@pytest.mark.parametrize(
    'env',
    [
        {},
        {'CLAUDE_CODE_REMOTE': 'false'},
        {'CLAUDE_CODE_REMOTE': 'true', 'AGENTDEV_RUNTIME_MODE': 'devcontainer'},
    ],
    ids=['local-host', 'remote-false', 'inside-devcontainer'],
)
def test_resume_does_nothing_off_a_cloud_host(scratch: Path, env: dict[str, str]) -> None:
    """Resume exits cleanly without touching Docker anywhere but a cloud-session host."""
    result, calls = run_resume(scratch, **env)
    assert (result.returncode, result.stdout) == (0, '')
    assert not calls.exists()


def test_resume_on_a_cloud_host_starts_docker(scratch: Path) -> None:
    """On a cloud-session host, resume starts dockerd and fails at once when it exits."""
    started = time.monotonic()
    result, calls = run_resume(scratch, CLAUDE_CODE_REMOTE='true')
    assert result.returncode == 1
    assert 'dockerd exited with 1' in result.stderr
    assert f'dockerd --bip {startup.DOCKER_BRIDGE_CIDR}' in calls.read_text().splitlines()
    assert time.monotonic() - started < startup.DOCKER_WAIT_SECONDS


def test_unknown_mode_is_a_usage_error() -> None:
    """Only setup and resume are modes."""
    result = subprocess.run(
        [sys.executable, str(STARTUP), 'restart'], capture_output=True, text=True, check=False
    )
    assert result.returncode == 2


@pytest.mark.parametrize(
    ('environ', 'port'),
    [
        ({'HTTPS_PROXY': 'http://127.0.0.1:44529'}, 44529),
        ({'https_proxy': 'http://127.0.0.1:8080/'}, 8080),
        ({'HTTPS_PROXY': 'http://proxy.corp:3128'}, None),
        ({}, None),
    ],
)
def test_proxy_port_needs_a_loopback_proxy(environ: dict[str, str], port: int | None) -> None:
    """Only a loopback HTTPS proxy is the session's agent proxy."""
    assert startup.proxy_port(environ) == port


def test_cloud_env_points_the_container_at_the_relay() -> None:
    """The env file names the relay, the session's no-proxy list, and its token."""
    text = startup.cloud_env_text({'NO_PROXY': 'localhost,pypi.org', 'GH_TOKEN': 'token'})
    relay = f'http://host.docker.internal:{startup.RELAY_PORT}'
    assert text.splitlines() == [
        f'HTTPS_PROXY={relay}',
        f'https_proxy={relay}',
        'NO_PROXY=localhost,pypi.org',
        'no_proxy=localhost,pypi.org',
        'GH_TOKEN=token',
    ]


def test_relay_liveness_follows_the_relay_process(
    scratch: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A recorded relay counts only while it runs and only for its own target port."""
    monkeypatch.setattr(startup, 'RELAY_PORT', free_port())
    pidfile = scratch / 'relay.pid'
    target = free_port()
    startup.start_relay('127.0.0.1', target, pidfile, scratch / 'relay.log')
    pid, recorded = startup.read_pidfile(pidfile)
    assert recorded == target
    assert startup.relay_running_for(target, pidfile)
    assert not startup.relay_running_for(target + 1, pidfile)
    assert not startup.relay_alive(os.getpid(), target)

    startup.stop_relay(pidfile)
    deadline = time.monotonic() + 5
    while startup.relay_alive(pid, target) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not startup.relay_alive(pid, target)
    assert not pidfile.exists()


def test_no_loopback_proxy_removes_stale_access(
    scratch: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the agent proxy, a leftover env file is removed so the container gets none."""
    cloud_env = scratch / 'cloud-session.env'
    cloud_env.write_text('HTTPS_PROXY=http://host.docker.internal:3128\n')
    monkeypatch.setattr(startup, 'CLOUD_ENV', cloud_env)
    monkeypatch.setattr(startup, 'RELAY_PIDFILE', scratch / 'relay.pid')
    startup.prepare_proxy_access({})
    assert not cloud_env.exists()
