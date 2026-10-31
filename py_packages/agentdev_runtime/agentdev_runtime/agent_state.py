"""
Agent state shared by the Dev Container lifecycle and deploy startup.

Deploy makes every step fatal and leaves the CBM install to its own ``cbm`` step; a Dev Container
keeps CBM nonfatal inside ``create``. Spec: catalog-lifecycle.
"""

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
    cbm,
    claude_state,
    codex_config,
    opencode_config,
    settings as env,
)

AGENTS_WITH_SHARED_AUTH = ('claude', 'codex')


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


def link_claude_json(settings: env.Settings) -> None:
    """Link ``~/.claude.json`` into the ``~/.claude`` volume before CBM folds its entry in."""
    claude_dir = settings.path('AGENTDEV_CLAUDE_DIR')
    claude_json = settings.path('AGENTDEV_CLAUDE_JSON')
    target = claude_dir / 'claude.json'
    claude_dir.mkdir(parents=True, exist_ok=True)
    if claude_json.is_file() and not claude_json.is_symlink():
        if deploy(settings):
            # No image-baked copy exists in a deploy home: a real file is the user's.
            shutil.move(claude_json, target)
        else:
            claude_json.unlink()
    if not target.exists():
        target.write_text('{}\n')
    if claude_json.is_symlink() or claude_json.exists():
        claude_json.unlink()
    claude_json.symlink_to(target)


def install_cbm(settings: env.Settings) -> None:
    if deploy(settings):
        try:
            status = cbm.install(cbm.Daemon(settings))
        except cbm.CbmError as error:
            raise StateError(str(error), error.status) from error
        if status != 0:
            raise StateError('codebase-memory-mcp install failed', status)
        return
    # Nonfatal: a failure here would also skip the rest of the create phase.
    status = cbm.configure_agents(settings, settings.path('CBM_INSTALL_DIR'))
    if status != 0:
        print(
            f'WARNING: codebase-memory-mcp install failed (exit {status}); continuing without it.',
            file=sys.stderr,
        )


def ensure_auth_dirs(settings: env.Settings) -> None:
    auth = settings.path('AGENTDEV_AGENTS_AUTH_DIR')
    for agent in AGENTS_WITH_SHARED_AUTH:
        (auth / agent).mkdir(parents=True, exist_ok=True)
        (auth / agent).chmod(0o700)


def register_user_tools(settings: env.Settings) -> None:
    """Register the image's root-home tooling for whichever account runs here."""
    source = settings.path('AGENTDEV_GH_STACK_DIR')
    binary = source / 'gh-stack'
    manifest = source / 'manifest.yml'
    if not (os.access(binary, os.X_OK) and manifest.is_file()):
        return
    extension = settings.path('XDG_DATA_HOME') / 'gh/extensions/gh-stack'
    extension.mkdir(parents=True, exist_ok=True)
    link = extension / 'gh-stack'
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(binary)
    lines = manifest.read_text().splitlines(keepends=True)
    (extension / 'manifest.yml').write_text(
        ''.join(f'path: {link}\n' if line.startswith('path: ') else line for line in lines)
    )


def link_codex_auth(settings: env.Settings) -> None:
    """
    Share Codex's ``auth.json`` through the auth volume as a symlink.

    Codex has no secure-storage directory setting, so only the file is shared. ``codex logout``
    unlinks the local path; every start repairs the link.
    """
    auth_dir = settings.path('AGENTDEV_AGENTS_AUTH_DIR') / 'codex'
    codex_home = settings.path('CODEX_HOME')
    target = auth_dir / 'auth.json'
    local = codex_home / 'auth.json'
    auth_dir.mkdir(parents=True, exist_ok=True)
    codex_home.mkdir(parents=True, exist_ok=True)
    auth_dir.chmod(0o700)
    if local.is_file() and not local.is_symlink():
        shutil.move(local, target)
        target.chmod(0o600)
    if local.is_symlink() or local.exists():
        local.unlink()
    local.symlink_to(target)


def apply_agent_policy() -> None:
    codex_config.configure()
    opencode_config.configure()


def create(settings: env.Settings) -> None:
    if deploy(settings):
        register_user_tools(settings)
    link_claude_json(settings)
    if not deploy(settings):
        install_cbm(settings)
    ensure_auth_dirs(settings)
    claude_state.preapprove(settings)
    link_codex_auth(settings)


def main(argv: list[str]) -> int:
    settings = env.Settings()
    try:
        if argv == ['create']:
            with config_lock(settings):
                create(settings)
        elif argv == ['links']:
            link_codex_auth(settings)
        elif argv == ['agent-policy']:
            with config_lock(settings):
                apply_agent_policy()
        elif argv == ['cbm']:
            with config_lock(settings):
                install_cbm(settings)
        else:
            print('usage: agentdev-runtime state create|links|agent-policy|cbm', file=sys.stderr)
            return 2
    except StateError as error:
        print(f'agentdev-runtime state: {error}', file=sys.stderr)
        return error.status
    return 0
