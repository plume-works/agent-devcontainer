"""Agent state shared by the Dev Container lifecycle and deploy startup. Spec: catalog-lifecycle."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import fcntl
import os
from pathlib import Path
import shutil
import sys
import time

from agentdev_runtime import (
    cbm_purge,
    claude_state,
    opencode_config,
    settings as env,
)

AGENTS_WITH_SHARED_AUTH = ('claude',)


class StateError(Exception):
    """A state step failed; ``status`` is the exit code it reports."""

    def __init__(self, message: str, status: int = 1) -> None:
        super().__init__(message)
        self.status = status


def deploy(settings: env.Settings) -> bool:
    return settings.raw('AGENTDEV_RUNTIME_MODE') == env.DEPLOY


@contextmanager
def config_lock(settings: env.Settings) -> Iterator[None]:
    """Serialize the steps that rewrite the agents' config files."""
    lock = Path(os.environ.get('HOME') or Path.home()) / '.local/state/agentdev/agent-config.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    timeout = float(settings.get('AGENTDEV_CONFIG_LOCK_TIMEOUT'))
    with lock.open('a') as handle:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise StateError(f'timed out waiting for {lock}') from None
                time.sleep(0.1)
        yield


def unlink_claude_json(settings: env.Settings) -> None:
    """Replace a ``~/.claude.json`` link into ``~/.claude`` with the file it points to."""
    claude_json = settings.path('AGENTDEV_CLAUDE_JSON')
    target = settings.path('AGENTDEV_CLAUDE_DIR') / 'claude.json'
    if not claude_json.is_symlink() or claude_json.resolve() != target.resolve():
        return
    claude_json.unlink()
    if target.is_file():
        shutil.move(target, claude_json)


def ensure_auth_dirs(settings: env.Settings) -> None:
    auth = settings.path('AGENTDEV_AGENTS_AUTH_DIR')
    for agent in AGENTS_WITH_SHARED_AUTH:
        (auth / agent).mkdir(parents=True, exist_ok=True)
        (auth / agent).chmod(0o700)


def apply_agent_policy() -> None:
    opencode_config.configure()


def create(settings: env.Settings) -> None:
    unlink_claude_json(settings)
    cbm_purge.purge(settings)
    ensure_auth_dirs(settings)
    claude_state.preapprove(settings)


def main(argv: list[str]) -> int:
    settings = env.Settings()
    try:
        if argv == ['create']:
            with config_lock(settings):
                create(settings)
        elif argv == ['agent-policy']:
            with config_lock(settings):
                apply_agent_policy()
        else:
            print('usage: agentdev-runtime state create|agent-policy', file=sys.stderr)
            return 2
    except StateError as error:
        print(f'agentdev-runtime state: {error}', file=sys.stderr)
        return error.status
    return 0
