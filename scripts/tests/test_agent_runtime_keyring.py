"""Tests for the instance-local D-Bus/keyring services shared by both lifecycles."""

from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / '.devcontainer/scripts'
RUNTIME_KEYRING = SCRIPTS / 'runtime-keyring.sh'
SETUP_KEYRING = SCRIPTS / 'setup-keyring.sh'
CLIENT = Path(__file__).with_name('secret_service_client.py')
SYSTEM_PYTHON = '/usr/bin/python3'
TMP_ROOT = REPO_ROOT / '.tmp'

pytestmark = pytest.mark.skipif(
    not all(shutil.which(tool) for tool in ('dbus-daemon', 'gnome-keyring-daemon', 'gdbus'))
    or subprocess.run([SYSTEM_PYTHON, '-c', 'import gi'], capture_output=True).returncode != 0,
    reason='the GNOME keyring stack is not installed',
)


class Instance:
    """One container's home and private runtime directory."""

    def __init__(self, root: Path) -> None:
        self.home = root / 'home'
        self.runtime = root / 'run'
        self.home.mkdir(parents=True)
        self.processes: list[subprocess.Popen[bytes]] = []

    @property
    def env(self) -> dict[str, str]:
        return {
            'PATH': '/usr/bin:/bin',
            'HOME': str(self.home),
            'XDG_RUNTIME_DIR': str(self.runtime),
            'DBUS_SESSION_BUS_ADDRESS': f'unix:path={self.runtime}/bus',
        }

    def start(self, piece: str) -> subprocess.Popen[bytes]:
        process = subprocess.Popen(
            [RUNTIME_KEYRING, piece],
            env=self.env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.processes.append(process)
        return process

    def wait_ready(self) -> None:
        result = subprocess.run([RUNTIME_KEYRING, 'wait', '10'], env=self.env, capture_output=True)
        assert result.returncode == 0, result.stderr

    def check(self) -> int:
        return subprocess.run([RUNTIME_KEYRING, 'check'], env=self.env).returncode

    def child(self, *args: str) -> subprocess.CompletedProcess[str]:
        """Run the client the way OpenCode runs a tool: only the inherited environment."""
        return subprocess.run(
            [SYSTEM_PYTHON, CLIENT, *args],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def stop_all(self) -> None:
        for process in self.processes:
            if process.poll() is None:
                process.terminate()
        for process in self.processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


@pytest.fixture
def instance() -> Iterator[Instance]:
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'kr-{uuid4().hex[:8]}'
    box = Instance(root)
    try:
        yield box
    finally:
        box.stop_all()
        shutil.rmtree(root, ignore_errors=True)


def wait_exit(process: subprocess.Popen[bytes], timeout: float = 10) -> bool:
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        return False
    return True


def test_env_names_a_deterministic_private_socket(instance: Instance):
    printed = subprocess.run(
        [RUNTIME_KEYRING, 'env'], env=instance.env, capture_output=True, text=True, check=True
    ).stdout
    assert f"export DBUS_SESSION_BUS_ADDRESS='unix:path={instance.runtime}/bus'" in printed
    assert f"export XDG_RUNTIME_DIR='{instance.runtime}'" in printed


def test_foreground_services_serve_secrets_to_a_child_process(instance: Instance):
    instance.start('dbus')
    instance.start('keyring')
    instance.wait_ready()

    assert instance.child('store', 'gh', 's3cret').returncode == 0
    looked_up = instance.child('lookup', 'gh')
    assert looked_up.returncode == 0, looked_up.stderr
    assert looked_up.stdout.strip() == 's3cret'
    assert (instance.runtime.stat().st_mode & 0o777) == 0o700


def test_secrets_survive_dbus_and_keyring_replacement(instance: Instance):
    bus = instance.start('dbus')
    keyring = instance.start('keyring')
    instance.wait_ready()
    assert instance.child('store', 'gh', 'kept').returncode == 0

    bus.send_signal(signal.SIGKILL)
    assert wait_exit(bus)
    assert wait_exit(keyring), 'the keyring must exit with its bus so a supervisor restarts it'
    assert instance.check() != 0

    instance.start('dbus')
    instance.start('keyring')
    instance.wait_ready()
    assert instance.child('lookup', 'gh').stdout.strip() == 'kept'


def test_existing_keyring_is_never_overwritten(instance: Instance):
    keyrings = instance.home / '.local/share/keyrings'
    keyrings.mkdir(parents=True)
    original = (
        '[keyring]\ndisplay-name=login\nctime=1\nmtime=0\nlock-on-idle=false\nlock-after=false\n'
    )
    (keyrings / 'login.keyring').write_text(original)
    stat_before = (keyrings / 'login.keyring').stat()

    instance.start('dbus')
    instance.start('keyring')
    instance.wait_ready()

    assert (keyrings / 'login.keyring').stat().st_ino == stat_before.st_ino
    assert (keyrings / 'login.keyring').read_text().startswith('[keyring]\ndisplay-name=login')


def test_no_session_state_is_persisted_in_home(instance: Instance):
    instance.start('dbus')
    instance.start('keyring')
    instance.wait_ready()
    instance.stop_all()

    persisted = sorted(
        p.relative_to(instance.home).as_posix() for p in instance.home.rglob('*') if not p.is_dir()
    )
    assert persisted == ['.local/share/keyrings/login.keyring']


def test_keyring_waits_for_its_bus_instead_of_spawning_one(instance: Instance):
    keyring = instance.start('keyring')
    time.sleep(1)
    assert keyring.poll() is None
    assert not (instance.runtime / 'bus').exists()
    instance.start('dbus')
    instance.wait_ready()


def test_background_lifecycle_still_starts_and_reuses_a_session(tmp_path: Path):
    home = tmp_path / 'home'
    home.mkdir()
    env_file = tmp_path / 'state/keyring-session.env'
    env = {'PATH': '/usr/bin:/bin', 'HOME': str(home), 'AGENTDEV_KEYRING_ENV_FILE': str(env_file)}
    first = subprocess.run([SETUP_KEYRING], env=env, capture_output=True, text=True)
    try:
        assert first.returncode == 0, first.stderr
        assert (env_file.stat().st_mode & 0o777) == 0o600
        saved = env_file.read_text()
        second = subprocess.run([SETUP_KEYRING], env=env, capture_output=True, text=True)
        assert second.returncode == 0, second.stderr
        assert env_file.read_text() == saved
    finally:
        pid = (
            next(
                line.split("'")[1]
                for line in env_file.read_text().splitlines()
                if 'DBUS_SESSION_BUS_PID' in line
            )
            if env_file.exists()
            else ''
        )
        if pid:
            os.kill(int(pid), signal.SIGTERM)
