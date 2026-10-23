"""Lifecycle tests for runtime-cbm.sh against the shipped codebase-memory-mcp pin."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
from uuid import uuid4

from cbm_pin import binary_version, pinned_version, stage_pinned_cbm
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / '.devcontainer/scripts/runtime-cbm.sh'
TMP_ROOT = REPO_ROOT / '.tmp'
ISOLATED_UID = 54321
IS_ROOT = os.geteuid() == 0


@pytest.fixture(scope='module')
def cbm_binary() -> Path:
    return stage_pinned_cbm()


@dataclass
class Sandbox:
    """An isolated account, home, cache, and daemon rendezvous for one test."""

    root: Path
    binary: Path
    uid: int

    @property
    def home(self) -> Path:
        return self.root / 'home'

    @property
    def cache(self) -> Path:
        return self.root / 'cache'

    def env(self, **extra: str) -> dict[str, str]:
        """Return the minimal environment the runtime passes to CBM services."""
        return {
            'PATH': f'{self.binary.parent}:/usr/local/bin:/usr/bin:/bin',
            'HOME': str(self.home),
            'CBM_CACHE_DIR': str(self.cache),
            'CBM_RUNTIME_DIR': str(self.root / 'run'),
            'AGENTDEV_CBM_BIN': str(self.binary),
            'AGENTDEV_CBM_STATE_DIR': str(self.root / 'state'),
            'AGENTDEV_CBM_POLL_INTERVAL': '0.5',
            **extra,
        }

    def argv(self, *command: str | Path, offline: bool = False) -> list[str]:
        """Prefix a command so it runs as the sandbox account."""
        prefix: list[str] = []
        if IS_ROOT:
            prefix = ['setpriv', f'--reuid={self.uid}', f'--regid={self.uid}', '--clear-groups']
            if offline:
                prefix = ['unshare', '-n', *prefix]
        return [*prefix, *map(str, command)]

    def run(self, *command: str | Path, offline: bool = False, **extra: str):
        """Run a command as the sandbox account and return the completed process."""
        return subprocess.run(
            self.argv(*command, offline=offline),
            env=self.env(**extra),
            capture_output=True,
            text=True,
            timeout=180,
        )

    def adapter(self, *args: str, **extra: str):
        return self.run(SCRIPT, *args, **extra)

    def popen_adapter(self, *args: str, **extra: str) -> subprocess.Popen[str]:
        return subprocess.Popen(
            self.argv(SCRIPT, *args),
            env=self.env(**extra),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def cbm(self, *args: str):
        return self.run(self.binary, *args)

    def daemon_pid(self) -> int | None:
        """Return the pid `daemon status` reports active, or None."""
        result = self.cbm('daemon', 'status')
        if result.returncode != 0:
            return None
        line = next(ln for ln in result.stdout.splitlines() if 'pid:' in ln)
        return int(line.split()[-1])

    def generation(self) -> tuple[int, int]:
        pid, started = (self.root / 'state/generation').read_text().split()
        return int(pid), int(started)


def wait_until(predicate, timeout: float = 30.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.2)
    return False


def pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


@pytest.fixture
def sandbox(cbm_binary: Path) -> Iterator[Sandbox]:
    """Create per-test state owned by an isolated account; stop its daemon afterwards."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'runtime-cbm-{uuid4().hex[:12]}'
    uid = ISOLATED_UID if IS_ROOT else os.geteuid()
    for name in ('home', 'cache', 'run', 'state'):
        (root / name).mkdir(parents=True)
        (root / name).chmod(0o700)
        if IS_ROOT:
            os.chown(root / name, uid, uid)
    box = Sandbox(root, cbm_binary, uid)
    box.cbm('config', 'set', 'ui_enabled', 'false')
    try:
        yield box
    finally:
        pid = box.daemon_pid()
        box.cbm('daemon', 'stop')
        if pid and wait_until(lambda: not pid_alive(pid), 10) is False:
            os.kill(pid, signal.SIGKILL)
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def checkout(sandbox: Sandbox) -> Path:
    """Create a Git checkout owned by the invoking user, as a bind mount would be."""
    repo = sandbox.root / 'checkout'
    repo.mkdir()
    (repo / 'module.py').write_text('def answer():\n    return 42\n')
    git = ['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid']
    subprocess.run([*git, 'init', '-q'], check=True)
    subprocess.run([*git, 'add', '.'], check=True)
    subprocess.run([*git, 'commit', '-qm', 'init'], check=True)
    return repo


def owners(path: Path) -> set[int]:
    return {p.stat().st_uid for p in [path, *path.rglob('*')]}


def test_start_index_and_stop_as_isolated_user(sandbox: Sandbox, checkout: Path):
    checkout_owners = owners(checkout)

    started = sandbox.adapter('start')
    assert started.returncode == 0, started.stderr
    assert sandbox.adapter('check').returncode == 0
    pid, _ = sandbox.generation()
    assert sandbox.daemon_pid() == pid

    indexed = sandbox.adapter('index', str(checkout))
    assert indexed.returncode == 0, indexed.stderr
    assert 'in the background' in indexed.stdout
    deadline = time.monotonic() + 60
    while str(checkout) not in sandbox.cbm('cli', '--json', 'list_projects').stdout:
        assert time.monotonic() < deadline, 'the background index never registered the project'
        time.sleep(0.5)

    assert owners(sandbox.cache) == {sandbox.uid}
    assert owners(checkout) == checkout_owners

    stopped = sandbox.adapter('stop')
    assert stopped.returncode == 0, stopped.stderr
    assert sandbox.daemon_pid() is None
    assert sandbox.adapter('check').returncode == 3


def test_detects_death_and_restarts_without_duplicates(sandbox: Sandbox):
    assert sandbox.adapter('start').returncode == 0
    first, _ = sandbox.generation()
    os.kill(first, signal.SIGKILL)
    assert wait_until(lambda: not pid_alive(first))

    assert sandbox.adapter('check').returncode == 3

    assert sandbox.adapter('start').returncode == 0
    second, _ = sandbox.generation()
    assert second != first
    assert sandbox.adapter('check').returncode == 0
    again = sandbox.adapter('start')
    assert again.returncode == 0
    assert sandbox.generation()[0] == second


def test_reports_a_generation_it_did_not_start(sandbox: Sandbox):
    assert sandbox.adapter('start').returncode == 0
    first, _ = sandbox.generation()
    sandbox.cbm('daemon', 'stop')
    assert wait_until(lambda: not pid_alive(first))
    assert sandbox.cbm('daemon', 'start').returncode == 0

    assert sandbox.adapter('check').returncode == 5


def test_never_kills_a_reused_pid(sandbox: Sandbox):
    bystander = subprocess.Popen(['sleep', '60'])
    try:
        (sandbox.root / 'state/generation').write_text(f'{bystander.pid} 1\n')
        result = sandbox.adapter('stop', AGENTDEV_CBM_STOP_TIMEOUT='2')
        assert result.returncode == 0, result.stderr
        assert bystander.poll() is None
    finally:
        bystander.kill()
        bystander.wait()


def wait_ready(process: subprocess.Popen[str], sandbox: Sandbox) -> int:
    assert wait_until(lambda: (sandbox.root / 'state/generation').exists()), process.stderr
    return sandbox.generation()[0]


def test_run_exits_nonzero_when_the_daemon_dies(sandbox: Sandbox):
    process = sandbox.popen_adapter('run')
    try:
        pid = wait_ready(process, sandbox)
        os.kill(pid, signal.SIGKILL)
        assert process.wait(timeout=30) != 0
    finally:
        if process.poll() is None:
            process.kill()


def test_run_stops_the_daemon_on_sigterm(sandbox: Sandbox):
    process = sandbox.popen_adapter('run')
    pid = wait_ready(process, sandbox)
    process.send_signal(signal.SIGTERM)
    assert process.wait(timeout=60) == 0, process.stderr.read() if process.stderr else ''
    assert wait_until(lambda: not pid_alive(pid), 10)
    assert sandbox.daemon_pid() is None


def test_stop_is_bounded_while_a_client_holds_the_daemon(sandbox: Sandbox):
    assert sandbox.adapter('start').returncode == 0
    pid, _ = sandbox.generation()
    client = subprocess.Popen(
        sandbox.argv(sandbox.binary),
        env=sandbox.env(),
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    try:
        assert client.stdin is not None and client.stdout is not None
        client.stdin.write(
            json.dumps(
                {
                    'jsonrpc': '2.0',
                    'id': 1,
                    'method': 'initialize',
                    'params': {
                        'protocolVersion': '2025-06-18',
                        'capabilities': {},
                        'clientInfo': {'name': 'test', 'version': '1'},
                    },
                }
            )
            + '\n'
        )
        client.stdin.flush()
        assert '"id":1' in client.stdout.readline()

        started = time.monotonic()
        result = sandbox.adapter('stop', AGENTDEV_CBM_STOP_TIMEOUT='3')
        assert result.returncode == 0, result.stderr
        assert time.monotonic() - started < 20
        assert not pid_alive(pid)
    finally:
        client.kill()
        client.wait()


def test_install_publishes_the_exact_pinned_binary_offline(sandbox: Sandbox):
    (sandbox.home / '.claude.json').write_text('{}\n')
    for directory in ('.codex', '.config/opencode'):
        (sandbox.home / directory).mkdir(parents=True)
    if IS_ROOT:
        for path in [sandbox.home, *sandbox.home.rglob('*')]:
            os.chown(path, sandbox.uid, sandbox.uid)

    result = sandbox.run(SCRIPT, 'install', offline=True)
    assert result.returncode == 0, result.stdout + result.stderr

    installed = sandbox.home / '.local/bin/codebase-memory-mcp'
    assert installed.read_bytes() == sandbox.binary.read_bytes()
    assert installed.stat().st_uid == sandbox.uid
    assert binary_version(installed) == pinned_version()
    server = json.loads((sandbox.home / '.claude.json').read_text())['mcpServers']
    assert server['codebase-memory-mcp']['command'] == str(installed)
    assert not (sandbox.home / '.cache/codebase-memory-mcp').exists()
