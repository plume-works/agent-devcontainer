"""Tests for runtime-supervisor.py driving the real supervisord.conf with scripted services."""

from __future__ import annotations

from collections.abc import Callable, Iterator
import configparser
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import time
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SUPERVISOR = REPO_ROOT / '.devcontainer/scripts/runtime-supervisor.py'
CONFIG = REPO_ROOT / 'docker/opencode/supervisord.conf'
TMP_ROOT = REPO_ROOT / '.tmp'
STARTUP_ORDER = ['dockerd', 'dbus', 'keyring', 'prepare', 'cbm', 'index', 'xpra', 'opencode']
STOP_ORDER = ['opencode', 'cbm', 'xpra', 'keyring', 'dbus', 'dockerd']
ONESHOTS = {'prepare', 'index'}

FAKE_SERVICE = """#!/usr/bin/env bash
name="$1"; state="$STATE_DIR"
echo "start $name" >> "$state/events"
mode="$(cat "$state/$name.mode" 2>/dev/null || echo ok)"
if [[ $mode == ignore-term ]]; then
  trap 'echo "stop $name" >> "$state/events"' TERM
else
  trap 'echo "stop $name" >> "$state/events"; rm -f "$state/$name.ready"; exit 0' TERM
fi
if [[ $mode == with-child ]]; then sleep 1000 & echo $! > "$state/$name.child"; fi
[[ $mode == never-ready ]] || touch "$state/$name.ready"
while true; do
  if [[ -f $state/$name.crash ]]; then
    rm -f "$state/$name.crash" "$state/$name.ready"; echo "crash $name" >> "$state/events"; exit 1
  fi
  if [[ $mode == crash-always ]]; then
    sleep 0.3; rm -f "$state/$name.ready"; echo "crash $name" >> "$state/events"; exit 1
  fi
  needs="$(cat "$state/$name.needs" 2>/dev/null || true)"
  if [[ -n $needs && ! -f $state/$needs.ready ]]; then
    rm -f "$state/$name.ready"; echo "lost $name" >> "$state/events"; exit 1
  fi
  sleep 0.1 & wait $!
done
"""
FAKE_ONESHOT = """#!/usr/bin/env bash
name="$1"; state="$STATE_DIR"
echo "run $name" >> "$state/events"
sleep "$(cat "$state/$name.sleep" 2>/dev/null || echo 0)"
exit "$(cat "$state/$name.exit" 2>/dev/null || echo 0)"
"""
FAKE_HEALTH = """#!/usr/bin/env bash
[[ -f $STATE_DIR/$1.ready && ! -f $STATE_DIR/$1.unhealthy ]]
"""
FAKE_BOOTSTRAP = """#!/usr/bin/env bash
echo "run bootstrap" >> "$STATE_DIR/events"
exit "$(cat "$STATE_DIR/bootstrap.exit" 2>/dev/null || echo 0)"
"""


def write_executable(path: Path, body: str) -> Path:
    path.write_text(body)
    path.chmod(0o755)
    return path


def build_config(root: Path, fake_service: Path, fake_oneshot: Path) -> Path:
    """Rewrite the shipped config: same programs and flags, scripted commands, local paths."""
    parser = configparser.RawConfigParser()
    parser.read(CONFIG)
    run_dir = root / 'run'
    parser['unix_http_server']['file'] = str(run_dir / 'supervisor.sock')
    parser['supervisorctl']['serverurl'] = f'unix://{run_dir}/supervisor.sock'
    parser['supervisord']['pidfile'] = str(run_dir / 'supervisord.pid')
    parser['supervisord']['childlogdir'] = str(run_dir)
    parser['eventlistener:controller']['command'] = f'{sys.executable} {SUPERVISOR} control'
    for section in parser.sections():
        if not section.startswith('program:'):
            continue
        name = section.split(':', 1)[1]
        program = parser[section]
        program.pop('user', None)
        program.pop('environment', None)
        fake = fake_oneshot if name in ONESHOTS else fake_service
        program['command'] = f'{fake} {name}'
    path = root / 'supervisord.conf'
    with path.open('w') as handle:
        parser.write(handle)
    return path


class Supervision:
    """One supervised container start under test."""

    def __init__(self, root: Path, **settings: str) -> None:
        self.root = root
        self.state = root / 'state'
        self.state.mkdir(parents=True)
        fake_service = write_executable(root / 'fake-service', FAKE_SERVICE)
        fake_oneshot = write_executable(root / 'fake-oneshot', FAKE_ONESHOT)
        self.env = {
            'PATH': os.environ['PATH'],
            'STATE_DIR': str(self.state),
            'AGENTDEV_RUN_DIR': str(root / 'run'),
            'AGENTDEV_SUPERVISOR_CONFIG': str(build_config(root, fake_service, fake_oneshot)),
            'AGENTDEV_BOOTSTRAP_COMMAND': str(
                write_executable(root / 'bootstrap', FAKE_BOOTSTRAP)
            ),
            'AGENTDEV_HEALTH_COMMAND': str(write_executable(root / 'health', FAKE_HEALTH)),
            'AGENTDEV_HEALTH_INTERVAL': '0.2',
            'AGENTDEV_RECOVERY_BACKOFF': '0.05',
            'AGENTDEV_SERVICE_START_TIMEOUT': '3',
            'AGENTDEV_PREPARE_TIMEOUT': '3',
            'AGENTDEV_STOP_TIMEOUT': '2',
            'DEV_WORKSPACE_FOLDER': str(root),
            **settings,
        }
        self.process: subprocess.Popen[str] | None = None

    def set(self, name: str, kind: str, value: str = '') -> None:
        (self.state / f'{name}.{kind}').write_text(value)

    def start(self) -> None:
        self.process = subprocess.Popen(
            [sys.executable, SUPERVISOR, 'run'],
            env=self.env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    def events(self) -> list[str]:
        path = self.state / 'events'
        return path.read_text().splitlines() if path.exists() else []

    def ready(self) -> bool:
        return (self.root / 'run/ready').exists()

    def wait_for(self, predicate: Callable[[], bool], timeout: float = 20) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if predicate():
                return
            assert self.process is not None
            if self.process.poll() is not None:
                break
            time.sleep(0.1)
        if not predicate():
            pytest.fail(f'condition not met; events={self.events()} output={self.output()}')

    def wait_exit(self, timeout: float = 30) -> int:
        assert self.process is not None
        return self.process.wait(timeout=timeout)

    def output(self) -> str:
        if self.process is None or self.process.poll() is None or self.process.stdout is None:
            return ''
        return self.process.stdout.read()

    def terminate(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.send_signal(signal.SIGTERM)
            try:
                self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.process.kill()


@pytest.fixture
def make() -> Iterator[Callable[..., Supervision]]:
    TMP_ROOT.mkdir(exist_ok=True)
    created: list[Supervision] = []

    def factory(**settings: str) -> Supervision:
        box = Supervision(TMP_ROOT / f'sv-{uuid4().hex[:8]}', **settings)
        created.append(box)
        return box

    yield factory
    for box in created:
        box.terminate()
        shutil.rmtree(box.root, ignore_errors=True)


def started(events: list[str]) -> list[str]:
    return [e.split()[1] for e in events if e.split()[0] in {'start', 'run'}]


def test_starts_services_in_dependency_order_then_publishes_readiness(make):
    box = make()
    box.start()
    box.wait_for(box.ready)
    assert started(box.events()) == ['bootstrap', *STARTUP_ORDER]


def test_disabled_xpra_is_neither_started_nor_required(make):
    box = make(AGENTDEV_SKIP_XPRA='1')
    box.start()
    box.wait_for(box.ready)
    assert 'xpra' not in started(box.events())


@pytest.mark.parametrize('failure', ['exit', 'timeout'])
def test_preparation_failure_keeps_opencode_unavailable_and_exits_nonzero(make, failure):
    box = make()
    if failure == 'exit':
        box.set('prepare', 'exit', '7')
    else:
        box.set('prepare', 'sleep', '30')
    box.start()
    assert box.wait_exit() == 1
    assert 'opencode' not in started(box.events())
    assert not box.ready()
    reason = (box.root / 'run/failed').read_text()
    assert 'prepare' in reason


def test_bootstrap_failure_exits_before_any_service(make):
    box = make()
    box.set('bootstrap', 'exit', '1')
    box.start()
    assert box.wait_exit() == 1
    assert started(box.events()) == ['bootstrap']


def test_a_crashed_service_recovers_without_rerunning_preparation(make):
    box = make()
    box.start()
    box.wait_for(box.ready)
    box.set('cbm', 'crash')
    box.wait_for(lambda: started(box.events()).count('cbm') == 2 and box.ready())
    runs = started(box.events())
    assert runs.count('prepare') == 1 and runs.count('index') == 1
    assert runs.count('opencode') == 2, 'OpenCode reconnects to the replacement CBM daemon'


def test_readiness_loss_counts_as_failure(make):
    box = make()
    box.start()
    box.wait_for(box.ready)
    box.set('xpra', 'unhealthy')
    box.wait_for(lambda: not box.ready())
    (box.state / 'xpra.unhealthy').unlink()
    box.wait_for(lambda: started(box.events()).count('xpra') == 2 and box.ready())


def test_exhausted_recovery_after_running_stops_everything_and_exits_nonzero(make):
    box = make()
    box.start()
    box.wait_for(box.ready)
    box.set('cbm', 'mode', 'crash-always')
    box.set('cbm', 'crash')
    assert box.wait_exit() == 1
    assert started(box.events()).count('cbm') == 4
    assert 'cbm exhausted 3 recovery attempts' in (box.root / 'run/failed').read_text()


def test_startup_failure_exhausts_the_same_budget(make):
    box = make()
    box.set('xpra', 'mode', 'never-ready')
    box.start()
    assert box.wait_exit() == 1
    assert started(box.events()).count('xpra') == 4
    assert 'opencode' not in started(box.events())


def test_hung_service_is_not_treated_as_healthy(make):
    box = make(AGENTDEV_RECOVERY_ATTEMPTS='1')
    box.start()
    box.wait_for(box.ready)
    box.set('dockerd', 'unhealthy')
    assert box.wait_exit() == 1
    assert 'dockerd exhausted' in (box.root / 'run/failed').read_text()


def test_dependency_outage_recovers_clients_outside_their_budget(make):
    box = make(AGENTDEV_RECOVERY_ATTEMPTS='1')
    box.set('keyring', 'needs', 'dbus')
    box.start()
    box.wait_for(box.ready)
    box.set('dbus', 'crash')
    box.wait_for(lambda: started(box.events()).count('keyring') == 2 and box.ready())
    assert 'lost keyring' in box.events()
    assert box.process is not None and box.process.poll() is None


def test_budget_resets_after_a_healthy_period(make):
    box = make(AGENTDEV_RECOVERY_ATTEMPTS='1', AGENTDEV_HEALTHY_RESET='0.5')
    box.start()
    box.wait_for(box.ready)
    for count in (2, 3):
        box.set('cbm', 'crash')
        box.wait_for(lambda c=count: started(box.events()).count('cbm') == c and box.ready())
        time.sleep(1.2)
    assert box.process is not None and box.process.poll() is None


def test_sigterm_stops_in_dependency_order_and_reaps_process_groups(make):
    box = make()
    box.set('opencode', 'mode', 'with-child')
    box.start()
    box.wait_for(box.ready)
    child = int((box.state / 'opencode.child').read_text())

    assert box.process is not None
    box.process.send_signal(signal.SIGTERM)
    assert box.wait_exit() == 0

    stops = [e.split()[1] for e in box.events() if e.startswith('stop ')]
    assert stops == STOP_ORDER
    with pytest.raises(ProcessLookupError):
        os.kill(child, 0)


def test_shutdown_is_bounded_when_a_service_ignores_sigterm(make):
    box = make()
    box.set('cbm', 'mode', 'ignore-term')
    box.start()
    box.wait_for(box.ready)
    started_at = time.monotonic()
    assert box.process is not None
    box.process.send_signal(signal.SIGTERM)
    assert box.wait_exit() == 0
    assert time.monotonic() - started_at < 15


def test_shipped_config_runs_user_services_unprivileged_and_logs_to_stdout():
    parser = configparser.RawConfigParser()
    parser.read(CONFIG)
    programs = {
        s.split(':', 1)[1]: parser[s] for s in parser.sections() if s.startswith('program:')
    }
    assert set(programs) == set(STARTUP_ORDER)
    for name, program in programs.items():
        assert program['autostart'] == 'false' and program['startretries'] == '0'
        assert program['stdout_logfile'] == '/dev/stdout'
        assert program['killasgroup'] == 'true'
        assert ('user' in program) == (name != 'dockerd')
    priorities = sorted(STOP_ORDER, key=lambda n: -int(programs[n]['priority']))
    assert priorities == STOP_ORDER
    assert parser['eventlistener:controller']['priority'] == '999'


def test_every_supervised_service_has_a_real_probe():
    health = (REPO_ROOT / '.devcontainer/scripts/runtime-health.sh').read_text()
    probes = health.split('case "$service" in', 2)[2]
    for name in STOP_ORDER:
        assert f'\n  {name})' in probes or f'\n  {name} |' in probes, name
