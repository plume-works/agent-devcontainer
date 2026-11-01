"""
Workspace preparation as the runtime user.

A valid checkout is reused offline; only deploy clones, into an empty destination. Spec:
standalone-opencode-runtime, agentdev-runtime-images.
"""

from __future__ import annotations

import os
from pathlib import Path
import re
import subprocess
import sys
import threading

from agentdev_runtime import agent_state, catalog, git, project, settings as env

PREFIX = 'agentdev-runtime workspace'
CREDENTIALS = re.compile(r'(://)[^/@\s]+@')


class WorkspaceError(Exception):
    """The checkout cannot be used; the message names the remedy."""


def log(message: str) -> None:
    print(f'{PREFIX}: {message}', flush=True)


def redact(text: str) -> str:
    """Strip any user:password@ from URLs so credentials never reach the log."""
    return CREDENTIALS.sub(r'\1***@', text)


def is_empty_dir(path: Path) -> bool:
    with os.scandir(path) as entries:
        return next(entries, None) is None


class Workspace:
    def __init__(self, settings: env.Settings) -> None:
        self.settings = settings
        self.path = Path(settings.get('DEV_WORKSPACE_FOLDER'))
        self.clone_marker = settings.path('AGENTDEV_STATE_DIR') / 'clone-in-progress'
        os.environ['GIT_TERMINAL_PROMPT'] = '0'

    def git(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ['git', '-C', str(self.path), *args], capture_output=True, text=True, check=False
        )

    def validate_checkout(self) -> None:
        found = self.git('rev-parse', '--absolute-git-dir')
        if found.returncode != 0:
            dot_git = self.path / '.git'
            if dot_git.is_file():
                gitdir = ''.join(
                    line.removeprefix('gitdir: ')
                    for line in dot_git.read_text().splitlines()
                    if line.startswith('gitdir: ')
                )
                raise WorkspaceError(
                    f'{self.path} is a worktree whose Git metadata ({gitdir}) is not available; '
                    "mount the main repository's .git at that same path"
                )
            raise WorkspaceError(
                f'{self.path} has a .git entry but is not a valid Git checkout; repair or empty it'
            )
        git_dir = found.stdout.strip()
        common = self.git('rev-parse', '--path-format=absolute', '--git-common-dir').stdout.strip()
        if not (Path(common) / 'objects').is_dir():
            raise WorkspaceError(
                f'{self.path} uses Git metadata at {common}, which is not mounted; mount it at '
                'that same path'
            )
        log(f'reusing checkout {self.path} (git dir {git_dir}) without contacting its remotes')

    def clone(self) -> None:
        url = self.settings.raw('AGENTDEV_REPOSITORY_URL')
        ref = self.settings.raw('AGENTDEV_REPOSITORY_REF')
        if self.settings.raw('AGENTDEV_RUNTIME_MODE') != env.DEPLOY:
            raise WorkspaceError(
                f'{self.path} is empty; a Dev Container uses the checkout its tool mounts and '
                'never clones'
            )
        if not url:
            raise WorkspaceError(
                f'{self.path} is empty and AGENTDEV_REPOSITORY_URL is not set; mount a checkout '
                'or set a repository to clone'
            )
        # HTTPS credentials come from the injected token through gh, set up before the clone.
        if git.credential_helper(self.settings) != 0:
            raise WorkspaceError('git credential helper setup failed')
        self.clone_marker.parent.mkdir(parents=True, exist_ok=True)
        self.clone_marker.touch()
        log(f'cloning {redact(url)}{f" at {ref}" if ref else ""} into {self.path}')
        command = ['git', 'clone', *(['--branch', ref] if ref else []), '--', url, str(self.path)]
        process = subprocess.Popen(command, stderr=subprocess.PIPE, text=True)
        assert process.stderr is not None

        def relay() -> None:
            for line in process.stderr:
                sys.stderr.write(redact(line))
                sys.stderr.flush()

        relay_thread = threading.Thread(target=relay, daemon=True)
        relay_thread.start()
        status = process.wait()
        relay_thread.join(timeout=5)
        if status != 0:
            raise WorkspaceError(f'git clone failed with exit code {status}')
        self.clone_marker.unlink(missing_ok=True)

    def checkout(self) -> None:
        if not self.path.is_dir():
            raise WorkspaceError(f'workspace {self.path} does not exist')
        if self.clone_marker.is_file() and not is_empty_dir(self.path):
            raise WorkspaceError(
                f'an earlier clone into {self.path} was interrupted; empty that directory to '
                'retry (nothing was deleted)'
            )
        self.clone_marker.unlink(missing_ok=True)
        # Before validation: Git refuses a checkout another UID owns until it is trusted.
        if self.path.stat().st_uid != os.getuid():
            git.safe_directory(self.settings)
        if (self.path / '.git').exists():
            self.validate_checkout()
        elif is_empty_dir(self.path):
            self.clone()
        else:
            raise WorkspaceError(
                f'{self.path} is not empty and is not a Git checkout; mount a checkout or an '
                'empty volume there'
            )

    def project(self) -> None:
        if (self.path / 'pyproject.toml').is_file():
            if project.sync(self.settings) != 0:
                raise WorkspaceError('uv sync failed')
        else:
            log('no pyproject.toml; skipping uv sync')
        if (self.path / '.pre-commit-config.yaml').is_file():
            if project.hooks(self.settings) != 0:
                raise WorkspaceError('pre-commit hook registration failed')
        else:
            log('no .pre-commit-config.yaml; skipping pre-commit hooks')

    def select_catalog(self) -> Path:
        if catalog.complete(self.path):
            return self.path
        staged = self.settings.raw('AGENTDEV_CATALOG_DIR')
        if staged and Path(staged).is_dir():
            return Path(staged)
        raise WorkspaceError(
            'no catalog: the checkout ships none and AGENTDEV_CATALOG_DIR is not a directory'
        )

    def catalog(self) -> None:
        root = self.select_catalog()
        log(f'registering the agentdev catalog at {root} for Claude and OpenCode')
        with agent_state.config_lock(self.settings):
            catalog.install(self.settings, str(root), 'user')

    def prepare(self) -> None:
        """Run the supervisor's core phase; OpenCode starts only once this succeeds."""
        self.checkout()
        with agent_state.config_lock(self.settings):
            agent_state.create(self.settings)
        with agent_state.config_lock(self.settings):
            agent_state.apply_agent_policy()

    def config(self) -> None:
        """Register the catalog, then CBM."""
        self.catalog()
        with agent_state.config_lock(self.settings):
            agent_state.install_cbm(self.settings)


def main(argv: list[str]) -> int:
    commands = ('checkout', 'project', 'catalog', 'config', 'prepare')
    if len(argv) != 1 or argv[0] not in commands:
        print(f'usage: agentdev-runtime workspace {"|".join(commands)}', file=sys.stderr)
        return 2
    try:
        getattr(Workspace(env.Settings()), argv[0])()
    except (
        WorkspaceError,
        agent_state.StateError,
        catalog.CatalogError,
        subprocess.CalledProcessError,
    ) as error:
        print(f'{PREFIX}: {error}', file=sys.stderr, flush=True)
        return 1
    return 0
