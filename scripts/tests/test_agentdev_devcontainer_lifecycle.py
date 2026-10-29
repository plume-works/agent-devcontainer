"""Tests for the agentdev-devcontainer create, start, and attach commands and their hooks."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import socket
import subprocess
import time

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / '.devcontainer/scripts'
REAL = [
    'devcontainer-created.sh',
    'devcontainer-ready.sh',
    'devcontainer-attached.sh',
    'run-agentdev-hooks.sh',
    'runtime-paths.sh',
    'postCreateCommand.sh',
    'postStartCommand.sh',
    'postAttachCommand.sh',
]
STUBS = [
    'setup-agent-state.sh',
    'runtime-workspace.sh',
    'uv-sync.sh',
    'codebase-memory-mcp-index.sh',
    'codebase-memory-mcp-start.sh',
    'setup-git-safe-directory.sh',
    'setup-gh-credential-helper.sh',
    'setup-keyring.sh',
    'firewall.sh',
]
FAKE_HEALTH = """#!/usr/bin/env bash
case "$1" in
  ready) [[ -f $LIFECYCLE_STATE/ready ]] ;;
  status) echo "runtime state: $(cat "$LIFECYCLE_STATE/state" 2>/dev/null || echo pending)" ;;
esac
"""
START_STEPS = [
    'setup-git-safe-directory.sh',
    'setup-gh-credential-helper.sh',
    'setup-agent-state.sh links',
    'setup-agent-state.sh agent-policy',
]


class Lifecycle:
    """A copied lifecycle tree whose helpers only record that they ran."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.scripts = root / 'scripts'
        self.bin = root / 'bin'
        self.workspace = root / 'workspace'
        self.hooks = root / 'hooks'
        self.state = root / 'state'
        self.staged = root / 'staged-catalog'
        self.log = root / 'calls.log'
        for directory in (self.scripts, self.bin, self.workspace, self.state, self.staged):
            directory.mkdir(parents=True)
        (root / 'home').mkdir()
        for name in REAL:
            shutil.copy2(SCRIPTS / name, self.scripts / name)
        for name in STUBS:
            self.stub(self.scripts / name, name)
        self.write(self.scripts / 'runtime-health.sh', FAKE_HEALTH)
        self.stub(self.bin / 'sudo', 'sudo')

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
            'AGENTDEV_SKIP_XPRA': '1',
            'LIFECYCLE_STATE': str(self.state),
            **extra,
        }

    def run(self, script: str, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.scripts / script, *args],
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
        (self.workspace / '.agents/plugins/marketplace.json').write_text('{}')

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
    assert_ok(lifecycle.run('devcontainer-created.sh'))
    # Trust the checkout first: pre-commit refuses a repository another UID owns.
    assert lifecycle.calls() == [
        'setup-git-safe-directory.sh',
        'setup-agent-state.sh create',
        'runtime-workspace.sh project',
        f'setup-agent-state.sh catalog {lifecycle.staged} user',
        'hook created/10-first created',
        'hook created/20-second created',
    ]
    assert lifecycle.marker.exists()


def test_create_is_idempotent(lifecycle):
    assert_ok(lifecycle.run('devcontainer-created.sh'))
    first = lifecycle.calls()
    assert_ok(lifecycle.run('devcontainer-created.sh'))
    assert lifecycle.calls() == first * 2
    assert lifecycle.marker.exists()


def test_create_without_a_staged_catalog_skips_its_install(lifecycle):
    result = lifecycle.run('devcontainer-created.sh', AGENTDEV_CATALOG_DIR='')
    assert_ok(result)
    assert not any('catalog' in call for call in lifecycle.calls())
    assert 'No catalog staged in the image' in result.stdout


@pytest.mark.skipif(os.geteuid() != 0, reason='ancestor ownership is claimed only as root')
def test_create_claims_only_ancestors_and_mounted_volumes(lifecycle):
    (lifecycle.workspace / '.cache').mkdir()
    assert_ok(lifecycle.run('devcontainer-created.sh'))
    sudo = [line for line in lifecycle.log.read_text().splitlines() if line.startswith('sudo ')]
    assert f'sudo chown 0:0 {lifecycle.workspace}' in sudo
    assert f'sudo chown -R 0:0 {lifecycle.workspace}/.cache' in sudo
    assert not any(line.startswith(f'sudo chown -R 0:0 {lifecycle.workspace} ') for line in sudo)


def test_wait_returns_only_after_a_create_phase_finished(lifecycle):
    waiter = subprocess.Popen(
        [lifecycle.scripts / 'devcontainer-created.sh', 'wait'], env=lifecycle.env()
    )
    try:
        time.sleep(1.5)
        assert waiter.poll() is None
        assert_ok(lifecycle.run('devcontainer-created.sh'))
        assert waiter.wait(timeout=10) == 0
    finally:
        waiter.kill()


def test_start_waits_for_the_runtime_then_repairs_state_and_runs_hooks(lifecycle):
    lifecycle.hook('started', 'notify')
    ready = subprocess.Popen(
        [lifecycle.scripts / 'devcontainer-ready.sh'],
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
    result = lifecycle.run('devcontainer-ready.sh', AGENTDEV_READY_TIMEOUT='30')
    assert result.returncode == 1
    assert 'the runtime failed; the editor cannot attach' in result.stderr
    assert 'runtime state: failed' in result.stderr
    assert lifecycle.calls() == []


def test_start_fails_when_the_runtime_is_not_ready_in_time(lifecycle):
    started = time.monotonic()
    result = lifecycle.run('devcontainer-ready.sh', AGENTDEV_READY_TIMEOUT='2')
    assert result.returncode == 1 and time.monotonic() - started < 20
    assert 'not ready within 2s' in result.stderr
    assert lifecycle.calls() == []


def test_attach_registers_a_complete_checkout_catalog(lifecycle):
    lifecycle.complete_catalog()
    (lifecycle.workspace / 'pyproject.toml').write_text('')
    lifecycle.hook('attached', 'refresh')
    assert_ok(lifecycle.run('devcontainer-attached.sh'))
    assert lifecycle.calls() == [
        'codebase-memory-mcp-index.sh',
        'uv-sync.sh',
        f'setup-agent-state.sh catalog {lifecycle.workspace}',
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
    result = lifecycle.run('devcontainer-attached.sh')
    assert_ok(result)
    assert lifecycle.calls() == ['codebase-memory-mcp-index.sh']
    assert 'keeping the staged catalog' in result.stdout


def test_repeated_attach_reruns_only_attach_scoped_work(lifecycle):
    for _ in range(3):
        assert_ok(lifecycle.run('devcontainer-attached.sh'))
    assert lifecycle.calls() == ['codebase-memory-mcp-index.sh'] * 3
    assert not lifecycle.marker.exists()


def test_hooks_run_executables_in_name_order_and_skip_the_rest(lifecycle):
    lifecycle.hook('attached', '9-last')
    lifecycle.hook('attached', '10-first')
    lifecycle.hook('attached', 'README', executable=False)
    (lifecycle.hooks / 'attached.d/nested').mkdir()
    result = lifecycle.run('run-agentdev-hooks.sh', 'attached')
    assert_ok(result)
    assert lifecycle.calls() == [
        'hook attached/10-first attached',
        'hook attached/9-last attached',
    ]
    assert 'skipping README in the attached phase' in result.stdout


def test_a_failing_hook_names_itself_and_its_phase_and_stops_the_phase(lifecycle):
    lifecycle.hook('created', '10-broken', 'exit 7\n')
    lifecycle.hook('created', '20-after')
    result = lifecycle.run('devcontainer-created.sh')
    assert result.returncode == 1
    assert 'hook 10-broken failed in the created phase (exit status 7)' in result.stderr
    assert 'hook created/20-after created' not in lifecycle.calls()
    assert not lifecycle.marker.exists()


def test_a_missing_hook_directory_is_not_an_error(lifecycle):
    assert_ok(lifecycle.run('run-agentdev-hooks.sh', 'started'))
    assert lifecycle.run('run-agentdev-hooks.sh', 'deployed').returncode == 2


def test_scripts_in_the_mounted_workspace_are_never_run_as_hooks(lifecycle):
    for base in ('.devcontainer/hooks', 'etc/agentdev/hooks', '.agentdev/hooks'):
        for phase in ('created', 'started', 'attached'):
            lifecycle.write(
                lifecycle.workspace / base / f'{phase}.d' / 'evil',
                f'#!/usr/bin/env bash\necho "evil {phase}" >> "{lifecycle.log}"\n',
            )
    (lifecycle.state / 'ready').touch()
    assert_ok(lifecycle.run('devcontainer-created.sh'))
    assert_ok(lifecycle.run('devcontainer-ready.sh'))
    assert_ok(lifecycle.run('devcontainer-attached.sh'))
    assert not any(call.startswith('evil') for call in lifecycle.calls())


def test_a_hook_root_inside_the_workspace_is_refused(lifecycle):
    inside = lifecycle.workspace / 'hooks'
    lifecycle.write(inside / 'attached.d/x', '#!/usr/bin/env bash\ntouch "$0.ran"\n')
    result = lifecycle.run('run-agentdev-hooks.sh', 'attached', AGENTDEV_HOOKS_ROOT=str(inside))
    assert result.returncode == 1
    assert 'is inside the workspace' in result.stderr
    assert not (inside / 'attached.d/x.ran').exists()


def test_checkout_relative_hooks_delegate_to_the_image_commands(lifecycle):
    (lifecycle.state / 'ready').touch()
    assert_ok(lifecycle.run('postCreateCommand.sh'))
    assert lifecycle.marker.exists()
    lifecycle.log.unlink()
    assert_ok(lifecycle.run('postAttachCommand.sh'))
    assert lifecycle.calls() == ['codebase-memory-mcp-index.sh']


def test_an_unsupervised_start_starts_services_before_the_start_steps(lifecycle):
    assert_ok(lifecycle.run('postStartCommand.sh'))
    assert lifecycle.calls() == [
        'codebase-memory-mcp-start.sh',
        'setup-keyring.sh',
        'firewall.sh',
        *START_STEPS,
    ]


def test_a_supervised_start_never_starts_a_second_set_of_services(lifecycle):
    run_dir = lifecycle.root / 'run'
    run_dir.mkdir()
    listener = socket.socket(socket.AF_UNIX)
    listener.bind(str(run_dir / 'supervisor.sock'))
    try:
        (lifecycle.state / 'ready').touch()
        assert_ok(lifecycle.run('postStartCommand.sh'))
        assert lifecycle.calls() == START_STEPS
    finally:
        listener.close()
