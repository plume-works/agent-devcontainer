"""Tests for the agentdev-devcontainer create, start, and attach commands and their hooks."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
# Runs `agentdev-runtime lifecycle` with the steps other modules own recorded instead of run;
# the hooks, the catalog check, and the marker stay real.
LIFECYCLE = """
import os, sys
from pathlib import Path
from agentdev_runtime import agent_state, catalog, cbm, git, health, lifecycle, project, workspace

state = Path(os.environ['LIFECYCLE_STATE'])

def record(text, code=0):
    with open(os.environ['CALL_LOG'], 'a') as handle:
        handle.write(text + '\\n')
    return code

git.safe_directory = lambda settings: record('agentdev-runtime git safe-directory')
git.credential_helper = lambda settings: record('agentdev-runtime git credential-helper')
agent_state.create = lambda settings: record('agentdev-runtime state create')
agent_state.apply_agent_policy = lambda: record('agentdev-runtime state agent-policy')
workspace.Workspace.project = lambda self: record('agentdev-runtime workspace project')
catalog.install = lambda settings, root, scope: record(
    f'agentdev-runtime catalog install {root}' + (f' --claude-scope {scope}' if scope else '')
)
cbm.Daemon.start = lambda self: record('agentdev-runtime cbm start')
cbm.Daemon.index = lambda self, repo: record(f'agentdev-runtime cbm index {repo}')
project.sync = lambda settings: record('agentdev-runtime project sync')
health.ready = lambda settings: 0 if (state / 'ready').exists() else 1

def status(settings):
    current = (state / 'state').read_text() if (state / 'state').exists() else 'pending'
    print(f'runtime state: {current}')
    return 1

health.status = status
sys.exit(lifecycle.main(sys.argv[1:]))
"""
START_STEPS = [
    'agentdev-runtime git safe-directory',
    'agentdev-runtime git credential-helper',
    'agentdev-runtime state agent-policy',
]


class Lifecycle:
    """A workspace, hook root, and fake tools around one lifecycle command at a time."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.bin = root / 'bin'
        self.workspace = root / 'workspace'
        self.hooks = root / 'hooks'
        self.state = root / 'state'
        self.staged = root / 'staged-catalog'
        self.log = root / 'calls.log'
        for directory in (self.bin, self.workspace, self.state, self.staged):
            directory.mkdir(parents=True)
        (root / 'home').mkdir()
        self.stub(self.bin / 'sudo', 'sudo')
        self.stub(self.bin / 'codebase-memory-mcp', 'codebase-memory-mcp')

    def write(self, path: Path, body: str) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
        path.chmod(0o755)

    def stub(self, path: Path, name: str) -> None:
        self.write(path, f'#!/usr/bin/env bash\necho "{name} $*" >> "{self.log}"\n')

    def hook(self, phase: str, name: str, body: str = '', executable: bool = True) -> Path:
        path = self.hooks / f'{phase}.d' / name
        self.write(
            path,
            f'#!/usr/bin/env bash\necho "hook {phase}/{name} $AGENTDEV_LIFECYCLE_PHASE" >> "{self.log}"\n{body}',
        )
        if not executable:
            path.chmod(0o644)
        return path

    def env(self, **extra: str) -> dict[str, str]:
        return {
            'PATH': f'{self.bin}:/usr/local/bin:/usr/bin:/bin',
            'HOME': str(self.root / 'home'),
            'GIT_CONFIG_GLOBAL': str(self.root / 'gitconfig'),
            'GIT_CONFIG_NOSYSTEM': '1',
            'DEV_WORKSPACE_FOLDER': str(self.workspace),
            'AGENTDEV_LIFECYCLE_DIR': str(self.root / 'lifecycle'),
            'AGENTDEV_HOOKS_ROOT': str(self.hooks),
            'AGENTDEV_CATALOG_DIR': str(self.staged),
            'AGENTDEV_RUN_DIR': str(self.root / 'run'),
            'AGENTDEV_READY_TIMEOUT': '3',
            'LIFECYCLE_STATE': str(self.state),
            'CALL_LOG': str(self.log),
            **extra,
        }

    def argv(self, *args: str) -> list[str]:
        return [sys.executable, '-c', LIFECYCLE, *args]

    def run(self, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            self.argv(*args),
            env=self.env(**extra),
            cwd=self.workspace,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def calls(self) -> list[str]:
        if not self.log.exists():
            return []
        return [
            line.strip()
            for line in self.log.read_text().splitlines()
            if not line.startswith('sudo ')
        ]

    def complete_catalog(self) -> None:
        (self.workspace / '.claude-plugin').mkdir()
        (self.workspace / '.claude-plugin/marketplace.json').write_text('{}')
        (self.workspace / '.agents/plugins/agentdev/.opencode-plugin').mkdir(parents=True)

    @property
    def marker(self) -> Path:
        return self.root / 'lifecycle/created'


@pytest.fixture
def lifecycle(tmp_path: Path) -> Lifecycle:
    return Lifecycle(tmp_path)


def assert_ok(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr


def test_create_initializes_clients_project_and_staged_catalog_then_runs_hooks(lifecycle):
    lifecycle.hook('created', '20-second')
    lifecycle.hook('created', '10-first')
    assert_ok(lifecycle.run('created'))
    # Trust the checkout first: pre-commit refuses a repository another UID owns.
    assert lifecycle.calls() == [
        'agentdev-runtime git safe-directory',
        'agentdev-runtime state create',
        'agentdev-runtime workspace project',
        f'agentdev-runtime catalog install {lifecycle.staged} --claude-scope user',
        'hook created/10-first created',
        'hook created/20-second created',
    ]
    assert lifecycle.marker.exists()


def test_create_is_idempotent(lifecycle):
    assert_ok(lifecycle.run('created'))
    first = lifecycle.calls()
    assert_ok(lifecycle.run('created'))
    assert lifecycle.calls() == first * 2
    assert lifecycle.marker.exists()


def test_create_without_a_staged_catalog_skips_its_install(lifecycle):
    result = lifecycle.run('created', AGENTDEV_CATALOG_DIR='')
    assert_ok(result)
    assert not any('catalog' in call for call in lifecycle.calls())
    assert 'No catalog staged in the image' in result.stdout


@pytest.mark.skipif(os.geteuid() != 0, reason='ancestor ownership is claimed only as root')
def test_create_claims_ancestors_but_never_checkout_contents(lifecycle):
    (lifecycle.workspace / '.cache').mkdir()
    assert_ok(lifecycle.run('created'))
    sudo = [line for line in lifecycle.log.read_text().splitlines() if line.startswith('sudo ')]
    assert f'sudo chown 0:0 {lifecycle.workspace}' in sudo
    assert f'sudo chown -R 0:0 {lifecycle.workspace}/.cache' not in sudo
    assert not any(line.startswith(f'sudo chown -R 0:0 {lifecycle.workspace} ') for line in sudo)


def test_wait_returns_only_after_a_create_phase_finished(lifecycle):
    waiter = subprocess.Popen(lifecycle.argv('created', '--wait'), env=lifecycle.env())
    try:
        time.sleep(1.5)
        assert waiter.poll() is None
        assert_ok(lifecycle.run('created'))
        assert waiter.wait(timeout=10) == 0
    finally:
        waiter.kill()


def test_start_waits_for_the_runtime_then_repairs_state_and_runs_hooks(lifecycle):
    lifecycle.hook('started', 'notify')
    ready = subprocess.Popen(
        lifecycle.argv('ready'),
        env=lifecycle.env(AGENTDEV_READY_TIMEOUT='30'),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    time.sleep(1.5)
    assert ready.poll() is None and lifecycle.calls() == []
    (lifecycle.state / 'ready').touch()
    assert ready.wait(timeout=10) == 0
    assert lifecycle.calls() == [*START_STEPS, 'hook started/notify started']


def test_start_fails_when_the_runtime_failed(lifecycle):
    (lifecycle.state / 'state').write_text('failed')
    result = lifecycle.run('ready', AGENTDEV_READY_TIMEOUT='30')
    assert result.returncode == 1
    assert 'the runtime failed; the editor cannot attach' in result.stderr
    assert 'runtime state: failed' in result.stderr
    assert lifecycle.calls() == []


def test_start_fails_when_the_runtime_is_not_ready_in_time(lifecycle):
    started = time.monotonic()
    result = lifecycle.run('ready', AGENTDEV_READY_TIMEOUT='2')
    assert result.returncode == 1 and time.monotonic() - started < 20
    assert 'not ready within 2s' in result.stderr
    assert lifecycle.calls() == []


def test_attach_registers_a_complete_checkout_catalog(lifecycle):
    lifecycle.complete_catalog()
    (lifecycle.workspace / 'pyproject.toml').write_text('')
    lifecycle.hook('attached', 'refresh')
    assert_ok(lifecycle.run('attached'))
    assert lifecycle.calls() == [
        f'agentdev-runtime cbm index {lifecycle.workspace}',
        'agentdev-runtime project sync',
        f'agentdev-runtime catalog install {lifecycle.workspace}',
        'hook attached/refresh attached',
    ]


@pytest.mark.parametrize(
    'missing', ['.claude-plugin/marketplace.json', '.agents/plugins/agentdev/.opencode-plugin']
)
def test_attach_keeps_the_staged_catalog_for_an_incomplete_checkout(lifecycle, missing):
    lifecycle.complete_catalog()
    target = lifecycle.workspace / missing
    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()
    result = lifecycle.run('attached')
    assert_ok(result)
    assert lifecycle.calls() == [f'agentdev-runtime cbm index {lifecycle.workspace}']
    assert 'keeping the staged catalog' in result.stdout


def test_repeated_attach_reruns_only_attach_scoped_work(lifecycle):
    for _ in range(3):
        assert_ok(lifecycle.run('attached'))
    assert lifecycle.calls() == [f'agentdev-runtime cbm index {lifecycle.workspace}'] * 3
    assert not lifecycle.marker.exists()


def test_hooks_run_executables_in_name_order_and_skip_the_rest(lifecycle):
    lifecycle.hook('attached', '9-last')
    lifecycle.hook('attached', '10-first')
    lifecycle.hook('attached', 'README', executable=False)
    (lifecycle.hooks / 'attached.d/nested').mkdir()
    result = lifecycle.run('hooks', 'attached')
    assert_ok(result)
    assert lifecycle.calls() == [
        'hook attached/10-first attached',
        'hook attached/9-last attached',
    ]
    assert 'skipping README in the attached phase' in result.stdout


def test_a_failing_hook_names_itself_and_its_phase_and_stops_the_phase(lifecycle):
    lifecycle.hook('created', '10-broken', 'exit 7\n')
    lifecycle.hook('created', '20-after')
    result = lifecycle.run('created')
    assert result.returncode == 1
    assert 'hook 10-broken failed in the created phase (exit status 7)' in result.stderr
    assert 'hook created/20-after created' not in lifecycle.calls()
    assert not lifecycle.marker.exists()


def test_a_missing_hook_directory_is_not_an_error(lifecycle):
    assert_ok(lifecycle.run('hooks', 'started'))
    assert lifecycle.run('hooks', 'deployed').returncode == 2


def test_scripts_in_the_mounted_workspace_are_never_run_as_hooks(lifecycle):
    for base in ('.devcontainer/hooks', 'etc/agentdev/hooks', '.agentdev/hooks'):
        for phase in ('created', 'started', 'attached'):
            lifecycle.write(
                lifecycle.workspace / base / f'{phase}.d' / 'evil',
                f'#!/usr/bin/env bash\necho "evil {phase}" >> "{lifecycle.log}"\n',
            )
    (lifecycle.state / 'ready').touch()
    assert_ok(lifecycle.run('created'))
    assert_ok(lifecycle.run('ready'))
    assert_ok(lifecycle.run('attached'))
    assert not any(call.startswith('evil') for call in lifecycle.calls())


def test_a_hook_root_inside_the_workspace_is_refused(lifecycle):
    inside = lifecycle.workspace / 'hooks'
    lifecycle.write(inside / 'attached.d/x', '#!/usr/bin/env bash\ntouch "$0.ran"\n')
    result = lifecycle.run('hooks', 'attached', AGENTDEV_HOOKS_ROOT=str(inside))
    assert result.returncode == 1
    assert 'is inside the workspace' in result.stderr
    assert not (inside / 'attached.d/x.ran').exists()


def test_a_start_without_a_supervisor_starts_cbm_before_the_start_steps(lifecycle):
    assert_ok(lifecycle.run('ready', '--no-wait'))
    assert lifecycle.calls() == ['agentdev-runtime cbm start', *START_STEPS]


def test_the_responder_runs_each_phase_through_the_cli():
    action = (REPO_ROOT / '.github/actions/run-claude-responder/action.yml').read_text()
    phases = [
        'agentdev-runtime lifecycle created',
        'agentdev-runtime lifecycle ready --no-wait',
        'agentdev-runtime lifecycle attached',
    ]
    assert [action.index(phase) for phase in phases] == sorted(action.index(p) for p in phases)
