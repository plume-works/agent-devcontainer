"""
Lifecycle adapter over codebase-memory-mcp's public ``daemon start|status|stop``.

A daemon generation is its PID plus kernel start time, so a reused PID is never mistaken for,
or killed as, the daemon this adapter started or adopted. Spec: cbm-startup-integration.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
import filecmp
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import time

from agentdev_runtime import codex_hooks, settings as env

PREFIX = 'agentdev-runtime cbm'
BINARY = 'codebase-memory-mcp'
USAGE = (
    'usage: agentdev-runtime cbm install [--config-only]|start|check|index <repo-path>|run|stop'
)
ACTIVE = re.compile(r'daemon: active \(([a-z-]+)\).*pid: ([0-9]+)', re.DOTALL)
HELD = re.compile(r'held by pid ([0-9]+)')
NOT_RUNNING, UNRESPONSIVE, REPLACED = 3, 4, 5
ACCEPTED_STATES = {'queued', 'running', 'succeeded'}
LOG_NAMES = ('activation-events.ndjson', 'cbm-daemon.log', 'daemon-conflicts.ndjson')


class CbmError(Exception):
    """A CBM command cannot run, or failed; ``status`` is its exit code."""

    def __init__(self, message: str, status: int = 1) -> None:
        super().__init__(message)
        self.status = status


def log(message: str) -> None:
    print(f'{PREFIX}: {message}', file=sys.stderr, flush=True)


def process_start_time(pid: int) -> str | None:
    """Return the kernel start time of ``pid``, field 22 of its stat line."""
    try:
        stat = Path(f'/proc/{pid}/stat').read_text()
    except OSError:
        return None
    # The fields count from after the parenthesised command name, which may hold spaces.
    fields = stat.rsplit(') ', 1)[-1].split()
    return fields[19] if len(fields) > 19 else None


@dataclass
class Daemon:
    """The CBM binary, its settings, and the generation file this adapter keeps."""

    settings: env.Settings

    def __post_init__(self) -> None:
        configured = self.settings.get('AGENTDEV_CBM_BIN')
        self.binary = shutil.which(configured) or configured
        self.state_dir = self.settings.path('AGENTDEV_CBM_STATE_DIR')
        self.generation_file = self.state_dir / 'generation'
        self.start_timeout = float(self.settings.get('AGENTDEV_CBM_START_TIMEOUT'))
        self.stop_timeout = float(self.settings.get('AGENTDEV_CBM_STOP_TIMEOUT'))
        self.poll_interval = float(self.settings.get('AGENTDEV_CBM_POLL_INTERVAL'))
        self.unresponsive_limit = int(self.settings.get('AGENTDEV_CBM_UNRESPONSIVE_LIMIT'))

    def require_environment(self) -> None:
        if (
            not self.binary
            or not os.access(self.binary, os.X_OK)
            or not Path(self.binary).is_file()
        ):
            raise CbmError('codebase-memory-mcp is not installed')
        if not self.settings.raw('CBM_CACHE_DIR'):
            raise CbmError('CBM_CACHE_DIR is required')
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.state_dir.chmod(0o700)

    def status(self) -> tuple[int, str | None]:
        """Return ``(0, "<pid> <mode>")`` when healthy, else 3 or ``(4, "<pid> unresponsive")``."""
        result = subprocess.run(
            [self.binary, 'daemon', 'status'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
        output = result.stdout
        active = ACTIVE.search(output)
        if result.returncode == 0 and active:
            return 0, f'{active.group(2)} {active.group(1)}'
        if 'not responding' in output:
            held = HELD.search(output)
            return UNRESPONSIVE, f'{held.group(1)} unresponsive' if held else None
        return NOT_RUNNING, None

    def record_generation(self, pid: int) -> None:
        started = process_start_time(pid)
        if started is None:
            raise CbmError(f'daemon pid {pid} vanished before its generation was recorded')
        staged = self.generation_file.with_name('generation.new')
        staged.write_text(f'{pid} {started}\n')
        staged.replace(self.generation_file)

    def read_generation(self) -> tuple[int, str] | None:
        try:
            pid, started = self.generation_file.read_text().split()[:2]
        except (OSError, ValueError):
            return None
        return int(pid), started

    @staticmethod
    def alive(pid: int, started: str) -> bool:
        return process_start_time(pid) == started

    def kill_generation(self, pid: int, started: str) -> None:
        """Kill only the process whose PID *and* start time match the generation."""
        if not self.alive(pid, started):
            return
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        deadline = time.monotonic() + 5
        while self.alive(pid, started) and time.monotonic() < deadline:
            time.sleep(0.2)
        if self.alive(pid, started):
            log(f'daemon pid {pid} ignored SIGTERM; sending SIGKILL')
            try:
                os.kill(pid, signal.SIGKILL)
            except ProcessLookupError:
                return

    def start(self) -> None:
        self.require_environment()
        try:
            result = subprocess.run(
                [self.binary, 'daemon', 'start'],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=self.start_timeout,
                check=False,
            )
            output, returncode = result.stdout, result.returncode
        except subprocess.TimeoutExpired as expired:
            output, returncode = expired.output or '', 124
            output = output.decode(errors='replace') if isinstance(output, bytes) else output
        print(output.rstrip('\n'), file=sys.stderr, flush=True)
        if returncode != 0:
            raise CbmError(f'daemon start failed with exit code {returncode}')
        deadline = time.monotonic() + self.start_timeout
        while (found := self.status())[0] != 0:
            if time.monotonic() >= deadline:
                raise CbmError(f'daemon did not report active within {self.start_timeout:g}s')
            time.sleep(0.5)
        pid, mode = (found[1] or '').split(' ', 1)
        self.record_generation(int(pid))
        log(f'ready: pid {pid} ({mode})')

    def check(self) -> int:
        """Return 0 for the tracked generation healthy, 3, 4, or 5 when it was replaced."""
        self.require_environment()
        code, found = self.status()
        if code != 0:
            return code
        pid, mode = (found or '').split(' ', 1)
        tracked = self.read_generation()
        if tracked and str(tracked[0]) == pid and self.alive(*tracked):
            return 0
        log(f'daemon generation changed: now pid {pid} ({mode})')
        return REPLACED

    def stop(self) -> None:
        self.require_environment()
        tracked = self.read_generation()
        try:
            returncode = subprocess.run(
                [self.binary, 'daemon', 'stop'],
                stdout=sys.stderr,
                timeout=self.stop_timeout,
                check=False,
            ).returncode
        except subprocess.TimeoutExpired:
            returncode = 124
        if returncode != 0:
            log(f'daemon stop exited {returncode}; bounding cleanup of the tracked generation')
        if tracked:
            deadline = time.monotonic() + self.stop_timeout
            while self.alive(*tracked) and time.monotonic() < deadline:
                time.sleep(0.2)
            self.kill_generation(*tracked)
        self.generation_file.unlink(missing_ok=True)

    def run(self) -> int:
        """Foreground mode for a supervisor: exit nonzero when the tracked daemon is lost."""
        stopping = False

        def stop_requested(*_: object) -> None:
            nonlocal stopping
            stopping = True

        signal.signal(signal.SIGTERM, stop_requested)
        signal.signal(signal.SIGINT, stop_requested)
        self.start()
        unresponsive = 0
        while not stopping:
            time.sleep(self.poll_interval)
            if stopping:
                break
            code = self.check()
            if code == 0:
                unresponsive = 0
            elif code == UNRESPONSIVE:
                unresponsive += 1
                if unresponsive >= self.unresponsive_limit:
                    log(f'daemon unresponsive for {unresponsive} checks')
                    tracked = self.read_generation()
                    if tracked:
                        self.kill_generation(*tracked)
                    return 1
            else:
                log(f'tracked daemon generation lost (check exit {code})')
                return 1
        self.stop()
        return 0

    def index(self, repo: str) -> int:
        """Submit a background index of ``repo`` and return once the daemon accepts it."""
        self.require_environment()
        try:
            result = subprocess.run(
                [
                    self.binary,
                    'cli',
                    '--json',
                    'index_repository',
                    '--repo-path',
                    repo,
                    '--async',
                    'true',
                ],
                capture_output=True,
                text=True,
                timeout=self.start_timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            raise CbmError(
                f'codebase-memory-mcp index request for {repo} timed out', 124
            ) from None
        output = result.stdout
        if result.returncode != 0:
            raise CbmError(
                f'codebase-memory-mcp index request for {repo} exited {result.returncode}: '
                f'{output[:500]}'
            )
        state = accepted_state(output)
        if state is None:
            raise CbmError(
                f'codebase-memory-mcp did not accept the index request for {repo}: {output[:500]}'
            )
        print(f'codebase-memory-mcp: indexing {repo} in the background ({state})')
        return 0


def accepted_state(output: str) -> str | None:
    """Return the job state when the daemon queued, ran, or joined the request."""
    try:
        envelope = json.loads(output)
    except ValueError:
        return None
    if not isinstance(envelope, dict) or envelope.get('isError') is True:
        return None
    content = envelope.get('structuredContent')
    if not isinstance(content, dict):
        return None
    state = content.get('state')
    if content.get('joined') is True or state in ACCEPTED_STATES:
        return state if isinstance(state, str) else None
    return None


@contextmanager
def materialized(claude_json: Path) -> Iterator[None]:
    """
    Make a symlinked ``~/.claude.json`` a real file for the install, then fold it back.

    The installer refuses to write MCP entries through the symlink into the persistent volume;
    restoring on every exit keeps later config writes inside that volume.
    """
    if not claude_json.is_symlink():
        yield
        return
    target = claude_json.resolve()
    print(f'temporarily materializing {claude_json} (symlink -> {target}) for the install')
    claude_json.unlink()
    shutil.copy2(target, claude_json)
    try:
        yield
    finally:
        if claude_json.is_file() and not claude_json.is_symlink():
            shutil.copy2(claude_json, target)
            claude_json.unlink()
        claude_json.unlink(missing_ok=True)
        claude_json.symlink_to(target)
        print(f'restored {claude_json} -> {target}')


def configure_agents(settings: env.Settings, install_dir: Path, extra_path: str = '') -> int:
    """
    Wire the image's CBM binary into the user's agent configuration.

    This runs at container start because the persistent ``~/.claude``/``~/.codex`` volumes
    mount over anything an image build writes; ``install -y --force`` is idempotent.
    """
    environ = dict(os.environ)
    if extra_path:
        environ['PATH'] = f'{extra_path}:{environ.get("PATH", "")}'
    binary = shutil.which(BINARY, path=environ.get('PATH'))
    if binary is None:
        print('codebase-memory-mcp is not installed; skipping agent config wiring.')
        return 0
    cache = settings.raw('CBM_CACHE_DIR')
    if not cache:
        print(
            'CBM_CACHE_DIR is required for codebase-memory-mcp install; it is not set in this '
            'container.',
            file=sys.stderr,
        )
        return 1
    home = Path(os.environ.get('HOME') or Path.home())
    user = subprocess.run(
        ['id', '-un'], capture_output=True, text=True, check=False
    ).stdout.strip()
    print(
        f'codebase-memory-mcp install: user={user} home={home} cache_dir={cache} binary={binary}'
    )
    umask = os.umask(0)
    os.umask(umask)
    print(f'umask={umask:04o}', flush=True)
    # Activation refuses group- or other-writable staging; log what it checks for diagnosis.
    for path in (Path(binary), Path(binary).parent, install_dir, home):
        if path.exists():
            subprocess.run(
                ['stat', '-c', 'preflight stat: %n mode=%a owner=%U:%G links=%h', str(path)],
                check=False,
            )
        else:
            print(f'preflight stat: {path} does not exist', flush=True)
    claude_json = Path(settings.raw('AGENTDEV_CLAUDE_JSON') or home / '.claude.json')
    with materialized(claude_json):
        # cbm writes Codex hooks to hooks.json only when it exists, outside the config.toml
        # Codex rewrites. Spec: cbm-startup-integration.
        codex_home = Path(settings.raw('CODEX_HOME') or home / '.codex')
        codex_home.mkdir(parents=True, exist_ok=True)
        hooks = codex_home / 'hooks.json'
        if not hooks.exists() and not hooks.is_symlink():
            hooks.write_text('{}\n')
        # See bugs/cbm-codex-hooks-block-foreign-tables.
        repaired = codex_hooks.repair_config(codex_home, str(install_dir))
        if repaired != 0:
            return repaired
        environ['CBM_LOG_LEVEL'] = settings.get('CBM_LOG_LEVEL')
        environ['CBM_INSTALL_DIR'] = str(install_dir)
        sys.stdout.flush()
        status = subprocess.run([BINARY, 'install', '-y', '--force'], env=environ, check=False)
    if status.returncode != 0:
        print(
            f'codebase-memory-mcp install failed with exit code {status.returncode}',
            file=sys.stderr,
        )
        report_logs(Path(cache), home)
        return status.returncode
    return 0


def report_logs(cache: Path, home: Path) -> None:
    """Tail CBM's logs under both roots: a rejected cache falls back to the HOME default."""
    for root in (cache, home / '.cache/codebase-memory-mcp'):
        for name in LOG_NAMES:
            path = root / 'logs' / name
            if path.is_file():
                print(f'--- tail of {path} ---', file=sys.stderr)
                print(
                    '\n'.join(path.read_text(errors='replace').splitlines()[-50:]), file=sys.stderr
                )
            else:
                print(f'no log found at {path}', file=sys.stderr)


def install(daemon: Daemon) -> int:
    """Publish a user-owned copy of the image binary, then wire it into the agents."""
    daemon.require_environment()
    install_dir = daemon.settings.path('CBM_INSTALL_DIR')
    staged = install_dir / BINARY
    # The native installer refuses to stage from a directory the caller does not own.
    if Path(daemon.binary).resolve() != staged.resolve():
        install_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        install_dir.chmod(0o700)
        if not staged.is_file() or not filecmp.cmp(daemon.binary, staged, shallow=False):
            fresh = staged.with_name(f'{BINARY}.new')
            shutil.copyfile(daemon.binary, fresh)
            fresh.chmod(0o755)
            fresh.replace(staged)
    status = configure_agents(daemon.settings, install_dir, str(install_dir))
    if status != 0:
        return status
    if not staged.is_file() or not filecmp.cmp(daemon.binary, staged, shallow=False):
        raise CbmError(f'installed {staged} differs from the image binary {daemon.binary}')
    return 0


def main(argv: list[str]) -> int:
    command = argv[0] if argv else ''
    settings = env.Settings()
    daemon = Daemon(settings)
    try:
        if argv == ['install']:
            return install(daemon)
        if argv == ['install', '--config-only']:
            return configure_agents(settings, settings.path('CBM_INSTALL_DIR'))
        if argv == ['start']:
            daemon.start()
            return 0
        if argv == ['check']:
            return daemon.check()
        if command == 'index' and len(argv) == 2:
            return daemon.index(argv[1])
        if argv == ['run']:
            return daemon.run()
        if argv == ['stop']:
            daemon.stop()
            return 0
    except CbmError as error:
        log(str(error))
        return error.status
    print(USAGE, file=sys.stderr)
    return 2
