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

# Runs startup.py with its daemon pid files in scratch, never the host's /var/run.
ISOLATED = """
import importlib.util, sys
from pathlib import Path
spec = importlib.util.spec_from_file_location('cloud_startup', sys.argv[1])
startup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(startup)
scratch = Path(sys.argv[2])
startup.DAEMON_PIDFILES = {name: scratch / f'{name}.pid' for name in startup.DAEMON_PIDFILES}
raise SystemExit(startup.main(sys.argv[3:]))
"""


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


def run_startup(
    scratch: Path, mode: str, scripts: dict[str, str] | None = None, **env: str
) -> tuple[subprocess.CompletedProcess[str], Path]:
    """Run `startup.py <mode>` with stubs that log each call, then run their script or fail."""
    bin_dir = scratch / 'bin'
    bin_dir.mkdir()
    calls = scratch / 'calls'
    for name in STUBBED:
        stub = bin_dir / name
        body = (scripts or {}).get(name, 'exit 1')
        stub.write_text(f'#!/bin/sh\necho {name} "$@" >> {calls}\n{body}\n')
        stub.chmod(0o755)
    result = subprocess.run(
        [sys.executable, '-c', ISOLATED, str(STARTUP), str(scratch), mode],
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


def run_resume(scratch: Path, **env: str) -> tuple[subprocess.CompletedProcess[str], Path]:
    """Run `startup.py resume` with failing stubs."""
    return run_startup(scratch, 'resume', **env)


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


def test_output_of_a_missing_command_is_empty() -> None:
    """A command that is not installed reads as failed, so the caller can install it."""
    assert startup.output(f'missing-command-{uuid4().hex}', '--version') == ''


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
    """The env file names the relay, the no-proxy list, the token, and offline zizmor."""
    text = startup.cloud_env_text({'NO_PROXY': 'localhost,pypi.org', 'GH_TOKEN': 'token'})
    relay = f'http://host.docker.internal:{startup.RELAY_PORT}'
    assert text.splitlines() == [
        f'HTTPS_PROXY={relay}',
        f'https_proxy={relay}',
        'NO_PROXY=localhost,pypi.org',
        'no_proxy=localhost,pypi.org',
        'GH_TOKEN=token',
        'ZIZMOR_OFFLINE=true',
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


SESSION_ENV = 'HTTPS_PROXY=http://host.docker.internal:3128\nGH_TOKEN=token\n'


def stub_container(
    scratch: Path, monkeypatch: pytest.MonkeyPatch, container_env: list[str] | None
) -> tuple[dict[str, str], Path]:
    """Stub docker and devcontainer around one container, or none; return the env and call log."""
    bin_dir = scratch / 'bin'
    bin_dir.mkdir()
    calls = scratch / 'calls'
    listing = '' if container_env is None else 'echo c0ffee'
    env_lines = '\n'.join(container_env or [])
    (bin_dir / 'docker').write_text(
        f'#!/bin/sh\necho docker "$@" >> {calls}\n'
        f'case "$1" in ps) {listing} ;; inspect) printf "%s\\n" "{env_lines}" ;; esac\n'
    )
    (bin_dir / 'devcontainer').write_text(f'#!/bin/sh\necho devcontainer "$@" >> {calls}\n')
    for stub in bin_dir.iterdir():
        stub.chmod(0o755)
    cloud_env = scratch / 'cloud-session.env'
    cloud_env.write_text(SESSION_ENV)
    monkeypatch.setattr(startup, 'CLOUD_ENV', cloud_env)
    path = f'{bin_dir}:/usr/bin:/bin'
    monkeypatch.setenv('PATH', path)
    return {'PATH': path}, calls


def devcontainer_calls(calls: Path) -> list[str]:
    """Return the recorded devcontainer invocations."""
    if not calls.exists():
        return []
    return [line for line in calls.read_text().splitlines() if line.startswith('devcontainer')]


@pytest.mark.parametrize(
    'container_env',
    [
        ['HTTPS_PROXY=http://host.docker.internal:3128'],
        ['HTTPS_PROXY=http://host.docker.internal:3128', 'GH_TOKEN=old'],
    ],
    ids=['missing-key', 'different-value'],
)
def test_container_without_the_session_env_is_recreated(
    scratch: Path, monkeypatch: pytest.MonkeyPatch, container_env: list[str]
) -> None:
    """A container whose environment differs from cloud-session.env is recreated from it."""
    environ, calls = stub_container(scratch, monkeypatch, container_env)
    startup.sync_devcontainer(environ)
    assert devcontainer_calls(calls) == [
        f'devcontainer up --remove-existing-container --workspace-folder {startup.REPO_ROOT}'
    ]


def test_running_container_with_the_session_env_is_kept(
    scratch: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Resume leaves a running container alone when it already carries cloud-session.env."""
    environ, calls = stub_container(
        scratch, monkeypatch, ['PATH=/usr/bin', *SESSION_ENV.splitlines()]
    )
    startup.sync_devcontainer(environ)
    assert devcontainer_calls(calls) == []


def test_missing_container_is_brought_up(scratch: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Without a container, devcontainer up creates one, with no recreate flag."""
    environ, calls = stub_container(scratch, monkeypatch, None)
    startup.sync_devcontainer(environ)
    assert devcontainer_calls(calls) == [f'devcontainer up --workspace-folder {startup.REPO_ROOT}']


def test_no_session_env_never_recreates(scratch: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Without cloud-session.env there is nothing to compare, so the container is kept."""
    environ, calls = stub_container(scratch, monkeypatch, ['PATH=/usr/bin'])
    startup.CLOUD_ENV.unlink()
    startup.sync_devcontainer(environ)
    assert devcontainer_calls(calls) == []


def test_setup_builds_the_image_without_creating_the_container(scratch: Path) -> None:
    """Setup has no session proxy, so it builds the devcontainer image and creates nothing."""
    version = startup.DEVCONTAINER_CLI_VERSION
    result, calls = run_startup(
        scratch,
        'setup',
        {
            'docker': 'exit 0',
            'claude': 'exit 0',
            'devcontainer': f'[ "$1" = --version ] && echo {version}; exit 0',
        },
    )
    assert result.returncode == 0, result.stderr
    lines = calls.read_text().splitlines()
    assert f'devcontainer build --workspace-folder {startup.REPO_ROOT}' in lines
    assert not [line for line in lines if line.startswith(('devcontainer up', 'docker compose'))]


def test_setup_builds_without_the_bake_fs_entitlement_check(scratch: Path) -> None:
    """The featureless build passes only when bake skips its filesystem entitlement check."""
    version = startup.DEVCONTAINER_CLI_VERSION
    seen = scratch / 'entitlements'
    result, _ = run_startup(
        scratch,
        'setup',
        {
            'docker': 'exit 0',
            'claude': 'exit 0',
            'devcontainer': (
                f'[ "$1" = --version ] && echo {version}\n'
                f'[ "$1" = build ] && echo "$BUILDX_BAKE_ENTITLEMENTS_FS" > {seen}\nexit 0'
            ),
        },
    )
    assert result.returncode == 0, result.stderr
    assert seen.read_text().strip() == '0'


def stub_dockerd(scratch: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Stub a dockerd that refuses to start while a daemon pid file exists."""
    bin_dir = scratch / 'bin'
    bin_dir.mkdir()
    pidfiles = {name: scratch / f'{name}.pid' for name in startup.DAEMON_PIDFILES}
    ready = scratch / 'ready'
    found = ' || '.join(f'[ -e {pidfile} ]' for pidfile in pidfiles.values())
    (bin_dir / 'docker').write_text(f'#!/bin/sh\n[ -e {ready} ]\n')
    (bin_dir / 'dockerd').write_text(
        f'#!/bin/sh\nif {found}; then echo "pid file found"; exit 1; fi\n'
        f'echo "dockerd started"\ntouch {ready}\n'
    )
    for stub in bin_dir.iterdir():
        stub.chmod(0o755)
    monkeypatch.setenv('PATH', f'{bin_dir}:/usr/bin:/bin')
    monkeypatch.setattr(startup, 'DAEMON_PIDFILES', pidfiles)
    monkeypatch.setattr(startup, 'DOCKERD_LOG', scratch / 'dockerd.log')
    return pidfiles


@pytest.mark.parametrize('daemon', list(startup.DAEMON_PIDFILES))
@pytest.mark.parametrize('stale', ['live-process', 'missing-process'])
def test_stale_daemon_pidfile_is_removed_before_dockerd_starts(
    scratch: Path, monkeypatch: pytest.MonkeyPatch, daemon: str, stale: str
) -> None:
    """A pid file the previous boot left names no such daemon, so it does not block the start."""
    pidfile = stub_dockerd(scratch, monkeypatch)[daemon]
    pidfile.write_text(f'{os.getpid() if stale == "live-process" else 2**22 + 1}\n')
    startup.start_docker()
    assert 'dockerd started' in startup.DOCKERD_LOG.read_text()
    assert not pidfile.exists()


def test_dockerd_log_keeps_earlier_runs(scratch: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Starting dockerd appends to its log, so a failed earlier start stays readable."""
    stub_dockerd(scratch, monkeypatch)
    startup.DOCKERD_LOG.write_text('earlier run\n')
    startup.start_docker()
    assert startup.DOCKERD_LOG.read_text().startswith('earlier run\n')


def test_dockerd_that_exits_once_ready_counts_as_started(
    scratch: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A dockerd that is ready by the time its exit is seen has started, not failed."""
    stub_dockerd(scratch, monkeypatch)
    ready, probes = scratch / 'ready', scratch / 'probes'
    # The first probe after the launch answers "not ready" only once dockerd is ready and gone.
    (scratch / 'bin/docker').write_text(
        f'#!/bin/sh\necho >> {probes}\nif [ "$(wc -l < {probes})" -eq 2 ]; then\n'
        f'  while [ ! -e {ready} ]; do sleep 0.05; done; sleep 0.2; exit 1\nfi\n[ -e {ready} ]\n'
    )
    startup.start_docker()
    assert 'dockerd started' in startup.DOCKERD_LOG.read_text()
