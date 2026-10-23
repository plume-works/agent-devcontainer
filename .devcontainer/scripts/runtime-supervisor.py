#!/usr/bin/env python3
"""
PID 1 and service controller for the standalone agent-opencode runtime.

``run`` is the container entrypoint: it runs the root bootstrap, then supervisord in this same
process. ``control`` is the supervisord event listener that starts services in dependency order,
gates them on readiness, and recovers failures within a bounded budget. A failure it cannot
recover latches the runtime ``failed`` until ``retry``; PID 1 exits nonzero only when the
controller or supervisord itself fails. ``exec`` wraps each program to keep its last result for
the failure record. Spec: standalone-opencode-runtime.
"""

from __future__ import annotations

from collections import deque
import configparser
from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import pwd
import queue
import signal
import subprocess
import sys
import threading
import time
from typing import NoReturn
from uuid import uuid4
import xmlrpc.client

SCRIPT_DIR = Path(__file__).resolve().parent
RUNNING_STATES = {'RUNNING'}
DONE_STATES = {'EXITED', 'FATAL', 'STOPPED', 'BACKOFF', 'UNKNOWN'}
SETTLED = {'ready', 'done'}
SUPERVISOR_FAULT_NOT_RUNNING = 70
SUPERVISOR_FAULT_ALREADY_STARTED = 60
OUTPUT_TAIL = 200
PROBE_TAIL = 500
DEFAULT_CONFIG = '/etc/agentdev/supervisord.conf'


def log(message: str) -> None:
    """Write to stderr: in an event listener, stdout carries the protocol."""
    print(f'runtime-supervisor: {message}', file=sys.stderr, flush=True)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def write_json(path: Path, data: dict, owner: tuple[int, int] | None = None) -> None:
    """Replace ``path`` atomically, so a reader never sees a partial document."""
    temp = path.with_name(f'.{path.name}.{os.getpid()}.{threading.get_ident()}')
    temp.write_text(json.dumps(data, indent=2) + '\n')
    if owner is not None:
        os.chown(temp, *owner)
    temp.replace(path)


def read_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return None
    except (OSError, json.JSONDecodeError) as error:
        log(f'ignoring unreadable {path}: {error}')
        return None


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
    strict: bool = field(
        default_factory=lambda: os.environ.get('AGENTDEV_STRICT_STARTUP', '').lower() == 'true'
    )

    @property
    def state_file(self) -> Path:
        return self.run_dir / 'state.json'

    @property
    def retry_file(self) -> Path:
        return self.run_dir / 'retry-request.json'

    @property
    def output_dir(self) -> Path:
        return self.run_dir / 'output'

    @property
    def crash_file(self) -> Path:
        return self.run_dir / 'controller-failed'

    @property
    def failure_record(self) -> Path:
        home = Path(os.environ.get('AGENTDEV_HOME') or Path.home())
        return home / '.local/state/agentdev/last-failure.json'


def runtime_owner() -> tuple[int, int] | None:
    """Return the runtime account's IDs when PID 1 runs as root for it, else None."""
    user = os.environ.get('AGENTDEV_USER')
    if os.geteuid() != 0 or not user:
        return None
    try:
        account = pwd.getpwnam(user)
    except KeyError:
        return None
    return account.pw_uid, account.pw_gid


class Captured:
    """Run a command, stream its output to ours, and keep the tail for a failure record."""

    def __init__(self, command: list[str]) -> None:
        self.command = command
        self.tail: deque[str] = deque(maxlen=OUTPUT_TAIL)
        self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        self.reader = threading.Thread(target=self.pump, daemon=True)
        self.reader.start()

    def pump(self) -> None:
        assert self.process.stdout is not None
        for line in self.process.stdout:
            sys.stdout.buffer.write(line)
            sys.stdout.buffer.flush()
            self.tail.append(line.decode(errors='replace').rstrip('\n'))

    def wait(self, timeout: float | None = None) -> int:
        status = self.process.wait(timeout=timeout)
        self.reader.join(timeout=5)
        return 128 - status if status < 0 else status

    def result(self, status: int) -> dict:
        return {'command': self.command, 'exit_status': status, 'output': list(self.tail)}


@dataclass(frozen=True)
class Service:
    """One supervisord program and its place in the dependency graph."""

    name: str
    # Components that must be ready, or done, before this one starts.
    after: tuple[str, ...] = ()
    oneshot: bool = False
    # Clients restarted, outside their own budget, once this service recovers.
    refresh: tuple[str, ...] = ()
    # A core failure latches the runtime; an optional one only degrades it.
    core: bool = False
    # Siblings launched together with this service, so neither waits for the other.
    alongside: tuple[str, ...] = ()


# Startup order. Optional work before OpenCode is what OpenCode reads when it starts;
# the rest follows it. Spec: standalone-opencode-runtime.
SERVICES = (
    Service('dbus', refresh=('keyring', 'xpra'), core=True),
    Service('keyring', after=('dbus',), core=True),
    Service('prepare', after=('keyring',), oneshot=True, core=True),
    Service('config', after=('prepare',), oneshot=True),
    Service('cbm', after=('prepare',), refresh=('opencode',)),
    Service('opencode', after=('keyring', 'prepare'), core=True, alongside=('xpra',)),
    Service('xpra', after=('keyring',)),
    Service('dockerd'),
    Service('prune', after=('dockerd',), oneshot=True),
    Service('project', after=('prepare',), oneshot=True),
    Service('index', after=('cbm',), oneshot=True),
)


class ComponentFailure(Exception):
    """A component failed, or exhausted its recovery budget."""

    def __init__(self, name: str, reason: str, exit_status: int | None = None) -> None:
        super().__init__(reason)
        self.name = name
        self.reason = reason
        self.exit_status = exit_status


class Latched(Exception):
    """The runtime is latched failed: nothing restarts or reruns until a retry."""


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
        self.by_name = {s.name: s for s in self.services}
        self.health = {s.name: Health() for s in self.services}
        self.status = {s.name: 'pending' for s in self.services}
        self.reasons: dict[str, str] = {}
        self.latched: str | None = None
        self.startup_id = os.environ.get('AGENTDEV_STARTUP_ID', '')
        self.retry: dict | None = None
        # Each program leads its own process group, so its first pid is the group id.
        self.groups: dict[str, int] = {}
        self.commands = program_commands()
        self.publishing = threading.Lock()

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

    # --- state --------------------------------------------------------------------------
    def runtime_state(self) -> str:
        if self.latched:
            return 'failed'
        statuses = set(self.status.values())
        if statuses & {'pending', 'starting', 'recovering'}:
            return 'pending'
        if statuses & {'failed', 'blocked'}:
            return 'degraded'
        return 'ready'

    def publish(self) -> None:
        """Write the state file; its heartbeat is what tells health the controller is alive."""
        statuses, reasons = self.status.copy(), self.reasons.copy()
        components = {
            name: {'status': status, **({'reason': reasons[name]} if name in reasons else {})}
            for name, status in statuses.items()
        }
        with self.publishing:
            write_json(
                self.settings.state_file,
                {
                    'startup_id': self.startup_id,
                    'state': self.runtime_state(),
                    'latched': self.latched,
                    'components': components,
                    'retry': self.retry,
                    'interval': self.settings.interval,
                    'heartbeat': time.time(),
                    'updated': utc_now(),
                },
            )

    def beat(self) -> None:
        """Publish every interval, even while the worker waits on a long phase."""
        while True:
            time.sleep(self.settings.interval)
            self.publish()

    def set_status(self, name: str, status: str, reason: str | None = None) -> None:
        self.status[name] = status
        if reason is None:
            self.reasons.pop(name, None)
        else:
            self.reasons[name] = reason
        self.publish()

    def record(self, failure: ComponentFailure) -> None:
        """Persist the failure on the home volume; only a later failure replaces it."""
        result = read_json(self.settings.output_dir / f'{failure.name}.json') or {}
        exit_status = failure.exit_status
        if exit_status is None:
            exit_status = result.get('exit_status')
        record = {
            'startup_id': self.startup_id,
            'component': failure.name,
            'reason': failure.reason,
            'command': result.get('command') or self.commands.get(failure.name, ''),
            'exit_status': exit_status,
            'output': result.get('output', [])[-OUTPUT_TAIL:],
            'time': utc_now(),
        }
        path = self.settings.failure_record
        owner = runtime_owner()
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if owner is not None:
                for parent in (path.parent.parent, path.parent):
                    os.chown(parent, *owner)
            write_json(path, record, owner)
        except OSError as error:
            log(f'could not write the failure record {path}: {error}')
            print(json.dumps(record), file=sys.stderr, flush=True)

    def fail(self, failure: ComponentFailure) -> None:
        """Record a failed component: a core one latches the runtime, an optional one degrades it."""
        log(f'{failure.name}: {failure.reason}')
        self.record(failure)
        self.status[failure.name] = 'failed'
        self.reasons[failure.name] = failure.reason
        if self.by_name[failure.name].core or self.settings.strict:
            self.latch(failure.name)
        log(
            f'degraded: {failure.name} failed; retry with runtime-supervisor.py retry {failure.name}'
        )
        self.publish()

    def latch(self, name: str) -> NoReturn:
        self.latched = name
        if 'opencode' in self.status and self.status['opencode'] not in {'failed', 'pending'}:
            self.stop('opencode')
            self.status['opencode'] = 'pending'
        for other, status in self.status.items():
            if status == 'starting':
                self.status[other] = 'pending'
        log(f'latched failed on {name}; retry with runtime-supervisor.py retry')
        self.publish()
        raise Latched(name)

    # --- readiness ----------------------------------------------------------------------
    def probe(self, name: str) -> bool:
        try:
            result = subprocess.run(
                [self.settings.health_command, name],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors='replace',
                timeout=max(self.settings.interval * 5, 10),
            )
        except subprocess.TimeoutExpired:
            log(f'{name}: readiness probe timed out')
            return False
        if result.returncode != 0 and result.stdout.strip():
            log(f'{name}: probe exited {result.returncode}: {result.stdout.strip()[-PROBE_TAIL:]}')
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
                status = info['exitstatus']
                if info['statename'] == 'EXITED' and status == 0:
                    log(f'{name}: completed')
                    return
                raise ComponentFailure(name, f'{name} failed (exit status {status})', status)
            self.pause(0.5)
        self.stop(name)
        raise ComponentFailure(name, f'{name} did not finish within {timeout:g}s')

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
                raise ComponentFailure(
                    name, f'{name} exhausted {self.settings.attempts} recovery attempts'
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
        self.set_status(name, 'recovering')
        paused = self.dependents(name)
        self.restart_until_ready(name)
        service = self.by_name[name]
        for client in service.refresh:
            if self.status.get(client) != 'ready':
                continue
            log(f'{client}: reconnecting after {name} recovered')
            try:
                self.restart(client)
                if not self.wait_ready(client):
                    self.restart_until_ready(client)
            except ComponentFailure as failure:
                self.fail(failure)
                continue
            self.health[client].healthy_since = time.monotonic()
        for dependent in paused:
            if dependent in service.refresh or self.status.get(dependent) != 'ready':
                continue
            try:
                if not self.healthy(dependent):
                    self.restart_until_ready(dependent)
            except ComponentFailure as failure:
                self.fail(failure)
        self.set_status(name, 'ready')

    # --- lifecycle ----------------------------------------------------------------------
    def launch(self, service: Service) -> None:
        self.set_status(service.name, 'starting')
        if not service.oneshot:
            log(f'{service.name}: starting')
            self.restart(service.name)

    def settle(self, service: Service) -> None:
        name = service.name
        if service.oneshot:
            self.run_oneshot(name)
            self.set_status(name, 'done')
            return
        if not self.wait_ready(name):
            self.restart_until_ready(name)
        self.health[name].healthy_since = time.monotonic()
        self.set_status(name, 'ready')
        log(f'{name}: ready')

    def eligible(self, service: Service) -> bool:
        """Return whether a component should start now, marking it blocked when it cannot."""
        name = service.name
        if self.status[name] in SETTLED or self.status[name] in {'failed', 'starting'}:
            return False
        unmet = [d for d in service.after if self.status.get(d, 'ready') not in SETTLED]
        if unmet:
            self.set_status(name, 'blocked', f'waiting for {", ".join(unmet)}')
            return False
        return True

    def resume(self) -> None:
        """Bring up, in order, every component that is not yet settled or failed."""
        for service in self.services:
            if not self.eligible(service):
                continue
            batch = [service] + [
                self.by_name[name]
                for name in service.alongside
                if name in self.by_name and self.eligible(self.by_name[name])
            ]
            for member in batch:
                self.launch(member)
            for member in batch:
                try:
                    self.settle(member)
                except ComponentFailure as failure:
                    self.fail(failure)
        state = self.runtime_state()
        if state == 'ready':
            log('all services are ready')
        elif state == 'degraded':
            log('OpenCode is serving; the runtime is degraded')

    def check_once(self) -> None:
        now = time.monotonic()
        for service in self.services:
            name, health = service.name, self.health[service.name]
            if service.oneshot or self.status[name] != 'ready':
                continue
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
            try:
                self.recover(name)
            except ComponentFailure as failure:
                self.fail(failure)
            return

    def take_retry(self) -> dict | None:
        request = read_json(self.settings.retry_file)
        if request is not None:
            self.settings.retry_file.unlink(missing_ok=True)
        return request

    def handle_retry(self, request: dict) -> None:
        component = request.get('component')
        failed = [name for name, status in self.status.items() if status == 'failed']
        if component and component not in self.status:
            self.answer(request, False, f'unknown component {component}')
            return
        if component and self.status[component] != 'failed':
            self.answer(request, False, f'{component} has not failed')
            return
        if component and self.latched and component != self.latched:
            self.answer(
                request, False, f'the runtime is latched on {self.latched}; retry it first'
            )
            return
        if not failed:
            self.answer(request, False, 'nothing has failed')
            return
        targets = [component] if component else failed
        log(f'retrying {", ".join(targets)}')
        for name in targets:
            self.health[name] = Health()
            self.status[name] = 'pending'
            self.reasons.pop(name, None)
        for name, status in self.status.items():
            if status == 'blocked':
                self.status[name] = 'pending'
        self.latched = None
        try:
            self.resume()
        finally:
            ok = all(self.status[name] in SETTLED for name in targets)
            self.answer(request, ok, None if ok else 'the retry failed again')

    def answer(self, request: dict, ok: bool, message: str | None) -> None:
        self.retry = {'id': request.get('id'), 'ok': ok, 'message': message}
        self.publish()

    def run(self) -> None:
        startup_retry = os.environ.get('AGENTDEV_RETRY_ID')
        self.publish()
        threading.Thread(target=self.beat, name='heartbeat', daemon=True).start()
        try:
            self.resume()
        except Latched:
            log('startup latched; waiting for a retry')
        if startup_retry:
            self.answer({'id': startup_retry}, self.latched is None, None)
        self.publish()
        while True:
            self.pause(self.settings.interval)
            if self.shutting_down():
                return
            request = self.take_retry()
            try:
                if request is not None:
                    self.handle_retry(request)
                elif self.latched is None:
                    self.check_once()
            except Latched:
                log('latched; waiting for a retry')


def program_commands(config: str | None = None) -> dict[str, str]:
    """Map each supervisord program to its command, for a failure the program never reported."""
    parser = configparser.RawConfigParser()
    parser.read(config or os.environ.get('AGENTDEV_SUPERVISOR_CONFIG', DEFAULT_CONFIG))
    return {
        section.split(':', 1)[1]: parser[section].get('command', '')
        for section in parser.sections()
        if section.startswith('program:')
    }


def server_proxy(config: str):
    """Return an XML-RPC client for this process's supervisord, over its Unix socket."""
    from supervisor.xmlrpc import SupervisorTransport

    parser = configparser.RawConfigParser()
    parser.read(config)
    transport = SupervisorTransport(None, None, parser['supervisorctl']['serverurl'])
    return xmlrpc.client.ServerProxy('http://127.0.0.1', transport=transport)


def crash(settings: Settings, rpc, reason: str) -> None:
    """End the container: the controller itself failed, so Docker's restart policy applies."""
    log(f'controller failure: {reason}')
    settings.crash_file.write_text(reason + '\n')
    settings.state_file.unlink(missing_ok=True)
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
        except Exception as error:  # noqa: BLE001 — any controller crash ends the container.
            crash(settings, rpc, f'controller error: {error!r}')

    threading.Thread(target=work, name='controller', daemon=True).start()
    while True:
        headers, _ = childutils.listener.wait(sys.stdin, sys.stdout)
        wakeups.put(headers['eventname'])
        childutils.listener.ok(sys.stdout)


def watch_controller(settings: Settings, config: str) -> None:
    """Shut supervisord down when the controller listener dies outside a shutdown."""
    proxy = server_proxy(config)
    while True:
        time.sleep(1)
        try:
            if proxy.supervisor.getState()['statename'] != 'RUNNING':
                continue
            info = proxy.supervisor.getProcessInfo('controller')
        except (OSError, xmlrpc.client.Error) as error:
            log(f'controller watch: supervisord not answering yet ({error})')
            continue
        if info['statename'] in DONE_STATES:
            crash(settings, proxy, f'controller exited ({info["statename"]})')
            return


class Interrupted(Exception):
    """SIGTERM or SIGINT reached PID 1 before supervisord took over."""


def preflight(settings: Settings, holder: dict) -> dict | None:
    """Check the configuration and run the root bootstrap; return a failure, or None."""
    if not settings.skip_xpra and not os.environ.get('XPRA_PASSWORD'):
        reason = (
            'XPRA_PASSWORD must be set to a nonempty secret: Xpra listens on the proxy '
            'network and authenticates every session with it. Set XPRA_PASSWORD, or set '
            'AGENTDEV_SKIP_XPRA=1 to run without Xpra'
        )
        log(reason)
        return {'component': 'configuration', 'reason': reason, 'command': [], 'exit_status': 1}
    bootstrap = os.environ.get(
        'AGENTDEV_BOOTSTRAP_COMMAND', str(SCRIPT_DIR / 'runtime-bootstrap.sh')
    )
    child = Captured([bootstrap])
    holder['child'] = child
    try:
        status = child.wait(timeout=settings.prepare_timeout)
        reason = f'bootstrap failed with exit status {status}'
    except subprocess.TimeoutExpired:
        child.process.kill()
        status = child.wait()
        reason = f'bootstrap did not finish within {settings.prepare_timeout:g}s'
    finally:
        holder['child'] = None
    if status == 0:
        return None
    log(reason)
    return {'component': 'bootstrap', 'reason': reason, **child.result(status)}


def wait_for_retry(settings: Settings, state: dict) -> str:
    """Keep ``state`` current until an operator asks for a retry; return the request's id."""
    published = 0.0
    while True:
        request = read_json(settings.retry_file)
        if request is not None:
            settings.retry_file.unlink(missing_ok=True)
            return str(request.get('id', ''))
        if time.monotonic() - published >= settings.interval:
            write_json(settings.state_file, {**state, 'heartbeat': time.time()})
            published = time.monotonic()
        time.sleep(0.5)


def run() -> int:
    """Container entrypoint: bootstrap as root, then supervisord in this process."""
    settings = Settings()
    settings.run_dir.mkdir(parents=True, exist_ok=True)
    # /run survives `docker restart`: nothing from the previous start may leak into this one.
    for stale in (
        settings.state_file,
        settings.crash_file,
        settings.retry_file,
    ):
        stale.unlink(missing_ok=True)
    startup_id = uuid4().hex
    os.environ['AGENTDEV_STARTUP_ID'] = startup_id
    holder: dict = {'child': None}

    def interrupt(signum: int, _frame) -> NoReturn:
        child = holder['child']
        if child is not None and child.process.poll() is None:
            child.process.terminate()
            raise SystemExit(128 + signum)
        raise SystemExit(0)

    # As PID 1, a signal with no handler would be ignored before supervisord starts.
    signal.signal(signal.SIGTERM, interrupt)
    signal.signal(signal.SIGINT, interrupt)
    retry_id = None
    while (failure := preflight(settings, holder)) is not None:
        # The home volume may not be usable yet, so this record goes to stderr only.
        print(
            json.dumps({'startup_id': startup_id, **failure, 'time': utc_now()}),
            file=sys.stderr,
            flush=True,
        )
        retry = {'id': retry_id, 'ok': False, 'message': failure['reason']} if retry_id else None
        state = {
            'startup_id': startup_id,
            'state': 'failed',
            'latched': failure['component'],
            'components': {
                failure['component']: {'status': 'failed', 'reason': failure['reason']}
            },
            'retry': retry,
            'interval': settings.interval,
            'updated': utc_now(),
        }
        log(f'latched failed on {failure["component"]}; retry with runtime-supervisor.py retry')
        retry_id = wait_for_retry(settings, state)
    if retry_id:
        os.environ['AGENTDEV_RETRY_ID'] = retry_id

    owner = runtime_owner()
    settings.output_dir.mkdir(mode=0o700, exist_ok=True)
    if owner is not None:
        os.chown(settings.output_dir, *owner)

    from supervisor import supervisord

    config = os.environ.get('AGENTDEV_SUPERVISOR_CONFIG', DEFAULT_CONFIG)
    threading.Thread(
        target=watch_controller, args=(settings, config), name='watch', daemon=True
    ).start()
    supervisord.main(['--nodaemon', '--configuration', config])
    if settings.crash_file.exists():
        log(f'exiting after a controller failure: {settings.crash_file.read_text().strip()}')
        return 1
    return 0


def execute() -> int:
    """``exec <name> <command...>``: run one supervised program and keep its last result."""
    if len(sys.argv) < 4:
        print('usage: runtime-supervisor.py exec <name> <command...>', file=sys.stderr)
        return 2
    name, command = sys.argv[2], sys.argv[3:]
    # supervisord signals the whole process group, so the command already has the signal.
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: None)
    child = Captured(command)
    status = child.wait()
    try:
        write_json(Settings().output_dir / f'{name}.json', child.result(status))
    except OSError as error:
        log(f'{name}: could not keep its result: {error}')
    return status


def retry() -> int:
    """``retry [component]``: ask a latched or degraded runtime to rerun what failed."""
    settings = Settings()
    component = sys.argv[2] if len(sys.argv) > 2 else None
    request = {'id': uuid4().hex, 'component': component}
    write_json(settings.retry_file, request)
    deadline = time.monotonic() + settings.prepare_timeout * 2 + settings.start_timeout * 10
    while time.monotonic() < deadline:
        state = read_json(settings.state_file) or {}
        answer = state.get('retry') or {}
        if answer.get('id') == request['id']:
            print(f'runtime state: {state.get("state")}')
            if answer.get('message'):
                print(answer['message'])
            return 0 if answer.get('ok') else 1
        time.sleep(0.5)
    print('the runtime did not answer the retry request in time', file=sys.stderr)
    return 1


def main() -> int:
    commands = {'run': run, 'control': control, 'exec': execute, 'retry': retry}
    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print(f'usage: {Path(sys.argv[0]).name} {"|".join(commands)}', file=sys.stderr)
        return 2
    if sys.argv[1] in {'run', 'control'} and len(sys.argv) != 2:
        print(f'usage: {Path(sys.argv[0]).name} {sys.argv[1]}', file=sys.stderr)
        return 2
    return commands[sys.argv[1]]()


if __name__ == '__main__':
    sys.exit(main())
