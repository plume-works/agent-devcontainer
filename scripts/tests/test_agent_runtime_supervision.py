"""Tests for runtime-supervisor.py driving the real supervisord.conf with scripted services."""

from __future__ import annotations

from collections.abc import Callable, Iterator
import configparser
import json
import os
from pathlib import Path
import pwd
import shutil
import signal
import subprocess
import sys
import time
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

REPO_ROOT = Path(__file__).resolve().parents[2]
SUPERVISOR = REPO_ROOT / '.devcontainer/scripts/runtime-supervisor.py'
CONFIG = REPO_ROOT / 'docker/deploy/supervisord.conf'
STARTUP_ORDER = [
    'dbus',
    'keyring',
    'prepare',
    'config',
    'cbm',
    'opencode',
    'xpra',
    'dockerd',
    'prune',
    'project',
    'index',
]
STOP_ORDER = ['opencode', 'cbm', 'xpra', 'keyring', 'dbus', 'dockerd']
ONESHOTS = {'prepare', 'config', 'prune', 'project', 'index'}
OPTIONAL = ['config', 'cbm', 'xpra', 'dockerd', 'prune', 'project', 'index']

FAKE_SERVICE = """#!/usr/bin/env bash
name="$1"; state="$STATE_DIR"
echo "start $name" >> "$state/events"
mode="$(cat "$state/$name.mode" 2>/dev/null || echo ok)"
if [[ $mode == ignore-term ]]; then
  trap 'echo "stop $name" >> "$state/events"' TERM
else
  trap 'echo "stop $name" >> "$state/events"; rm -f "$state/$name.ready"; exit 0' TERM
fi
# The child leaves the wrapper's output, so the wrapper exits with the service.
if [[ $mode == with-child ]]; then sleep 1000 >/dev/null 2>&1 & echo $! > "$state/$name.child"; fi
echo "$name is up"
[[ $mode == never-ready ]] || touch "$state/$name.ready"
while true; do
  if [[ -f $state/$name.crash ]]; then
    rm -f "$state/$name.crash" "$state/$name.ready"; echo "crash $name" >> "$state/events"; exit 1
  fi
  if [[ -f $state/$name.wedge ]]; then
    rm -f "$state/$name.wedge" "$state/$name.ready"; echo "wedge $name" >> "$state/events"
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
lines="$(cat "$state/$name.lines" 2>/dev/null || echo 0)"
for ((i = 1; i <= lines; i++)); do echo "$name line $i"; done
sleep "$(cat "$state/$name.sleep" 2>/dev/null || echo 0)"
exit "$(cat "$state/$name.exit" 2>/dev/null || echo 0)"
"""
FAKE_HEALTH = """#!/usr/bin/env bash
[[ -f $STATE_DIR/$1.unhealthy ]] && cat "$STATE_DIR/$1.unhealthy"
[[ -f $STATE_DIR/$1.ready && ! -f $STATE_DIR/$1.unhealthy ]]
"""
HEALTH = REPO_ROOT / '.devcontainer/scripts/runtime-health.sh'

FAKE_BOOTSTRAP = """#!/usr/bin/env bash
echo "run bootstrap" >> "$STATE_DIR/events"
echo "bootstrap says hello"
echo "${ENABLE_FIREWALL-unset}" > "$STATE_DIR/bootstrap.firewall"
if [[ -f $STATE_DIR/bootstrap.spawn ]]; then sleep 1000 & echo $! > "$STATE_DIR/bootstrap.child"; fi
sleep "$(cat "$STATE_DIR/bootstrap.sleep" 2>/dev/null || echo 0)"
exit "$(cat "$STATE_DIR/bootstrap.exit" 2>/dev/null || echo 0)"
"""


def write_executable(path: Path, body: str) -> Path:
    path.write_text(body)
    path.chmod(0o755)
    return path


def build_config(
    root: Path,
    fake_service: Path,
    fake_oneshot: Path,
    config: Path = CONFIG,
    oneshots: set[str] = ONESHOTS,
) -> Path:
    """Rewrite a shipped config: same programs and flags, scripted commands, local paths."""
    parser = configparser.RawConfigParser()
    parser.read(config)
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
        fake = fake_oneshot if name in oneshots else fake_service
        program['command'] = f'{sys.executable} {SUPERVISOR} exec {name} {fake} {name}'
    path = root / 'supervisord.conf'
    with path.open('w') as handle:
        parser.write(handle)
    return path


class Supervision:
    """One supervised container start under test."""

    def __init__(
        self,
        root: Path,
        config: Path = CONFIG,
        oneshots: set[str] = ONESHOTS,
        mode: str = 'deploy',
        **settings: str,
    ) -> None:
        self.root = root
        self.state = root / 'state'
        self.state.mkdir(parents=True)
        fake_service = write_executable(root / 'fake-service', FAKE_SERVICE)
        fake_oneshot = write_executable(root / 'fake-oneshot', FAKE_ONESHOT)
        built = build_config(root, fake_service, fake_oneshot, config, oneshots)
        self.env = {
            'PATH': os.environ['PATH'],
            'STATE_DIR': str(self.state),
            'AGENTDEV_RUNTIME_MODE': mode,
            'AGENTDEV_RUN_DIR': str(root / 'run'),
            'AGENTDEV_SUPERVISOR_CONFIG': str(built),
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
            'AGENTDEV_HOME': str(root / 'home'),
            'XPRA_PASSWORD': 'supervision-test',
            **settings,
        }
        self.process: subprocess.Popen[str] | None = None
        self._output: str | None = None

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
        return self.runtime().get('state') == 'ready'

    def health(self, check: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [HEALTH, check], env=self.env, text=True, capture_output=True, timeout=30
        )

    def runtime(self) -> dict:
        try:
            return json.loads((self.root / 'run/state.json').read_text())
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def latched(self) -> str | None:
        state = self.runtime()
        return state.get('latched') if state.get('state') == 'failed' else None

    def degraded(self) -> bool:
        return self.runtime().get('state') == 'degraded'

    def status(self, name: str) -> str:
        return self.runtime().get('components', {}).get(name, {}).get('status', '')

    @property
    def record_path(self) -> Path:
        return self.root / 'home/.local/state/agentdev/last-failure.json'

    def record(self) -> dict:
        return json.loads(self.record_path.read_text())

    def retry(self, *component: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, SUPERVISOR, 'retry', *component],
            env=self.env,
            text=True,
            capture_output=True,
            timeout=60,
        )

    def alive(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def controller_pid(self) -> int:
        for proc in Path('/proc').iterdir():
            try:
                cmdline = (proc / 'cmdline').read_bytes().split(b'\0')
                environ = (proc / 'environ').read_bytes()
            except OSError:
                continue
            if cmdline[-2:] == [b'control', b''] and f'STATE_DIR={self.state}'.encode() in environ:
                return int(proc.name)
        pytest.fail('no controller process found')

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
        if self._output is None:
            self._output = self.process.stdout.read()
        return self._output

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

    def factory(**settings) -> Supervision:
        box = Supervision(TMP_ROOT / f'sv-{uuid4().hex[:8]}', **settings)
        created.append(box)
        return box

    yield factory
    for box in created:
        box.terminate()
        shutil.rmtree(box.root, ignore_errors=True)


def started(events: list[str]) -> list[str]:
    """Return what started, in order; OpenCode and Xpra launch together, so they may swap."""
    runs = [e.split()[1] for e in events if e.split()[0] in {'start', 'run'}]
    for index in range(len(runs) - 1):
        if runs[index : index + 2] == ['xpra', 'opencode']:
            runs[index : index + 2] = ['opencode', 'xpra']
    return runs


def test_starts_services_in_dependency_order_then_publishes_readiness(make):
    box = make()
    box.start()
    box.wait_for(box.ready)
    assert started(box.events()) == ['bootstrap', *STARTUP_ORDER]


def test_disabled_xpra_is_neither_started_nor_required(make):
    box = make(AGENTDEV_SKIP_XPRA='1')
    del box.env['XPRA_PASSWORD']
    box.start()
    box.wait_for(box.ready)
    assert 'xpra' not in started(box.events())


def stays_latched(box: Supervision, component: str, seconds: float = 1.5) -> None:
    """Assert the runtime latched on ``component`` and nothing reruns while it stays latched."""
    box.wait_for(lambda: box.latched() == component)
    before = box.events()
    time.sleep(seconds)
    assert box.alive(), box.output()
    assert box.events() == before
    assert not box.ready()


@pytest.mark.parametrize('password', [None, ''])
def test_enabled_xpra_without_a_password_latches_before_the_bootstrap(make, password):
    box = make()
    del box.env['XPRA_PASSWORD']
    if password is not None:
        box.env['XPRA_PASSWORD'] = password
    box.start()
    stays_latched(box, 'configuration')
    assert box.events() == []
    reason = box.runtime()['components']['configuration']['reason']
    assert 'XPRA_PASSWORD must be set' in reason and 'AGENTDEV_SKIP_XPRA=1' in reason
    assert not box.record_path.exists(), 'the home volume is not known usable yet'
    box.terminate()
    assert box.process is not None and box.process.returncode == 0


@pytest.mark.parametrize('failure', ['exit', 'timeout'])
def test_preparation_failure_latches_with_opencode_unavailable(make, failure):
    box = make()
    if failure == 'exit':
        box.set('prepare', 'exit', '7')
    else:
        box.set('prepare', 'sleep', '30')
    box.start()
    stays_latched(box, 'prepare')
    assert 'opencode' not in started(box.events())
    record = box.record()
    assert record['component'] == 'prepare' and 'prepare' in record['reason']
    assert record['startup_id'] == box.runtime()['startup_id']
    assert record['command'][-2:] == [str(box.root / 'fake-oneshot'), 'prepare']
    assert record['exit_status'] == (7 if failure == 'exit' else 143)
    assert record['time'].endswith('+00:00')


def test_a_latched_preparation_resumes_on_retry_in_the_same_process(make):
    box = make()
    box.set('prepare', 'exit', '7')
    box.start()
    stays_latched(box, 'prepare', seconds=0.5)
    first = box.record_path.read_bytes()

    again = box.retry()
    assert again.returncode == 1 and 'failed' in again.stdout
    second = box.record()
    assert second['exit_status'] == 7 and box.record_path.read_bytes() != first
    assert started(box.events()).count('prepare') == 2

    (box.state / 'prepare.exit').unlink()
    resumed = box.retry()
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr
    box.wait_for(box.ready)
    runs = started(box.events())
    assert runs.count('bootstrap') == 1 and runs.count('keyring') == 1
    assert runs[runs.index('prepare') + 2 :] == STARTUP_ORDER[STARTUP_ORDER.index('prepare') :]
    assert box.record() == second, 'success leaves the last failure in place'


def test_the_failure_record_keeps_the_last_200_output_lines(make):
    box = make()
    box.set('prepare', 'lines', '300')
    box.set('prepare', 'exit', '3')
    box.start()
    box.wait_for(lambda: box.latched() == 'prepare')
    output = box.record()['output']
    assert len(output) == 200
    assert output[0] == 'prepare line 101' and output[-1] == 'prepare line 300'


@pytest.mark.skipif(os.geteuid() != 0, reason='changing ownership requires root')
def test_the_failure_record_leaves_a_fresh_home_owned_by_the_runtime_user(make):
    account = pwd.getpwnam('nobody')
    box = make(AGENTDEV_USER='nobody')
    (box.root / 'home').mkdir()
    box.set('prepare', 'exit', '7')
    box.start()
    box.wait_for(lambda: box.latched() == 'prepare')
    box.wait_for(box.record_path.exists)
    for directory in ('.local', '.local/state', '.local/state/agentdev'):
        info = (box.root / 'home' / directory).stat()
        assert (info.st_uid, info.st_gid) == (account.pw_uid, account.pw_gid), directory


def test_a_new_start_keeps_the_previous_failure_record(make):
    box = make()
    box.set('prepare', 'exit', '7')
    box.start()
    box.wait_for(lambda: box.latched() == 'prepare')
    recorded = box.record_path.read_bytes()
    box.terminate()
    (box.state / 'prepare.exit').unlink()
    box.start()
    box.wait_for(box.ready)
    assert box.record_path.read_bytes() == recorded


def test_bootstrap_failure_latches_before_any_service_and_retries(make):
    box = make()
    box.set('bootstrap', 'exit', '1')
    box.start()
    stays_latched(box, 'bootstrap')
    assert started(box.events()) == ['bootstrap']
    assert not box.record_path.exists()

    (box.state / 'bootstrap.exit').unlink()
    resumed = box.retry()
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr
    assert box.ready()
    assert started(box.events()) == ['bootstrap', 'bootstrap', *STARTUP_ORDER]
    box.terminate()
    printed = [json.loads(line) for line in box.output().splitlines() if line.startswith('{')]
    assert printed[0]['component'] == 'bootstrap' and printed[0]['exit_status'] == 1
    assert printed[0]['output'] == ['bootstrap says hello']
    assert set(printed[0]) >= {'startup_id', 'command', 'time'}


def test_a_controller_crash_exits_pid_1_nonzero(make):
    box = make()
    box.start()
    box.wait_for(box.ready)
    os.kill(box.controller_pid(), signal.SIGKILL)
    assert box.wait_exit() == 1
    assert 'controller exited' in box.output()


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


def test_exhausted_recovery_after_running_latches_and_stops_opencode(make):
    box = make()
    box.start()
    box.wait_for(box.ready)
    box.set('keyring', 'mode', 'crash-always')
    box.set('keyring', 'crash')
    stays_latched(box, 'keyring')
    assert started(box.events()).count('keyring') == 4
    assert 'stop opencode' in box.events()
    assert 'keyring exhausted 3 recovery attempts' in box.record()['reason']


def test_an_unready_opencode_that_exhausts_its_budget_is_stopped(make):
    box = make(AGENTDEV_RECOVERY_ATTEMPTS='1')
    box.start()
    box.wait_for(box.ready)
    box.set('opencode', 'unhealthy')
    stays_latched(box, 'opencode')
    opencode = [e for e in box.events() if e.endswith(' opencode')]
    assert opencode[-1] == 'stop opencode', opencode


def test_startup_failure_exhausts_the_same_budget(make):
    box = make()
    box.set('keyring', 'mode', 'never-ready')
    box.start()
    stays_latched(box, 'keyring')
    assert started(box.events()).count('keyring') == 4
    assert 'opencode' not in started(box.events())


def test_hung_service_is_not_treated_as_healthy(make):
    box = make(AGENTDEV_RECOVERY_ATTEMPTS='1')
    box.start()
    box.wait_for(box.ready)
    box.set('dbus', 'unhealthy')
    box.wait_for(lambda: box.latched() == 'dbus')
    assert 'dbus exhausted' in box.record()['reason']


def fail_component(box: Supervision, name: str) -> None:
    if name in ONESHOTS:
        box.set(name, 'exit', '1')
    else:
        box.set(name, 'mode', 'never-ready')


@pytest.mark.parametrize('name', OPTIONAL)
def test_an_optional_failure_degrades_while_opencode_serves(make, name):
    box = make(AGENTDEV_RECOVERY_ATTEMPTS='1')
    fail_component(box, name)
    box.start()
    box.wait_for(box.degraded)
    assert box.alive()
    assert (box.state / 'opencode.ready').exists() and box.status('opencode') == 'ready'
    assert box.status(name) == 'failed'
    assert box.record()['component'] == name
    assert not box.ready()


def test_a_failed_optional_dependency_blocks_its_dependents_until_retried(make):
    box = make(AGENTDEV_RECOVERY_ATTEMPTS='1')
    box.set('dockerd', 'mode', 'never-ready')
    box.start()
    box.wait_for(box.degraded)
    assert box.status('prune') == 'blocked'
    assert 'prune' not in started(box.events())

    (box.state / 'dockerd.mode').unlink()
    resumed = box.retry('dockerd')
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr
    box.wait_for(box.ready)
    assert started(box.events()).count('prune') == 1


def test_opencode_does_not_wait_for_xpra(make):
    box = make(AGENTDEV_RECOVERY_ATTEMPTS='2', AGENTDEV_SERVICE_START_TIMEOUT='1')
    box.set('xpra', 'mode', 'never-ready')
    box.start()
    box.wait_for(lambda: box.status('opencode') == 'ready')
    assert box.status('xpra') in {'starting', 'recovering'}
    box.wait_for(box.degraded)
    assert box.status('opencode') == 'ready'


@pytest.mark.parametrize('name', ['config', 'xpra', 'project'])
def test_strict_startup_latches_on_an_optional_failure(make, name):
    box = make(AGENTDEV_RECOVERY_ATTEMPTS='1', AGENTDEV_STRICT_STARTUP='true')
    fail_component(box, name)
    box.start()
    stays_latched(box, name)
    if name == 'config':
        assert 'opencode' not in started(box.events())
    else:
        assert 'stop opencode' in box.events()


def test_retrying_one_optional_component_restores_readiness(make):
    box = make()
    box.set('project', 'exit', '1')
    box.start()
    box.wait_for(box.degraded)
    assert box.retry('opencode').returncode == 1, 'only a failed component can be retried'

    (box.state / 'project.exit').unlink()
    resumed = box.retry('project')
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr
    assert 'ready' in resumed.stdout
    box.wait_for(box.ready)
    assert started(box.events()).count('project') == 2
    assert started(box.events()).count('prepare') == 1
    assert started(box.events()).count('opencode') == 1, 'project is not read by OpenCode'


def test_retrying_config_restarts_the_opencode_that_reads_it(make):
    box = make()
    box.set('config', 'exit', '1')
    box.start()
    box.wait_for(box.degraded)
    assert started(box.events()).count('opencode') == 1

    (box.state / 'config.exit').unlink()
    resumed = box.retry('config')
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr
    box.wait_for(box.ready)
    assert started(box.events()).count('opencode') == 2


def test_a_retry_whose_client_restart_fails_reports_failure(make):
    box = make(AGENTDEV_RECOVERY_ATTEMPTS='1')
    box.set('config', 'exit', '1')
    box.start()
    box.wait_for(box.degraded)
    (box.state / 'config.exit').unlink()
    box.set('opencode', 'mode', 'never-ready')

    resumed = box.retry('config')
    assert resumed.returncode == 1, resumed.stdout + resumed.stderr
    box.wait_for(lambda: box.latched() == 'opencode')


def test_core_services_recover_while_optional_work_runs(make):
    box = make(AGENTDEV_PREPARE_TIMEOUT='60')
    box.set('project', 'sleep', '30')
    box.start()
    box.wait_for(lambda: box.status('opencode') == 'ready' and box.status('project') == 'starting')
    box.set('opencode', 'crash')
    box.wait_for(lambda: started(box.events()).count('opencode') == 2)
    box.wait_for(lambda: box.status('opencode') == 'ready')
    assert box.status('project') == 'starting', 'recovery did not wait for the phase'


def test_a_failure_record_holds_only_the_current_attempts_output(make):
    box = make(AGENTDEV_RECOVERY_ATTEMPTS='1')
    stale = {'command': ['old'], 'exit_status': 9, 'output': ['stale'], 'started': 1.0}
    (box.root / 'run/output').mkdir(parents=True)
    (box.root / 'run/output/xpra.json').write_text(json.dumps(stale))
    box.set('xpra', 'mode', 'never-ready')
    box.start()
    box.wait_for(box.degraded)
    record = box.record()
    assert record['component'] == 'xpra' and record['exit_status'] is None
    assert record['output'] == ['xpra is up'], 'the live tail of the attempt that failed'


def test_dependency_outage_recovers_clients_outside_their_budget(make):
    box = make(AGENTDEV_RECOVERY_ATTEMPTS='1')
    box.set('keyring', 'needs', 'dbus')
    box.start()
    box.wait_for(box.ready)
    box.set('dbus', 'crash')
    box.wait_for(lambda: started(box.events()).count('keyring') == 2 and box.ready())
    assert 'lost keyring' in box.events()
    assert box.process is not None and box.process.poll() is None


def test_a_client_failure_escalates_to_its_failing_dependency(make):
    # The debounce cannot confirm a wedged D-Bus, so only escalation recovers it.
    box = make(AGENTDEV_RECOVERY_ATTEMPTS='1', AGENTDEV_PROBE_FAILURES='1000')
    box.set('keyring', 'needs', 'dbus')
    box.start()
    box.wait_for(box.ready)
    box.set('dbus', 'wedge')
    box.wait_for(lambda: box.latched() is not None or started(box.events()).count('dbus') == 2)
    box.wait_for(lambda: box.latched() is not None or box.ready())
    assert box.latched() is None, box.record()['reason']
    runs = started(box.events())
    assert runs.count('dbus') == 2 and runs.count('keyring') == 2, runs
    assert 'wedge dbus' in box.events() and 'lost keyring' in box.events()


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
    deadline = time.monotonic() + 5
    while running(child) and time.monotonic() < deadline:
        time.sleep(0.05)
    assert not running(child)


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
    assert set(programs) == set(STARTUP_ORDER) | {'remote-control'}
    for name, program in programs.items():
        assert program['autostart'] == 'false' and program['startretries'] == '0'
        assert program['stdout_logfile'] == '/dev/stdout'
        assert program['killasgroup'] == 'true'
        assert ('user' in program) == (name != 'dockerd')
        wrapper = '/opt/agentdev-runtime/runtime-supervisor.py exec'
        assert program['command'].startswith(f'{wrapper} {name} /'), name
    priorities = sorted(STOP_ORDER, key=lambda n: -int(programs[n]['priority']))
    assert priorities == STOP_ORDER
    assert parser['eventlistener:controller']['priority'] == '999'


def test_every_supervised_service_has_a_real_probe():
    health = (REPO_ROOT / '.devcontainer/scripts/runtime-health.sh').read_text()
    probes = health.split('case "$service" in', 2)[2]
    for name in [*STOP_ORDER, 'remote-control']:
        assert f'\n  {name})' in probes or f'\n  {name} |' in probes, name


def test_recovery_kills_what_a_crashed_service_left_in_its_group(make):
    box = make()
    box.set('xpra', 'mode', 'with-child')
    box.start()
    box.wait_for(box.ready)
    orphan = int((box.state / 'xpra.child').read_text())
    box.set('xpra', 'crash')
    box.wait_for(lambda: started(box.events()).count('xpra') == 2 and box.ready())
    box.wait_for(lambda: not running(orphan), timeout=5)


def test_health_needs_a_live_controller_reporting_ready(make):
    box = make()
    box.start()
    box.wait_for(box.ready)
    assert box.health('ready').returncode == 0
    box.set('opencode', 'unhealthy')
    assert box.health('ready').returncode == 1, 'the core probes run at every check'
    (box.state / 'opencode.unhealthy').unlink()

    controller = box.controller_pid()
    os.kill(controller, signal.SIGSTOP)
    try:
        stopped = time.monotonic()
        while box.health('ready').returncode == 0:
            assert time.monotonic() - stopped < 3 * 0.2 + 1, 'a stale heartbeat still passed'
            time.sleep(0.05)
        assert 'stale' in box.health('ready').stdout
    finally:
        os.kill(controller, signal.SIGCONT)
    box.wait_for(lambda: box.health('ready').returncode == 0)

    os.kill(controller, signal.SIGKILL)
    box.wait_exit()
    assert box.health('ready').returncode == 1


def test_status_names_each_failure_and_its_retry_command(make):
    box = make()
    box.set('project', 'exit', '4')
    box.start()
    box.wait_for(box.degraded)
    shown = box.health('status')
    assert shown.returncode == 1
    lines = shown.stdout
    assert 'runtime state: degraded' in lines
    assert 'project: failed (project failed (exit status 4))' in lines
    assert 'runtime-supervisor.py retry project' in lines
    record = box.record()
    assert f'last failure: project, exit status 4, at {record["time"]}' in lines


def test_a_failing_probe_logs_its_output(make):
    box = make()
    box.start()
    box.wait_for(box.ready)
    box.set('xpra', 'unhealthy', 'the display is gone')
    box.wait_for(lambda: not box.ready())
    (box.state / 'xpra.unhealthy').unlink()
    box.wait_for(box.ready)
    box.terminate()
    assert 'xpra: probe exited 1: the display is gone' in box.output()


@pytest.mark.parametrize('spelling', ['false', 'FALSE', '0', 'no', 'Off', ''])
def test_a_false_spelling_of_skip_xpra_starts_xpra(make, spelling):
    box = make(AGENTDEV_SKIP_XPRA=spelling)
    box.start()
    box.wait_for(box.ready)
    assert 'xpra' in started(box.events())


@pytest.mark.parametrize('spelling', ['1', 'true', 'Yes', 'ON'])
def test_a_true_spelling_of_skip_xpra_skips_it(make, spelling):
    box = make(AGENTDEV_SKIP_XPRA=spelling)
    del box.env['XPRA_PASSWORD']
    box.start()
    box.wait_for(box.ready)
    assert 'xpra' not in started(box.events())


@pytest.mark.parametrize(
    ('name', 'value'),
    [
        ('AGENTDEV_SKIP_XPRA', 'maybe'),
        ('AGENTDEV_STRICT_STARTUP', 'enabled'),
        *[
            (name, value)
            for name in (
                'AGENTDEV_RECOVERY_ATTEMPTS',
                'AGENTDEV_PROBE_FAILURES',
                'AGENTDEV_STOP_TIMEOUT',
                'AGENTDEV_RECOVERY_BACKOFF',
                'AGENTDEV_HEALTHY_RESET',
                'AGENTDEV_SERVICE_START_TIMEOUT',
                'AGENTDEV_BOOTSTRAP_TIMEOUT',
                'AGENTDEV_PREPARE_TIMEOUT',
                'AGENTDEV_HEALTH_INTERVAL',
            )
            for value in ('0', '-1', 'soon')
        ],
        ('AGENTDEV_RECOVERY_ATTEMPTS', '1.5'),
    ],
)
def test_a_malformed_setting_latches_a_configuration_failure(make, name, value):
    box = make(**{name: value})
    box.start()
    box.wait_for(lambda: box.latched() == 'configuration')
    assert box.events() == [], 'nothing starts on a malformed setting'
    reason = box.runtime()['components']['configuration']['reason']
    assert name in reason and repr(value) in reason


def test_the_bootstrap_has_its_own_deadline(make):
    box = make(AGENTDEV_BOOTSTRAP_TIMEOUT='1', AGENTDEV_PREPARE_TIMEOUT='600')
    box.set('bootstrap', 'sleep', '30')
    box.start()
    box.wait_for(lambda: box.latched() == 'bootstrap', timeout=10)
    reason = box.runtime()['components']['bootstrap']['reason']
    assert reason == 'bootstrap did not finish within 1s'


def test_a_timed_out_bootstrap_takes_its_children_with_it(make):
    box = make(AGENTDEV_BOOTSTRAP_TIMEOUT='1')
    box.set('bootstrap', 'spawn')
    box.set('bootstrap', 'sleep', '30')
    box.start()
    box.wait_for(lambda: box.latched() == 'bootstrap', timeout=10)
    child = int((box.state / 'bootstrap.child').read_text())
    box.wait_for(lambda: not running(child), timeout=5)


def running(pid: int) -> bool:
    """Return whether ``pid`` is alive, counting a zombie awaiting its reaper as gone."""
    try:
        stat_line = Path(f'/proc/{pid}/stat').read_text()
    except FileNotFoundError:
        return False
    return stat_line.rsplit(')', 1)[1].split()[0] != 'Z'


@pytest.mark.parametrize(('spelling', 'passed'), [('yes', 'true'), ('ON', 'true'), ('0', 'false')])
def test_the_bootstrap_sees_a_normalized_firewall_switch(make, spelling, passed):
    box = make(ENABLE_FIREWALL=spelling)
    box.start()
    box.wait_for(box.ready)
    assert (box.state / 'bootstrap.firewall').read_text().strip() == passed


def test_a_malformed_firewall_switch_latches_before_the_bootstrap(make):
    box = make(ENABLE_FIREWALL='enabled')
    box.start()
    box.wait_for(lambda: box.latched() == 'configuration')
    assert box.events() == []
    assert 'ENABLE_FIREWALL' in box.runtime()['components']['configuration']['reason']


def test_remote_control_is_left_out_without_a_mode(make):
    box = make(AGENTDEV_CLAUDE_RC_MODE='')
    box.start()
    box.wait_for(box.ready)
    assert 'remote-control' not in started(box.events())
    assert 'remote-control' not in box.runtime()['components']


@pytest.mark.parametrize('mode', ['session', 'server'])
def test_a_remote_control_mode_starts_it_after_prepare(make, mode):
    box = make(AGENTDEV_CLAUDE_RC_MODE=mode)
    box.start()
    box.wait_for(box.ready)
    runs = started(box.events())
    assert runs.index('prepare') < runs.index('remote-control')
    assert box.status('remote-control') == 'ready'


@pytest.mark.parametrize(
    'settings, variable',
    [
        ({'AGENTDEV_CLAUDE_RC_MODE': 'sever'}, 'AGENTDEV_CLAUDE_RC_MODE'),
        (
            {'AGENTDEV_CLAUDE_RC_MODE': 'server', 'AGENTDEV_CLAUDE_RC_SPAWN': 'tree'},
            'AGENTDEV_CLAUDE_RC_SPAWN',
        ),
    ],
)
def test_an_unrecognized_remote_control_setting_latches_before_the_bootstrap(
    make, settings, variable
):
    box = make(**settings)
    box.start()
    stays_latched(box, 'configuration')
    assert box.events() == []
    assert variable in box.runtime()['components']['configuration']['reason']


def test_a_session_mode_ignores_the_spawn_setting(make):
    box = make(AGENTDEV_CLAUDE_RC_MODE='session', AGENTDEV_CLAUDE_RC_SPAWN='tree')
    box.start()
    box.wait_for(box.ready)


def test_a_failing_remote_control_degrades_while_opencode_serves(make):
    box = make(AGENTDEV_CLAUDE_RC_MODE='server', AGENTDEV_RECOVERY_ATTEMPTS='1')
    box.set('remote-control', 'mode', 'never-ready')
    box.start()
    box.wait_for(box.degraded)
    assert box.status('remote-control') == 'failed'
    assert box.status('opencode') == 'ready'


def test_strict_startup_latches_on_a_failing_remote_control(make):
    box = make(
        AGENTDEV_CLAUDE_RC_MODE='server',
        AGENTDEV_RECOVERY_ATTEMPTS='1',
        AGENTDEV_STRICT_STARTUP='true',
    )
    box.set('remote-control', 'mode', 'never-ready')
    box.start()
    stays_latched(box, 'remote-control')


def test_status_shows_what_remote_control_is_doing(make, tmp_path):
    box = make(AGENTDEV_CLAUDE_RC_MODE='server', XDG_RUNTIME_DIR=str(tmp_path))
    box.start()
    box.wait_for(box.ready)
    assert 'remote-control: not started' in box.health('status').stdout
    (tmp_path / 'remote-control.status').write_text('waiting for a claude.ai login\n')
    shown = box.health('status')
    assert shown.returncode == 0
    assert '  remote-control: waiting for a claude.ai login' in shown.stdout


def test_status_names_no_remote_control_without_a_mode(make, tmp_path):
    box = make(XDG_RUNTIME_DIR=str(tmp_path))
    box.start()
    box.wait_for(box.ready)
    (tmp_path / 'remote-control.status').write_text('waiting for a claude.ai login\n')
    assert 'remote-control' not in box.health('status').stdout
