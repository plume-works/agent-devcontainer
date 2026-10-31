"""
The controller's on-disk shapes: ``state.json``, the retry request, and the failure record.

Every reader and writer in the package goes through this module. Spec:
standalone-opencode-runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import threading
import time
from uuid import uuid4

# The failure record keeps this many trailing output lines.
OUTPUT_TAIL = 200
# A heartbeat this many intervals old means the controller is gone.
STALE_INTERVALS = 3
DEFAULT_INTERVAL = 2


def log(message: str) -> None:
    """Write to stderr: in an event listener, stdout carries the protocol."""
    print(f'agentdev-runtime: {message}', file=sys.stderr, flush=True)


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


@dataclass(frozen=True)
class RunFiles:
    """The controller's files under ``AGENTDEV_RUN_DIR``."""

    run_dir: Path

    @property
    def state(self) -> Path:
        return self.run_dir / 'state.json'

    @property
    def retry(self) -> Path:
        return self.run_dir / 'retry-request.json'

    @property
    def output_dir(self) -> Path:
        return self.run_dir / 'output'

    @property
    def crash(self) -> Path:
        return self.run_dir / 'controller-failed'

    def output(self, name: str) -> Path:
        """Return where ``supervisor exec`` keeps a program's last result."""
        return self.output_dir / f'{name}.json'

    @property
    def socket(self) -> Path:
        return self.run_dir / 'supervisor.sock'


def failure_record(home: Path) -> Path:
    """Return the failure record on the runtime account's home volume."""
    return home / '.local/state/agentdev/last-failure.json'


def runtime_state(
    *,
    startup_id: str,
    profile: str,
    state: str,
    ready: bool,
    probes: list[str],
    latched: str | None,
    components: dict[str, dict],
    retry: dict | None,
    interval: float,
) -> dict:
    """Build a ``state.json`` document; ``publish`` stamps its heartbeat."""
    return {
        'startup_id': startup_id,
        'profile': profile,
        'state': state,
        'ready': ready,
        'probes': probes,
        'latched': latched,
        'components': components,
        'retry': retry,
        'interval': interval,
        'updated': utc_now(),
    }


def component(status: str, reason: str | None = None) -> dict:
    return {'status': status, **({'reason': reason} if reason is not None else {})}


def publish(path: Path, document: dict) -> None:
    """Write ``document`` with a fresh heartbeat."""
    write_json(path, {**document, 'heartbeat': time.time()})


def current(path: Path, now: float | None = None) -> tuple[str, dict]:
    """Return the published state, or ``stale``, ``missing``, or ``unreadable``, and the document."""
    try:
        document = json.loads(path.read_text())
    except FileNotFoundError:
        return 'missing', {}
    except (OSError, json.JSONDecodeError):
        return 'unreadable', {}
    if not isinstance(document, dict):
        return 'unreadable', {}
    now = time.time() if now is None else now
    try:
        heartbeat = float(document.get('heartbeat') or 0)
        interval = float(document.get('interval') or DEFAULT_INTERVAL)
    except (TypeError, ValueError):
        return 'unreadable', {}
    if now - heartbeat >= STALE_INTERVALS * interval:
        return 'stale', document
    return str(document.get('state')), document


def retry_request(component_name: str | None) -> dict:
    return {'id': uuid4().hex, 'component': component_name}


def take_retry(path: Path) -> dict | None:
    """Return a pending retry request and remove it, so each is answered once."""
    request = read_json(path)
    if request is not None:
        path.unlink(missing_ok=True)
    return request


def retry_answer(request_id: str | None, ok: bool, message: str | None) -> dict:
    return {'id': request_id, 'ok': ok, 'message': message}


def program_result(command: list[str], exit_status: int | None, output: list[str]) -> dict:
    """Build the result ``supervisor exec`` keeps for a program's current attempt."""
    return {'command': command, 'exit_status': exit_status, 'output': output}


def failure(
    *,
    startup_id: str,
    component_name: str,
    reason: str,
    command: list[str] | str,
    exit_status: int | None,
    output: list[str],
) -> dict:
    """Build a failure record."""
    return {
        'startup_id': startup_id,
        'component': component_name,
        'reason': reason,
        'command': command,
        'exit_status': exit_status,
        'output': output[-OUTPUT_TAIL:],
        'time': utc_now(),
    }
