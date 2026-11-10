"""Tests for .claude/startup.py, the Claude Code cloud session setup script."""

from collections.abc import Iterator
import importlib.util
import json
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
STUBBED = ('claude', 'bash', 'ansible-playbook', 'uv', 'docker', 'dockerd')


def load_startup() -> ModuleType:
    """Import startup.py, which lives outside any package."""
    spec = importlib.util.spec_from_file_location('cloud_startup', STARTUP)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


startup = load_startup()


def free_port() -> int:
    """Return a TCP port nothing listens on right now."""
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


@pytest.fixture
def scratch() -> Iterator[Path]:
    """Yield a fresh scratch directory under real /tmp."""
    path = TMP_ROOT / f'cloud-startup-{uuid4().hex}'
    path.mkdir(parents=True)
    yield path
    shutil.rmtree(path)


def run_startup(
    scratch: Path, *args: str, failing: str = 'docker dockerd', **env: str
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    """Run startup.py with stubs that log each call; the stubs named in failing exit 1."""
    bin_dir = scratch / 'bin'
    bin_dir.mkdir()
    calls = scratch / 'calls'
    for name in STUBBED:
        stub = bin_dir / name
        stub.write_text(
            f'#!/bin/sh\necho {name} "$@" ANSIBLE_LOG_PATH="${{ANSIBLE_LOG_PATH-unset}}"'
            f' >> {calls}\nexit {1 if name in failing.split() else 0}\n'
        )
        stub.chmod(0o755)
    result = subprocess.run(
        [sys.executable, str(STARTUP), *args],
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


def test_setup_gives_its_commands_blocking_stdio(scratch: Path) -> None:
    """Setup started on non-blocking stdio hands its commands blocking ones, which Ansible needs."""
    bin_dir = scratch / 'bin'
    bin_dir.mkdir()
    report = scratch / 'blocking'
    probe = f'import os; print(*map(os.get_blocking, (0, 1, 2)), file=open("{report}", "a"))'
    for name in STUBBED:
        (bin_dir / name).write_text(f"#!/bin/sh\n{sys.executable} -c '{probe}'\n")
        (bin_dir / name).chmod(0o755)
    read_end, write_end = os.pipe()
    stdin_read, stdin_write = os.pipe()
    for fd in (write_end, stdin_read):
        os.set_blocking(fd, False)
    try:
        result = subprocess.run(
            [sys.executable, str(STARTUP), 'setup'],
            env={'PATH': f'{bin_dir}:/usr/bin:/bin', 'HOME': str(scratch)},
            stdin=stdin_read,
            stdout=write_end,
            stderr=write_end,
            check=False,
        )
    finally:
        for fd in (read_end, write_end, stdin_read, stdin_write):
            os.close(fd)
    assert result.returncode == 0
    assert set(report.read_text().splitlines()) == {'True True True'}


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
    result, calls = run_startup(scratch, 'resume', **env)
    assert (result.returncode, result.stdout) == (0, '')
    assert calls == []


def test_resume_on_a_cloud_host_starts_docker(scratch: Path) -> None:
    """On a cloud-session host, resume starts dockerd and fails at once when it exits."""
    started = time.monotonic()
    result, calls = run_startup(scratch, 'resume', CLAUDE_CODE_REMOTE='true')
    assert result.returncode == 1
    assert 'dockerd exited with 1' in result.stderr
    assert f'dockerd --bip {startup.DOCKER_BRIDGE_CIDR}' in calls
    assert time.monotonic() - started < startup.DOCKER_WAIT_SECONDS


def test_unknown_mode_is_a_usage_error(scratch: Path) -> None:
    """Only setup and resume are modes."""
    result, calls = run_startup(scratch, 'restart')
    assert result.returncode == 2
    assert calls == []


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


def test_proxy_access_points_docker_clients_at_the_relay(
    scratch: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Docker's client config sends containers through the relay and keeps its other keys."""
    monkeypatch.setenv('HOME', str(scratch))
    monkeypatch.setattr(startup, 'RELAY_PIDFILE', scratch / 'relay.pid')
    monkeypatch.setattr(startup, 'RELAY_LOG', scratch / 'relay.log')
    monkeypatch.setattr(startup, 'RELAY_HOST', '127.0.0.1')
    monkeypatch.setattr(startup, 'RELAY_PORT', free_port())
    config = scratch / '.docker/config.json'
    config.parent.mkdir()
    config.write_text(json.dumps({'auths': {'ghcr.io': {}}}))
    startup.prepare_proxy_access(
        {'HTTPS_PROXY': f'http://127.0.0.1:{free_port()}', 'NO_PROXY': 'x'}
    )
    try:
        relay = f'http://127.0.0.1:{startup.RELAY_PORT}'
        assert json.loads(config.read_text()) == {
            'auths': {'ghcr.io': {}},
            'proxies': {'default': {'httpProxy': relay, 'httpsProxy': relay, 'noProxy': 'x'}},
        }
    finally:
        startup.stop_relay(startup.RELAY_PIDFILE)


def test_no_loopback_proxy_removes_stale_access(
    scratch: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Without the agent proxy, the Docker client stops sending containers to a dead relay."""
    monkeypatch.setenv('HOME', str(scratch))
    monkeypatch.setattr(startup, 'RELAY_PIDFILE', scratch / 'relay.pid')
    config = scratch / '.docker/config.json'
    config.parent.mkdir()
    config.write_text(json.dumps({'proxies': {'default': {'httpsProxy': 'http://stale'}}}))
    startup.prepare_proxy_access({})
    assert json.loads(config.read_text()) == {'proxies': {}}


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
