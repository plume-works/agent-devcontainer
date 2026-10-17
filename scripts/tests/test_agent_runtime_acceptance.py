"""Container acceptance tests for agent-opencode, run against AGENTDEV_RUNTIME_TEST_IMAGE."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TMP_ROOT = REPO_ROOT / '.tmp'
IMAGE = os.environ.get('AGENTDEV_RUNTIME_TEST_IMAGE', '')
PASSWORD = 'acceptance-password'
INSTANCE_VOLUMES = {'home': '/home/agent', 'uv': '/uv', 'docker': '/var/lib/docker'}
AUTH = '/var/lib/agentdev/auth'
WORKSPACE = '/workspaces/project'

# Without an explicit image these tests skip rather than run against whatever is local.
pytestmark = pytest.mark.skipif(not IMAGE, reason='set AGENTDEV_RUNTIME_TEST_IMAGE')


def docker(*args: str, check: bool = True, timeout: float = 300):
    return subprocess.run(
        ['docker', *args], capture_output=True, text=True, check=check, timeout=timeout
    )


@dataclass
class Runtime:
    """One project container: its instance volumes, a workspace, and a shared auth volume."""

    name: str
    auth: str
    workspace: list[str]
    env: dict[str, str] = field(default_factory=dict)
    image: str = IMAGE

    def volume(self, key: str) -> str:
        return f'{self.name}-{key}'

    def run(self) -> None:
        mounts = [
            arg
            for key, target in INSTANCE_VOLUMES.items()
            for arg in ('-v', f'{self.volume(key)}:{target}')
        ]
        env = {'OPENCODE_SERVER_PASSWORD': PASSWORD, **self.env}
        env_args = [arg for key, value in env.items() for arg in ('-e', f'{key}={value}')]
        docker(
            'run',
            '-d',
            '--name',
            self.name,
            '--privileged',
            *mounts,
            *self.workspace,
            '-v',
            f'{self.auth}:{AUTH}',
            *env_args,
            self.image,
        )

    def wait(self, timeout: float = 600) -> str:
        """Return 'ready', 'failed: <reason>', or 'exited'."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = docker('inspect', '-f', '{{.State.Running}}', self.name).stdout.strip()
            if state != 'true':
                return 'exited'
            probe = docker(
                'exec',
                self.name,
                'bash',
                '-c',
                'cat /run/agentdev/failed 2>/dev/null && exit 2; test -f /run/agentdev/ready',
                check=False,
            )
            if probe.returncode == 0:
                return 'ready'
            if probe.returncode == 2:
                return f'failed: {probe.stdout.strip()}'
            time.sleep(1)
        pytest.fail(f'{self.name} not ready within {timeout}s:\n{self.logs()}')

    def sh(self, script: str, *, user: str = 'agent', check: bool = True):
        result = docker('exec', '-u', user, self.name, 'bash', '-lc', script, check=False)
        if check and result.returncode != 0:
            pytest.fail(f'{script!r} failed:\n{result.stdout}{result.stderr}')
        return result

    def logs(self) -> str:
        result = docker('logs', self.name, check=False)
        return result.stdout + result.stderr

    def remove(self) -> None:
        docker('rm', '-f', self.name, check=False)
        docker('volume', 'rm', '-f', *(self.volume(key) for key in INSTANCE_VOLUMES), check=False)


@pytest.fixture
def checkout() -> Iterator[Path]:
    """Create a Git checkout owned by the default runtime UID, to bind as the workspace."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'acceptance-{uuid4().hex[:8]}'
    repo = root / 'repo'
    repo.mkdir(parents=True)
    (repo / 'main.py').write_text('def answer():\n    return 42\n')
    git = ['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid']
    subprocess.run([*git, 'init', '-q', '-b', 'main'], check=True)
    subprocess.run([*git, 'add', '.'], check=True)
    subprocess.run([*git, 'commit', '-qm', 'init'], check=True)
    for path in [repo, *repo.rglob('*')]:
        os.lchown(path, 1000, 1000)
    try:
        yield repo
    finally:
        shutil.rmtree(root, ignore_errors=True)


@pytest.fixture
def make_runtime() -> Iterator[Callable[..., Runtime]]:
    created: list[Runtime] = []
    auth_volumes: set[str] = set()

    def factory(*, workspace: list[str], auth: str | None = None, **env: str) -> Runtime:
        name = f'agentdev-accept-{uuid4().hex[:8]}'
        runtime = Runtime(name, auth or f'{name}-auth', workspace, env)
        auth_volumes.add(runtime.auth)
        created.append(runtime)
        return runtime

    yield factory
    for runtime in created:
        runtime.remove()
    if auth_volumes:
        docker('volume', 'rm', '-f', *auth_volumes, check=False)


@pytest.fixture
def ready_runtime(make_runtime, checkout: Path) -> Runtime:
    runtime = make_runtime(workspace=['-v', f'{checkout}:{WORKSPACE}'])
    runtime.run()
    assert runtime.wait() == 'ready', runtime.logs()
    return runtime


TOOLS = (
    'claude',
    'codex',
    'opencode',
    'iwe',
    'uv',
    'bun',
    'node',
    'zizmor',
    'gh',
    'codebase-memory-mcp',
    'pre-commit',
    'xpra',
    'docker',
    'git',
    'jq',
    'shellcheck',
    'cmake',
)


def test_runtime_user_tool_inventory(ready_runtime: Runtime):
    for tool in TOOLS:
        path = ready_runtime.sh(f'command -v {tool}').stdout.strip()
        assert path and not path.startswith('/root/'), tool
        ready_runtime.sh(f'timeout 60 {tool} --version >/dev/null')
    ready_runtime.sh('validate_agent_files --help >/dev/null')
    ready_runtime.sh('gh stack --help >/dev/null')
    ready_runtime.sh('test ! -r /root && sudo -n true')
    configured = docker('image', 'inspect', '-f', '{{json .Config.Env}}', IMAGE).stdout
    image_path = next(e for e in json.loads(configured) if e.startswith('PATH='))[5:].split(':')
    assert image_path.index('/home/agent/.local/bin') == len(image_path) - 1, image_path
