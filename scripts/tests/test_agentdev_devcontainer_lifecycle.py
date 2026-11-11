"""Tests for the agentdev-devcontainer create, start, and attach commands and their hooks."""

from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import time

import pytest

# Runs `agentdev-runtime lifecycle` with the steps other modules own recorded instead of run;
# the hooks, the catalog check, and the marker stay real.
LIFECYCLE = """
import os, sys
from pathlib import Path
from agentdev_runtime import agent_state, catalog, git, health, lifecycle, project, workspace

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


def test_create_runs_once_per_container(lifecycle):
    lifecycle.hook('created', '10-only')
    assert_ok(lifecycle.run('created'))
    first = lifecycle.calls()
    result = lifecycle.run('created')
    assert_ok(result)
    assert lifecycle.calls() == first
    assert 'already ran in this container' in result.stdout


def test_create_runs_its_hooks_from_the_workspace(lifecycle):
    lifecycle.hook('created', '10-cwd', f'pwd >> "{lifecycle.log}"\n')
    result = subprocess.run(
        lifecycle.argv('created'),
        env=lifecycle.env(),
        cwd=lifecycle.root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert_ok(result)
    assert lifecycle.calls()[-1] == str(lifecycle.workspace)


def test_create_makes_an_environment_root_inside_the_home(lifecycle):
    root = lifecycle.root / 'home/.local/share/uv/venvs'
    assert_ok(lifecycle.run('created', AGENTDEV_VENV_ROOT=str(root)))
    assert root.is_dir()


def test_create_leaves_an_environment_root_outside_the_home_alone(lifecycle):
    root = lifecycle.root / 'uv/venvs'
    assert_ok(lifecycle.run('created', AGENTDEV_VENV_ROOT=str(root)))
    assert not (lifecycle.root / 'uv').exists()


def test_create_without_a_staged_catalog_skips_its_install(lifecycle):
    result = lifecycle.run('created', AGENTDEV_CATALOG_DIR='')
    assert_ok(result)
    assert not any('catalog' in call for call in lifecycle.calls())
    assert 'No catalog staged in the image' in result.stdout


def test_wait_returns_only_after_a_create_phase_finished(lifecycle):
    waiter = subprocess.Popen(
        lifecycle.argv('created', '--wait'), env=lifecycle.env(AGENTDEV_READY_TIMEOUT='30')
    )
    try:
        time.sleep(1.5)
        assert waiter.poll() is None
        assert_ok(lifecycle.run('created'))
        assert waiter.wait(timeout=10) == 0
    finally:
        waiter.kill()


def test_wait_fails_when_the_runtime_fails_before_the_create_phase(lifecycle):
    (lifecycle.state / 'state').write_text('failed')
    result = lifecycle.run('created', '--wait')
    assert result.returncode == 1
    assert 'the runtime failed before the create phase finished' in result.stderr


def test_wait_gives_up_after_the_ready_timeout(lifecycle):
    result = lifecycle.run('created', '--wait', AGENTDEV_READY_TIMEOUT='1')
    assert result.returncode == 1
    assert 'the create phase did not finish within 1s' in result.stderr


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
    assert lifecycle.calls() == []
    assert 'keeping the staged catalog' in result.stdout


def test_repeated_attach_reruns_only_attach_scoped_work(lifecycle):
    for _ in range(3):
        assert_ok(lifecycle.run('attached'))
    assert lifecycle.calls() == []
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


def test_a_start_without_a_supervisor_runs_the_start_steps(lifecycle):
    assert_ok(lifecycle.run('ready', '--no-wait'))
    assert lifecycle.calls() == START_STEPS


PACKAGE = Path(__file__).resolve().parents[2] / 'py_packages/agentdev_runtime'
PROJECT_IMAGE_DOCKERFILE = """\
FROM ubuntu:24.04
RUN apt-get update && apt-get install -y --no-install-recommends sudo python3 python3-json5 python3-yaml \\
 && rm -rf /var/lib/apt/lists/* && userdel --remove ubuntu \\
 && useradd --uid 1000 --user-group --no-create-home agent \\
 && echo 'agent ALL=(ALL:ALL) NOPASSWD: ALL' > /etc/sudoers.d/agent
"""
CLAIM_PROJECT = (
    'setpriv --reuid=1000 --regid=1000 --init-groups env PYTHONPATH=/opt/src '
    'DEV_WORKSPACE_FOLDER={workspace} python3 -c '
    "'from agentdev_runtime import lifecycle, settings; "
    "lifecycle.claim_project(settings.Settings())'"
    " && stat -c '%u:%g' /workspaces/project /workspaces/project/src/file"
)
docker_missing = pytest.mark.skipif(
    shutil.which('docker') is None
    or subprocess.run(['docker', 'info'], capture_output=True).returncode != 0,
    reason='requires a Docker daemon',
)


@pytest.fixture
def project_volume():
    digest = hashlib.sha256(PROJECT_IMAGE_DOCKERFILE.encode()).hexdigest()[:12]
    tag = f'agentdev-lifecycle-project-test:{digest}'
    if subprocess.run(['docker', 'image', 'inspect', tag], capture_output=True).returncode:
        subprocess.run(
            ['docker', 'build', '-q', '-t', tag, '-'],
            input=PROJECT_IMAGE_DOCKERFILE,
            text=True,
            check=True,
            capture_output=True,
        )
    volume = f'agentdev-test-project-{time.monotonic_ns()}'

    def run(before: str, workspace: str = '/workspaces/agent-devcontainer') -> list[str]:
        result = subprocess.run(
            [
                'docker',
                'run',
                '--rm',
                '-v',
                f'{PACKAGE}:/opt/src:ro',
                '-v',
                f'{volume}:/workspaces/project',
                tag,
                'bash',
                '-c',
                f'{before} && {CLAIM_PROJECT.format(workspace=workspace)}',
            ],
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout.splitlines()[-2:]

    try:
        yield run
    finally:
        subprocess.run(['docker', 'volume', 'rm', '-f', volume], capture_output=True)


SEED = 'mkdir -p /workspaces/project/src && echo work > /workspaces/project/src/file'


@docker_missing
def test_create_re_owns_a_sibling_checkout_volume_another_uid_owns(project_volume):
    assert project_volume(SEED) == ['1000:1000', '1000:1000']


@docker_missing
def test_create_leaves_a_sibling_checkout_the_account_owns_untouched(project_volume):
    owned = (
        f'{SEED} && chown 1000:1000 /workspaces/project && chown 0:0 /workspaces/project/src/file'
    )
    assert project_volume(owned) == ['1000:1000', '0:0']


@docker_missing
def test_create_never_re_owns_the_open_workspace(project_volume):
    assert project_volume(SEED, workspace='/workspaces/project') == ['0:0', '0:0']
