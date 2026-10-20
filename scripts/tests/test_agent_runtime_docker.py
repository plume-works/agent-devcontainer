"""Tests for runtime-docker.sh: guards, the exact dockerd invocation, and a real nested engine."""

from __future__ import annotations

from collections.abc import Iterator
import json
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / '.devcontainer/scripts'
SCRIPT = SCRIPTS / 'runtime-docker.sh'
PINS = REPO_ROOT / 'devcontainer-compose-pins.yml'
TMP_ROOT = REPO_ROOT / '.tmp'
PRIVILEGED_CAPS = 'CapEff:\t000001ffffffffff\n'
UNPRIVILEGED_CAPS = 'CapEff:\t00000000a80425fb\n'
DAEMON_JSON = {'builder': {'gc': {'enabled': True, 'defaultMaxUsedSpace': '10GB'}}}

needs_root = pytest.mark.skipif(os.geteuid() != 0, reason='dockerd guards require root')


class Engine:
    """A scripted engine environment with a fake dockerd that records its argv."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.bin = root / 'bin'
        self.bin.mkdir(parents=True)
        self.data = root / 'data'
        self.config = root / 'daemon.json'
        self.config.write_text(json.dumps(DAEMON_JSON))
        self.status = root / 'status'
        self.status.write_text(PRIVILEGED_CAPS)
        self.pidfile = root / 'docker.pid'
        self.argv = root / 'argv'
        fake = self.bin / 'dockerd'
        fake.write_text(f'#!/usr/bin/env bash\nprintf "%s\\n" "$@" > "{self.argv}"\n')
        fake.chmod(0o755)

    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        env = {
            'PATH': f'{self.bin}:/usr/bin:/bin',
            'AGENTDEV_DOCKER_DATA_DIR': str(self.data),
            'AGENTDEV_DOCKER_SOCKET': str(self.root / 'docker.sock'),
            'AGENTDEV_DOCKER_CONFIG': str(self.config),
            'AGENTDEV_DOCKER_EXEC_ROOT': str(self.root / 'exec'),
            'AGENTDEV_DOCKER_PIDFILE': str(self.pidfile),
            'AGENTDEV_PROC_STATUS': str(self.status),
        }
        return subprocess.run([SCRIPT, *args], env=env, capture_output=True, text=True)


@pytest.fixture
def engine(tmp_path: Path) -> Engine:
    return Engine(tmp_path)


@needs_root
def test_execs_one_dockerd_on_the_private_socket(engine: Engine):
    result = engine.run('run')
    assert result.returncode == 0, result.stderr
    assert engine.argv.read_text().splitlines() == [
        '--config-file',
        str(engine.config),
        '--data-root',
        str(engine.data),
        '--exec-root',
        str(engine.root / 'exec'),
        '--pidfile',
        str(engine.pidfile),
        '--host',
        f'unix://{engine.root / "docker.sock"}',
        '--group',
        'docker',
    ]


@needs_root
def test_refuses_an_unprivileged_container(engine: Engine):
    engine.status.write_text(UNPRIVILEGED_CAPS)
    result = engine.run('run')
    assert result.returncode == 1
    assert 'privileged' in result.stderr
    assert not engine.argv.exists()


@needs_root
def test_refuses_configured_listeners(engine: Engine):
    engine.config.write_text(json.dumps({**DAEMON_JSON, 'hosts': ['tcp://0.0.0.0:2375']}))
    result = engine.run('run')
    assert result.returncode == 1
    assert 'declares listeners' in result.stderr


@needs_root
def test_refuses_a_second_engine_but_clears_a_stale_pid_file(engine: Engine, tmp_path: Path):
    impostor = tmp_path / 'dockerd'
    shutil.copy2(shutil.which('sleep') or '/bin/sleep', impostor)
    live = subprocess.Popen([impostor, '30'])
    try:
        engine.pidfile.write_text(str(live.pid))
        result = engine.run('run')
        assert result.returncode == 1
        assert f'already running as pid {live.pid}' in result.stderr
    finally:
        live.kill()
        live.wait()
    assert engine.run('run').returncode == 0
    assert not engine.pidfile.exists()


def test_preparation_prunes_images_before_touching_the_workspace():
    prepare = (SCRIPTS / 'runtime-workspace.sh').read_text().split('cmd_prepare() {', 1)[1]
    assert prepare.index('docker-image-prune.sh') < prepare.index('cmd_checkout')


def desktop_image() -> str | None:
    """Return a local agent-desktop image to run the nested engine in, if one is present."""
    candidates = [os.environ.get('AGENTDEV_DESKTOP_TEST_IMAGE', '')]
    for line in PINS.read_text().splitlines():
        if line.strip().startswith('image:'):
            candidates.append(line.split('image:', 1)[1].strip())
    for image in filter(None, candidates):
        if (
            subprocess.run(['docker', 'image', 'inspect', image], capture_output=True).returncode
            == 0
        ):
            return image
    return None


@pytest.fixture
def nested() -> Iterator[tuple[str, str]]:
    if shutil.which('docker') is None or desktop_image() is None:
        pytest.skip('requires Docker and a local agent-desktop image')
    volume = f'agentdev-test-docker-{uuid4().hex[:8]}'
    try:
        yield desktop_image() or '', volume
    finally:
        subprocess.run(['docker', 'volume', 'rm', '-f', volume], capture_output=True)


NESTED_SCRIPT = """
set -euo pipefail
useradd --uid 2000 --gid docker --no-create-home builder
start() {
  /opt/agentdev-runtime/runtime-docker.sh run >/tmp/dockerd.log 2>&1 &
  for _ in $(seq 120); do docker info >/dev/null 2>&1 && return; sleep 0.5; done
  cat /tmp/dockerd.log; exit 1
}
start
mkdir -p /tmp/ctx && echo payload > /tmp/ctx/f && printf 'FROM scratch\\nCOPY f /f\\n' > /tmp/ctx/Dockerfile
chown -R builder /tmp/ctx
mkdir -p /tmp/bh && chown builder /tmp/bh
setpriv --reuid=builder --regid=docker --init-groups env HOME=/tmp/bh docker build -q -t agentdev-nested:probe /tmp/ctx >/dev/null
echo built-as-user
if ss -ltn | grep -q ':2375\\|:2376'; then echo tcp-listener; fi
pkill -KILL -x dockerd; sleep 1
start
docker image inspect agentdev-nested:probe >/dev/null && echo kept-after-crash
docker info --format '{{.DockerRootDir}}'
"""


def test_nested_engine_builds_as_user_and_keeps_images_across_restarts(nested):
    image, volume = nested
    base = [
        'docker',
        'run',
        '--rm',
        '--privileged',
        '-v',
        f'{SCRIPTS}:/opt/agentdev-runtime:ro',
        '-v',
        f'{volume}:/var/lib/docker',
        '--entrypoint',
        'bash',
        image,
        '-c',
    ]
    first = subprocess.run([*base, NESTED_SCRIPT], capture_output=True, text=True, timeout=600)
    assert first.returncode == 0, first.stdout + first.stderr
    lines = first.stdout.splitlines()
    assert 'built-as-user' in lines and 'kept-after-crash' in lines
    assert 'tcp-listener' not in lines
    assert lines[-1] == '/var/lib/docker'

    replacement = (
        '/opt/agentdev-runtime/runtime-docker.sh run >/tmp/d.log 2>&1 & '
        'for _ in $(seq 120); do docker info >/dev/null 2>&1 && break; sleep 0.5; done; '
        'docker image inspect agentdev-nested:probe >/dev/null && echo kept-after-replacement'
    )
    second = subprocess.run([*base, replacement], capture_output=True, text=True, timeout=600)
    assert 'kept-after-replacement' in second.stdout, second.stdout + second.stderr
