#!/usr/bin/env python3
"""
PID 1 and service controller for the standalone agent-opencode runtime.

``run`` is the container entrypoint: it runs the root bootstrap, then supervisord in this same
process, and exits nonzero when the controller recorded a terminal failure. ``control`` is the
supervisord event listener that starts services in dependency order, gates them on readiness,
and recovers failures within a bounded budget. Spec: standalone-opencode-runtime.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import queue
import signal
import subprocess
import sys
import threading
import time
from typing import NoReturn
import xmlrpc.client

SCRIPT_DIR = Path(__file__).resolve().parent
RUNNING_STATES = {'RUNNING'}
DONE_STATES = {'EXITED', 'FATAL', 'STOPPED', 'BACKOFF', 'UNKNOWN'}
SUPERVISOR_FAULT_NOT_RUNNING = 70
SUPERVISOR_FAULT_ALREADY_STARTED = 60


def log(message: str) -> None:
    """Write to stderr: in an event listener, stdout carries the protocol."""
    print(f'runtime-supervisor: {message}', file=sys.stderr, flush=True)


def env_float(name: str, default: float) -> float:
    """Read a numeric setting, failing loudly on a malformed value."""
    raw = os.environ.get(name, '')
    try:
        return float(raw) if raw else default
    except ValueError as error:
        raise SystemExit(f'runtime-supervisor: {name} must be a number, got {raw!r}') from error


@dataclass(frozen=True)
class Settings:
    """Deadlines and budgets, overridable through documented AGENTDEV_* variables."""

    attempts: int = field(default_factory=lambda: int(env_float('AGENTDEV_RECOVERY_ATTEMPTS', 3)))
    backoff: float = field(default_factory=lambda: env_float('AGENTDEV_RECOVERY_BACKOFF', 1))
    healthy_reset: float = field(default_factory=lambda: env_float('AGENTDEV_HEALTHY_RESET', 60))
    start_timeout: float = field(
        default_factory=lambda: env_float('AGENTDEV_SERVICE_START_TIMEOUT', 60)
    )
    prepare_timeout: float = field(
        default_factory=lambda: env_float('AGENTDEV_PREPARE_TIMEOUT', 1800)
    )
    interval: float = field(default_factory=lambda: env_float('AGENTDEV_HEALTH_INTERVAL', 2))
    probe_failures: int = field(
        default_factory=lambda: int(env_float('AGENTDEV_PROBE_FAILURES', 2))
    )
    run_dir: Path = field(
        default_factory=lambda: Path(os.environ.get('AGENTDEV_RUN_DIR', '/run/agentdev'))
    )
    health_command: str = field(
        default_factory=lambda: os.environ.get(
            'AGENTDEV_HEALTH_COMMAND', str(SCRIPT_DIR / 'runtime-health.sh')
        )
    )
    skip_xpra: bool = field(default_factory=lambda: bool(os.environ.get('AGENTDEV_SKIP_XPRA')))

    @property
    def ready_file(self) -> Path:
        return self.run_dir / 'ready'

    @property
    def failure_file(self) -> Path:
        return self.run_dir / 'failed'


@dataclass(frozen=True)
class Service:
    """One supervisord program and its place in the dependency graph."""

    name: str
    after: tuple[str, ...] = ()
    oneshot: bool = False
    # Clients restarted, outside their own budget, once this service recovers.
    refresh: tuple[str, ...] = ()


SERVICES = (
    Service('dockerd'),
    Service('dbus', refresh=('keyring', 'xpra')),
    Service('keyring', after=('dbus',)),
    Service('prepare', after=('dockerd', 'keyring'), oneshot=True),
    Service('cbm', after=('prepare',), refresh=('opencode',)),
    Service('index', after=('cbm',), oneshot=True),
    Service('xpra', after=('keyring', 'index')),
    Service('opencode', after=('dockerd', 'keyring', 'cbm', 'index', 'xpra')),
)


class TerminalFailure(Exception):
    """Recovery is impossible; the container must stop and exit nonzero."""


@dataclass
class Health:
    attempts: int = 0
    probe_failures: int = 0
    healthy_since: float = 0.0


class Controller:
    """Sequence startup, watch readiness, and recover services within their budgets."""

    def __init__(self, settings: Settings, rpc, wakeups: queue.Queue[str]) -> None:
        self.settings = settings
        self.rpc = rpc
        self.wakeups = wakeups
        self.services = [s for s in SERVICES if not (s.name == 'xpra' and settings.skip_xpra)]
        self.enabled = {s.name for s in self.services}
        self.health = {s.name: Health() for s in self.services}
        # Each program leads its own process group, so its first pid is the group id.
        self.groups: dict[str, int] = {}

    # --- supervisord access -------------------------------------------------------------
    def state(self, name: str) -> dict:
        return self.rpc.supervisor.getProcessInfo(name)

    def start(self, name: str) -> None:
        try:
            self.rpc.supervisor.startProcess(name, False)
        except xmlrpc.client.Fault as fault:
            if fault.faultCode != SUPERVISOR_FAULT_ALREADY_STARTED:
                raise

    def stop(self, name: str) -> None:
        try:
            self.rpc.supervisor.stopProcess(name, True)
        except xmlrpc.client.Fault as fault:
            if fault.faultCode != SUPERVISOR_FAULT_NOT_RUNNING:
                raise

    def restart(self, name: str) -> None:
        """Stop a service and anything left of its process group, then start it again."""
        self.stop(name)
        group = self.groups.pop(name, 0)
        if group:
            # supervisord signals a group only on an orderly stop; a crashed service
            # can leave children, such as Xpra's X server, holding its resources.
            try:
                os.killpg(group, signal.SIGKILL)
                log(f'{name}: killed processes left in group {group}')
            except ProcessLookupError:
                log(f'{name}: process group {group} already gone')
        self.start(name)

    def shutting_down(self) -> bool:
        return self.rpc.supervisor.getState()['statename'] in {'SHUTDOWN', 'RESTARTING'}

    # --- readiness ----------------------------------------------------------------------
    def probe(self, name: str) -> bool:
        try:
            result = subprocess.run(
                [self.settings.health_command, name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=max(self.settings.interval * 5, 10),
            )
        except subprocess.TimeoutExpired:
            log(f'{name}: readiness probe timed out')
            return False
        return result.returncode == 0

    def healthy(self, name: str) -> bool:
        return self.state(name)['statename'] in RUNNING_STATES and self.probe(name)

    def pause(self, seconds: float) -> None:
        """Sleep, but wake early on a process-state event."""
        try:
            self.wakeups.get(timeout=seconds)
        except queue.Empty:
            return

    def wait_ready(self, name: str) -> bool:
        deadline = time.monotonic() + self.settings.start_timeout
        while time.monotonic() < deadline:
            info = self.state(name)
            if info['statename'] in DONE_STATES:
                log(f'{name}: exited during startup ({info["statename"]})')
                return False
            if info['statename'] in RUNNING_STATES:
                self.groups[name] = info['pid']
                if self.probe(name):
                    return True
            self.pause(min(self.settings.interval, 0.5))
        log(f'{name}: not ready within {self.settings.start_timeout:g}s')
        return False

    def run_oneshot(self, name: str) -> None:
        timeout = self.settings.prepare_timeout
        self.start(name)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            info = self.state(name)
            if info['statename'] in DONE_STATES:
                if info['statename'] == 'EXITED' and info['exitstatus'] == 0:
                    log(f'{name}: completed')
                    return
                raise TerminalFailure(f'{name} failed (exit status {info["exitstatus"]})')
            self.pause(0.5)
        self.stop(name)
        raise TerminalFailure(f'{name} did not finish within {timeout:g}s')

    def publish(self, ready: bool) -> None:
        if ready:
            self.settings.ready_file.write_text('ready\n')
        else:
            self.settings.ready_file.unlink(missing_ok=True)

    # --- recovery -----------------------------------------------------------------------
    def dependents(self, name: str) -> list[str]:
        found: list[str] = []
        for service in self.services:
            if service.oneshot or service.name in found:
                continue
            if name in service.after or any(dep in found for dep in service.after):
                found.append(service.name)
        return found

    def restart_until_ready(self, name: str) -> None:
        health = self.health[name]
        while True:
            health.attempts += 1
            if health.attempts > self.settings.attempts:
                raise TerminalFailure(
                    f'{name} exhausted {self.settings.attempts} recovery attempts'
                )
            delay = self.settings.backoff * 2 ** (health.attempts - 1)
            log(
                f'{name}: recovery attempt {health.attempts}/{self.settings.attempts} '
                f'in {delay:g}s'
            )
            time.sleep(delay)
            self.restart(name)
            if self.wait_ready(name):
                break
        health.probe_failures = 0
        health.healthy_since = time.monotonic()
        log(f'{name}: recovered')

    def recover(self, name: str) -> None:
        self.publish(False)
        paused = self.dependents(name)
        self.restart_until_ready(name)
        service = next(s for s in self.services if s.name == name)
        for client in service.refresh:
            if client not in self.enabled:
                continue
            log(f'{client}: reconnecting after {name} recovered')
            self.restart(client)
            if not self.wait_ready(client):
                self.restart_until_ready(client)
            self.health[client].healthy_since = time.monotonic()
        for dependent in paused:
            if dependent not in service.refresh and not self.healthy(dependent):
                self.restart_until_ready(dependent)
        self.publish(True)

    # --- lifecycle ----------------------------------------------------------------------
    def startup(self) -> None:
        for service in self.services:
            if service.oneshot:
                self.run_oneshot(service.name)
                continue
            log(f'{service.name}: starting')
            self.start(service.name)
            if not self.wait_ready(service.name):
                self.restart_until_ready(service.name)
            self.health[service.name].healthy_since = time.monotonic()
            log(f'{service.name}: ready')
        self.publish(True)
        log('all required services are ready')

    def check_once(self) -> None:
        now = time.monotonic()
        for service in self.services:
            if service.oneshot:
                continue
            name, health = service.name, self.health[service.name]
            if self.state(name)['statename'] not in RUNNING_STATES:
                failed = 'exited'
            elif not self.probe(name):
                health.probe_failures += 1
                if health.probe_failures < self.settings.probe_failures:
                    continue
                failed = 'failed its readiness probe'
            else:
                health.probe_failures = 0
                if health.attempts and now - health.healthy_since >= self.settings.healthy_reset:
                    log(f'{name}: healthy for {self.settings.healthy_reset:g}s; budget reset')
                    health.attempts = 0
                continue
            if self.shutting_down():
                return
            log(f'{name}: {failed}')
            self.recover(name)
            return

    def run(self) -> None:
        self.startup()
        while True:
            self.pause(self.settings.interval)
            if self.shutting_down():
                return
            self.check_once()


def fail_terminally(settings: Settings, rpc, reason: str) -> None:
    log(f'terminal failure: {reason}')
    settings.failure_file.write_text(reason + '\n')
    settings.ready_file.unlink(missing_ok=True)
    rpc.supervisor.shutdown()


def control() -> int:
    """Event-listener entry point; a worker thread runs the controller."""
    from supervisor import childutils

    settings = Settings()
    wakeups: queue.Queue[str] = queue.Queue()

    def work() -> None:
        rpc = childutils.getRPCInterface(os.environ)
        try:
            Controller(settings, rpc, wakeups).run()
        except TerminalFailure as failure:
            fail_terminally(settings, rpc, str(failure))
        except Exception as error:  # noqa: BLE001 — any controller crash ends the container.
            fail_terminally(settings, rpc, f'controller error: {error!r}')

    threading.Thread(target=work, name='controller', daemon=True).start()
    while True:
        headers, _ = childutils.listener.wait(sys.stdin, sys.stdout)
        wakeups.put(headers['eventname'])
        childutils.listener.ok(sys.stdout)


def run() -> int:
    """Container entrypoint: bootstrap as root, then supervisord in this process."""
    settings = Settings()
    settings.run_dir.mkdir(parents=True, exist_ok=True)
    settings.failure_file.unlink(missing_ok=True)
    settings.ready_file.unlink(missing_ok=True)
    bootstrap = os.environ.get(
        'AGENTDEV_BOOTSTRAP_COMMAND', str(SCRIPT_DIR / 'runtime-bootstrap.sh')
    )
    child: subprocess.Popen[bytes] | None = None

    def interrupt(signum: int, _frame) -> NoReturn:
        if child is not None and child.poll() is None:
            child.terminate()
        raise SystemExit(128 + signum)

    # As PID 1, a signal with no handler would be ignored during the bootstrap.
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    child = subprocess.Popen([bootstrap])
    try:
        status = child.wait(timeout=settings.prepare_timeout)
    except subprocess.TimeoutExpired:
        child.kill()
        log(f'bootstrap did not finish within {settings.prepare_timeout:g}s')
        return 1
    if status != 0:
        log(f'bootstrap failed with exit status {status}')
        return 1
    child = None

    from supervisor import supervisord

    config = os.environ.get('AGENTDEV_SUPERVISOR_CONFIG', '/etc/agentdev/supervisord.conf')
    supervisord.main(['--nodaemon', '--configuration', config])
    if settings.failure_file.exists():
        log(f'exiting after terminal failure: {settings.failure_file.read_text().strip()}')
        return 1
    return 0


def main() -> int:
    commands = {'run': run, 'control': control}
    if len(sys.argv) != 2 or sys.argv[1] not in commands:
        print(f'usage: {Path(sys.argv[0]).name} {"|".join(commands)}', file=sys.stderr)
        return 2
    return commands[sys.argv[1]]()


if __name__ == '__main__':
    sys.exit(main())
