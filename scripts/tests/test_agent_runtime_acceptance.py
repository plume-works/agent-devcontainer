"""
Container acceptance tests for agent-opencode, run against AGENTDEV_RUNTIME_TEST_IMAGE.

Every container, volume, and network carries the ``agentdev.test=acceptance`` label so
``.devcontainer/scripts/test-agent-runtime.sh`` can clean up after an interrupted run. No test
spends provider or model usage.
"""

from __future__ import annotations

import base64
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import shlex
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from uuid import uuid4

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TESTS = Path(__file__).resolve().parent
TMP_ROOT = REPO_ROOT / '.tmp'
IMAGE = os.environ.get('AGENTDEV_RUNTIME_TEST_IMAGE', '')
PREVIOUS_IMAGE = os.environ.get('AGENTDEV_RUNTIME_PREVIOUS_IMAGE', '')
LABEL = 'agentdev.test=acceptance'
PASSWORD = 'acceptance-password'
XPRA_PASSWORD = 'acceptance-xpra-password'
AUTH_HEADER = 'Basic ' + base64.b64encode(f'opencode:{PASSWORD}'.encode()).decode()
INSTANCE_VOLUMES = {'home': '/home/agent', 'uv': '/uv', 'docker': '/var/lib/docker'}
AUTH = '/var/lib/agentdev/auth'
WORKSPACE = '/workspaces/project'
SCRATCH_DOCKERFILE = 'printf "FROM scratch\\nCOPY f /f\\n" > ~/ctx/Dockerfile'
RUNTIME = '/opt/agentdev-runtime'
FAILURE_RECORD = '/home/agent/.local/state/agentdev/last-failure.json'

# Without an explicit image these tests skip rather than run against whatever is local.
pytestmark = pytest.mark.skipif(not IMAGE, reason='set AGENTDEV_RUNTIME_TEST_IMAGE')


def docker(*args: str, check: bool = True, timeout: float = 300):
    return subprocess.run(
        ['docker', *args], capture_output=True, text=True, check=check, timeout=timeout
    )


def address_of(container: str) -> str:
    return docker(
        'inspect', '-f', '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}', container
    ).stdout.strip()


@dataclass
class Runtime:
    """One project container: its instance volumes, a workspace, and a shared auth volume."""

    name: str
    network: str
    auth: str
    workspace: list[str]
    # A None value leaves that variable out of the container entirely.
    env: dict[str, str | None] = field(default_factory=dict)
    # Further `docker run` options, such as a restart policy or extra mounts.
    options: list[str] = field(default_factory=list)

    def volume(self, key: str) -> str:
        return f'{self.name}-{key}'

    @property
    def volumes(self) -> dict[str, str]:
        """Instance volumes, plus a workspace volume when no checkout is bound there."""
        if any(arg.endswith(f':{WORKSPACE}') for arg in self.workspace):
            return INSTANCE_VOLUMES
        return {**INSTANCE_VOLUMES, 'workspace': WORKSPACE}

    def run(self, image: str = IMAGE) -> None:
        for volume in [self.auth, *(self.volume(key) for key in self.volumes)]:
            docker('volume', 'create', '--label', LABEL, volume)
        mounts = [
            arg
            for key, target in self.volumes.items()
            for arg in ('-v', f'{self.volume(key)}:{target}')
        ]
        env = {'OPENCODE_SERVER_PASSWORD': PASSWORD, 'XPRA_PASSWORD': XPRA_PASSWORD, **self.env}
        env_args = [
            arg
            for key, value in env.items()
            if value is not None
            for arg in ('-e', f'{key}={value}')
        ]
        docker(
            'run',
            '-d',
            '--name',
            self.name,
            '--label',
            LABEL,
            '--network',
            self.network,
            '--privileged',
            *self.options,
            *mounts,
            *self.workspace,
            '-v',
            f'{self.auth}:{AUTH}',
            *env_args,
            image,
        )

    def exit_code(self) -> int:
        return int(docker('inspect', '-f', '{{.State.ExitCode}}', self.name).stdout)

    def runtime(self) -> dict:
        """Return the controller's published state, or an empty dict before it publishes one."""
        shown = docker('exec', self.name, 'cat', '/run/agentdev/state.json', check=False)
        return json.loads(shown.stdout) if shown.returncode == 0 else {}

    def state(self) -> str:
        """Return 'ready', 'degraded', 'failed', 'exited', or 'starting'."""
        if docker('inspect', '-f', '{{.State.Running}}', self.name).stdout.strip() != 'true':
            return 'exited'
        state = self.runtime().get('state')
        return state if state in {'ready', 'degraded', 'failed'} else 'starting'

    def wait(self, timeout: float = 600) -> str:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self.state()
            if state != 'starting':
                return state
            time.sleep(1)
        pytest.fail(f'{self.name} not settled within {timeout}s:\n{self.logs()[-4000:]}')

    def inspect(self, template: str) -> str:
        return docker('inspect', '-f', template, self.name).stdout.strip()

    def retry(self, *component: str) -> subprocess.CompletedProcess[str]:
        return docker(
            'exec', self.name, f'{RUNTIME}/runtime-supervisor.py', 'retry', *component, check=False
        )

    def wait_unready_then_ready(self, timeout: float = 300) -> None:
        deadline = time.monotonic() + timeout
        while self.state() == 'ready' and time.monotonic() < deadline:
            time.sleep(0.5)
        assert self.wait(timeout) == 'ready', self.logs()[-4000:]

    def restart(self) -> None:
        docker('restart', '-t', '120', self.name, timeout=300)
        # PID 1 clears the previous start's readiness marker first thing.
        time.sleep(2)

    def stop(self) -> tuple[int, float]:
        started = time.monotonic()
        docker('stop', '-t', '120', self.name, timeout=300)
        return self.exit_code(), time.monotonic() - started

    def replace(self, image: str = IMAGE) -> None:
        docker('rm', '-f', self.name)
        self.run(image)

    def sh(self, script: str, *, user: str = 'agent', check: bool = True):
        result = docker('exec', '-u', user, self.name, 'bash', '-lc', script, check=False)
        if check and result.returncode != 0:
            pytest.fail(f'{script!r} failed:\n{result.stdout}{result.stderr}')
        return result

    def api(self, method: str, path: str, body: dict | None = None):
        """Call OpenCode's /api{path} inside the container; return its `data` when wrapped."""
        data = f"-H 'content-type: application/json' -d '{json.dumps(body)}'" if body else ''
        out = self.sh(
            f'curl -fsS --max-time 60 -X {method} -H "Authorization: {AUTH_HEADER}" {data} '
            f'http://127.0.0.1:4096/api{path}'
        ).stdout
        payload = json.loads(out)
        return payload['data'] if 'data' in payload else payload

    def logs(self) -> str:
        result = docker('logs', self.name, check=False)
        return result.stdout + result.stderr

    def remove(self) -> None:
        docker('rm', '-f', self.name, check=False)
        docker('volume', 'rm', '-f', *(self.volume(key) for key in self.volumes), check=False)


@pytest.fixture(scope='module')
def network() -> Iterator[str]:
    name = f'agentdev-accept-{uuid4().hex[:8]}'
    docker('network', 'create', '--label', LABEL, name)
    try:
        yield name
    finally:
        listed = docker('ps', '-aq', '--filter', f'network={name}', check=False).stdout.split()
        if listed:
            docker('rm', '-f', *listed, check=False)
        docker('network', 'rm', name, check=False)


def git(repo: Path, *args: str) -> str:
    # Detached auto-maintenance would race own() over the checkout's lock files.
    config = [
        '-c',
        'user.name=t',
        '-c',
        'user.email=t@example.invalid',
        '-c',
        'maintenance.auto=false',
    ]
    return subprocess.run(
        ['git', '-C', str(repo), *config, *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def own(path: Path, uid: int, gid: int | None = None) -> None:
    for item in [path, *path.rglob('*')]:
        os.lchown(item, uid, uid if gid is None else gid)


@pytest.fixture
def scratch() -> Iterator[Path]:
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'acceptance-{uuid4().hex[:8]}'
    root.mkdir()
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def make_checkout(
    root: Path, files: dict[str, str] | None = None, uid: int = 1000, gid: int | None = None
) -> Path:
    """Create a committed checkout under ``root`` owned by ``uid``, to bind as the workspace."""
    repo = root / 'repo'
    repo.mkdir(parents=True)
    for name, body in (files or {'main.py': 'def answer():\n    return 42\n'}).items():
        (repo / name).write_text(body)
    git(repo, 'init', '-q', '-b', 'main')
    git(repo, 'add', '.')
    git(repo, 'commit', '-qm', 'init')
    own(repo, uid, gid)
    return repo


def bind(path: Path) -> list[str]:
    return ['-v', f'{path}:{WORKSPACE}']


@pytest.fixture
def make_runtime(network: str) -> Iterator[Callable[..., Runtime]]:
    created: list[Runtime] = []
    auth_volumes: set[str] = set()

    def factory(
        *,
        workspace: list[str],
        auth: str | None = None,
        options: list[str] | None = None,
        **env: str | None,
    ) -> Runtime:
        name = f'agentdev-accept-{uuid4().hex[:8]}'
        runtime = Runtime(name, network, auth or f'{name}-auth', workspace, env, options or [])
        auth_volumes.add(runtime.auth)
        created.append(runtime)
        return runtime

    yield factory
    for runtime in created:
        runtime.remove()
    if auth_volumes:
        docker('volume', 'rm', '-f', *auth_volumes, check=False)


@pytest.fixture
def ready_runtime(make_runtime, scratch: Path) -> Runtime:
    runtime = make_runtime(workspace=bind(make_checkout(scratch)))
    runtime.run()
    assert runtime.wait() == 'ready', runtime.logs()[-4000:]
    return runtime


@pytest.fixture
def proxy(network: str) -> Iterator[Callable[[Runtime], str]]:
    """Start a pass-through proxy container in front of a runtime; return its address."""
    started: list[str] = []

    def factory(runtime: Runtime) -> str:
        name = f'{runtime.name}-proxy'
        docker(
            'run',
            '-d',
            '--name',
            name,
            '--label',
            LABEL,
            '--network',
            network,
            '-v',
            f'{TESTS / "tcp_proxy.py"}:/tcp_proxy.py:ro',
            '--entrypoint',
            'python3',
            IMAGE,
            '/tcp_proxy.py',
            runtime.name,
            '8080:4096',
            '8081:14500',
        )
        started.append(name)
        deadline = time.monotonic() + 30
        while 'ready' not in docker('logs', name).stdout and time.monotonic() < deadline:
            time.sleep(0.2)
        return address_of(name)

    yield factory
    if started:
        docker('rm', '-f', *started, check=False)


def http(url: str, *, auth: bool) -> tuple[int, bytes]:
    request = urllib.request.Request(url)
    if auth:
        request.add_header('Authorization', AUTH_HEADER)
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def websocket_status(
    host: str, port: int, path: str, *, auth: bool = False, protocol: str | None = None
) -> str:
    """Send a WebSocket upgrade and return the response's status code."""
    headers = [
        f'GET {path} HTTP/1.1',
        f'Host: {host}:{port}',
        'Upgrade: websocket',
        'Connection: Upgrade',
        f'Sec-WebSocket-Key: {base64.b64encode(os.urandom(16)).decode()}',
        'Sec-WebSocket-Version: 13',
    ]
    if auth:
        headers.append(f'Authorization: {AUTH_HEADER}')
    if protocol:
        headers.append(f'Sec-WebSocket-Protocol: {protocol}')
    with socket.create_connection((host, port), timeout=15) as conn:
        conn.sendall(('\r\n'.join(headers) + '\r\n\r\n').encode())
        return conn.recv(4096).split(b'\r\n', 1)[0].decode().split()[1]


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


def test_proxy_reaches_opencode_and_xpra_at_the_root_without_host_ports(
    ready_runtime: Runtime, proxy
):
    address = proxy(ready_runtime)
    assert docker('port', ready_runtime.name).stdout.strip() == ''
    assert http(f'http://{address}:8080/api/info', auth=False)[0] == 401
    status, body = http(f'http://{address}:8080/api/info', auth=True)
    shipped = ready_runtime.sh('opencode --version').stdout.strip()
    assert status == 200 and json.loads(body)['version'] in shipped
    status, page = http(f'http://{address}:8080/', auth=True)
    assert status == 200 and b'<title>OpenCode</title>' in page
    asset = page.split(b'src="', 1)[1].split(b'"', 1)[0].decode()
    assert http(f'http://{address}:8080{asset}', auth=True)[0] == 200
    pty = ready_runtime.api('POST', '/pty', {'command': 'bash', 'args': ['-c', 'sleep 60']})
    connect = f'/api/pty/{pty["id"]}/connect'
    assert websocket_status(address, 8080, connect, auth=True) == '101'
    assert websocket_status(address, 8080, connect) == '401'
    status, page = http(f'http://{address}:8081/', auth=False)
    assert status == 200 and b'<html' in page.lower()
    assert websocket_status(address, 8081, '/', protocol='binary') == '101'


def xpra_session(peer: str, target: str, password: str | None) -> int:
    """Open an Xpra client session from container ``peer``; return the client's exit status."""
    secret = ''
    if password is not None:
        docker('exec', peer, 'sh', '-c', f'printf %s {shlex.quote(password)} > /tmp/xpra-secret')
        secret = '--password-file=/tmp/xpra-secret'
    command = f'timeout 60 xpra info tcp://{target}/ {secret} </dev/null'
    return docker('exec', peer, 'sh', '-c', command, check=False, timeout=120).returncode


def test_peers_on_the_proxy_network_need_the_xpra_password(ready_runtime: Runtime, proxy):
    proxy(ready_runtime)
    peer, target = f'{ready_runtime.name}-proxy', f'{ready_runtime.name}:14500'
    for password in (None, 'wrong'):
        assert xpra_session(peer, target, password) not in (0, 124), password
    assert 'authentication failed' in ready_runtime.logs()
    assert xpra_session(peer, target, XPRA_PASSWORD) == 0
    assert XPRA_PASSWORD not in ready_runtime.sh('ps -eo args', user='root').stdout


def test_enabled_xpra_needs_its_password_to_start(make_runtime, scratch: Path):
    runtime = make_runtime(workspace=bind(make_checkout(scratch / 'a')), XPRA_PASSWORD='')
    runtime.run()
    assert runtime.wait() == 'failed'
    assert runtime.runtime()['latched'] == 'configuration'
    logs = runtime.logs()
    assert 'XPRA_PASSWORD must be set' in logs and 'AGENTDEV_SKIP_XPRA=1' in logs
    assert 'runtime-bootstrap:' not in logs
    skipped = make_runtime(
        workspace=bind(make_checkout(scratch / 'b')), XPRA_PASSWORD=None, AGENTDEV_SKIP_XPRA='1'
    )
    skipped.run()
    assert skipped.wait() == 'ready', skipped.logs()[-4000:]
    assert skipped.sh('pgrep -f "xpra start"', check=False).returncode == 1


def test_cbm_secret_service_and_nested_docker_serve_agent_processes(ready_runtime: Runtime):
    found = ready_runtime.sh(
        'codebase-memory-mcp cli --json search_graph --project workspaces-project '
        '--name-pattern answer'
    ).stdout
    assert 'answer' in found and '"isError":false' in found.replace(' ', '')

    docker('cp', str(TESTS / 'secret_service_client.py'), f'{ready_runtime.name}:/tmp/ssc.py')
    ready_runtime.sh('chmod 755 /tmp/ssc.py', user='root')
    ready_runtime.api(
        'POST',
        '/pty',
        {
            'command': 'bash',
            'args': ['-c', '/usr/bin/python3 /tmp/ssc.py store probe kept; sleep 30'],
        },
    )
    deadline, looked_up = time.monotonic() + 30, ''
    while time.monotonic() < deadline and looked_up != 'kept':
        looked_up = ready_runtime.sh(
            '/usr/bin/python3 /tmp/ssc.py lookup probe', check=False
        ).stdout.strip()
        time.sleep(1)
    assert looked_up == 'kept', 'a secret an OpenCode child stored is visible to docker exec'

    ready_runtime.sh('docker run --rm hello-world | grep -q "Hello from Docker"')
    ready_runtime.sh(
        f'mkdir -p ~/ctx && echo payload > ~/ctx/f && {SCRATCH_DOCKERFILE} && '
        'docker build -q -t acceptance:probe ~/ctx >/dev/null'
    )
    gc = ready_runtime.sh('jq -r .builder.gc.defaultMaxUsedSpace /etc/docker/daemon.json')
    assert gc.stdout.strip() == '10GB'


PYPROJECT = '[project]\nname = "probe"\nversion = "0"\nrequires-python = ">=3.12"\n'
PRE_COMMIT = (
    'repos:\n- repo: local\n  hooks:\n  - id: noop\n    name: noop\n'
    '    entry: "true"\n    language: system\n'
)


def test_clone_start_prepares_a_python_project_with_pre_commit(make_runtime, scratch: Path):
    seed = make_checkout(
        scratch,
        {'pyproject.toml': PYPROJECT, '.pre-commit-config.yaml': PRE_COMMIT},
        uid=os.geteuid(),
    )
    remote = scratch / 'remote.git'
    subprocess.run(['git', 'clone', '-q', '--bare', str(seed), str(remote)], check=True)
    own(remote, 1000)
    runtime = make_runtime(
        workspace=['-v', f'{remote}:/srv/remote.git:ro'],
        AGENTDEV_REPOSITORY_URL='file:///srv/remote.git',
    )
    runtime.run()
    assert runtime.wait() == 'ready', runtime.logs()[-4000:]
    runtime.sh(f'test -f {WORKSPACE}/pyproject.toml && test -x /uv/venvs/project/bin/python')
    runtime.sh(f'grep -q "File generated by pre-commit" {WORKSPACE}/.git/hooks/pre-commit')
    runtime.sh(f'test "$(stat -c %u {WORKSPACE})" = 1000')


def test_non_python_bind_start_skips_project_tooling(ready_runtime: Runtime):
    logs = ready_runtime.logs()
    assert 'no pyproject.toml; skipping uv sync' in logs
    assert 'no .pre-commit-config.yaml; skipping pre-commit hooks' in logs


def test_custom_ids_own_their_files_and_keep_sudo(make_runtime, scratch: Path):
    checkout = make_checkout(scratch, uid=2345, gid=3456)
    runtime = make_runtime(workspace=bind(checkout), AGENTDEV_UID='2345', AGENTDEV_GID='3456')
    runtime.run()
    assert runtime.wait() == 'ready', runtime.logs()[-4000:]
    assert runtime.sh('id -u; id -g').stdout.split() == ['2345', '3456']
    runtime.sh(f'sudo -n true && touch {WORKSPACE}/made-here')
    assert (checkout / 'made-here').stat().st_uid == 2345


def test_preparation_failure_keeps_opencode_unavailable(make_runtime):
    runtime = make_runtime(workspace=[], AGENTDEV_REPOSITORY_URL='file:///nonexistent.git')
    runtime.run()
    assert runtime.wait() == 'failed'
    assert runtime.runtime()['latched'] == 'prepare'
    record = json.loads(runtime.sh(f'cat {FAILURE_RECORD}').stdout)
    assert record['component'] == 'prepare' and record['exit_status'] == 1
    assert any('git clone failed' in line for line in record['output'])
    assert 'opencode: starting' not in runtime.logs()


FORCED_PREPARE = """#!/usr/bin/env bash
if [[ ${1:-} == prepare && -f /srv/force/exit ]]; then
  echo "forced preparation failure"
  exit "$(cat /srv/force/exit)"
fi
exec /opt/agentdev-runtime/runtime-workspace-real.sh "$@"
"""


def opencode_answers(runtime: Runtime) -> bool:
    probe = (
        f'curl -fsS --max-time 5 -H "Authorization: {AUTH_HEADER}" http://127.0.0.1:4096/api/info'
    )
    return runtime.sh(probe, check=False).returncode == 0


@pytest.mark.parametrize('status', [1, 3])
def test_a_latched_start_stays_put_under_the_restart_policy(
    make_runtime, scratch: Path, status: int
):
    force = scratch / 'force'
    force.mkdir()
    (force / 'exit').write_text(str(status))
    stub = scratch / 'runtime-workspace.sh'
    stub.write_text(FORCED_PREPARE)
    stub.chmod(0o755)
    real = REPO_ROOT / '.devcontainer/scripts/runtime-workspace.sh'
    runtime = make_runtime(
        workspace=bind(make_checkout(scratch)),
        options=[
            '--restart',
            'unless-stopped',
            '-v',
            f'{force}:/srv/force:ro',
            '-v',
            f'{stub}:{RUNTIME}/runtime-workspace.sh:ro',
            '-v',
            f'{real}:{RUNTIME}/runtime-workspace-real.sh:ro',
        ],
    )
    runtime.run()
    assert runtime.wait() == 'failed', runtime.logs()[-4000:]
    recorded = runtime.sh(f'cat {FAILURE_RECORD}').stdout
    assert json.loads(recorded)['exit_status'] == status
    interval = float(runtime.runtime().get('interval', 2))
    for _ in range(10):
        time.sleep(interval)
        assert not opencode_answers(runtime)
    assert runtime.inspect('{{.RestartCount}}') == '0'
    assert runtime.state() == 'failed'
    assert runtime.sh(f'cat {FAILURE_RECORD}').stdout == recorded

    (force / 'exit').unlink()
    resumed = runtime.retry()
    assert resumed.returncode == 0, resumed.stdout + resumed.stderr
    assert runtime.wait() == 'ready', runtime.logs()[-4000:]
    assert opencode_answers(runtime)

    docker('exec', runtime.name, 'pkill', '-KILL', '-f', 'runtime-supervisor.py control')
    deadline = time.monotonic() + 120
    while runtime.inspect('{{.RestartCount}}') == '0' and time.monotonic() < deadline:
        time.sleep(1)
    assert runtime.inspect('{{.RestartCount}}') != '0', runtime.logs()[-4000:]
    assert 'controller exited' in runtime.logs()
    assert runtime.wait() == 'ready', runtime.logs()[-4000:]


def test_restart_and_replacement_keep_the_dirty_tree_config_sessions_and_images(
    ready_runtime: Runtime,
):
    ready_runtime.sh(
        f'cd {WORKSPACE} && git switch -qc feature && echo dirty >> main.py && touch untracked.txt'
    )
    ready_runtime.sh(
        'jq ". + {theme: \\"kept\\"}" ~/.config/opencode/opencode.json > /tmp/c && '
        'cp /tmp/c ~/.config/opencode/opencode.json'
    )
    session = ready_runtime.api('POST', '/session', {'title': 'kept'})
    ready_runtime.sh(
        f'mkdir -p ~/ctx && echo x > ~/ctx/f && {SCRATCH_DOCKERFILE} && '
        'docker build -q -t acceptance:kept ~/ctx >/dev/null'
    )
    status = f'cd {WORKSPACE} && git status --porcelain && git rev-parse HEAD'
    before = ready_runtime.sh(status).stdout

    ready_runtime.restart()
    assert ready_runtime.wait() == 'ready', ready_runtime.logs()[-4000:]
    ready_runtime.replace()
    assert ready_runtime.wait() == 'ready', ready_runtime.logs()[-4000:]

    assert ready_runtime.sh(status).stdout == before
    branch = ready_runtime.sh(f'git -C {WORKSPACE} branch --show-current').stdout.strip()
    assert branch == 'feature'
    config = json.loads(ready_runtime.sh('cat ~/.config/opencode/opencode.json').stdout)
    assert config['theme'] == 'kept'
    assert any(p.endswith('/.opencode-plugin') for p in config['plugin'])
    assert session['id'] in {s['id'] for s in ready_runtime.api('GET', '/session')}
    ready_runtime.sh('docker image inspect acceptance:kept >/dev/null')


@pytest.mark.skipif(not PREVIOUS_IMAGE, reason='set AGENTDEV_RUNTIME_PREVIOUS_IMAGE')
def test_upgrade_from_the_previous_image_keeps_user_state(make_runtime, scratch: Path):
    runtime = make_runtime(workspace=bind(make_checkout(scratch)))
    runtime.run(PREVIOUS_IMAGE)
    assert runtime.wait() == 'ready', runtime.logs()[-4000:]
    session = runtime.api('POST', '/session', {'title': 'upgrade'})
    runtime.sh(
        'jq ". + {theme: \\"kept\\"}" ~/.config/opencode/opencode.json > /tmp/c && '
        'cp /tmp/c ~/.config/opencode/opencode.json'
    )
    runtime.replace(IMAGE)
    assert runtime.wait() == 'ready', runtime.logs()[-4000:]
    config = json.loads(runtime.sh('cat ~/.config/opencode/opencode.json').stdout)
    assert config['theme'] == 'kept'
    assert any(p.endswith('/.opencode-plugin') for p in config['plugin'])
    assert session['id'] in {s['id'] for s in runtime.api('GET', '/session')}


def test_concurrent_projects_share_codex_auth_but_not_sessions(make_runtime, scratch: Path):
    first = make_runtime(workspace=bind(make_checkout(scratch / 'a')))
    second = make_runtime(workspace=bind(make_checkout(scratch / 'b')), auth=first.auth)
    first.run()
    second.run()
    assert (first.wait(), second.wait()) == ('ready', 'ready'), first.logs() + second.logs()

    first.sh('echo \'{"shared": true}\' > ~/.codex/auth.json')
    assert json.loads(second.sh('cat ~/.codex/auth.json').stdout) == {'shared': True}
    session = first.api('POST', '/session', {'title': 'only-first'})
    assert session['id'] in {s['id'] for s in first.api('GET', '/session')}
    assert session['id'] not in {s['id'] for s in second.api('GET', '/session')}
    links = second.sh('find ~/.local/share/opencode -type l -printf "%l\\n"').stdout.split()
    assert not [link for link in links if link.startswith(AUTH)], links
    engines = {runtime.sh('docker info -f {{.ID}}').stdout.strip() for runtime in (first, second)}
    assert len(engines) == 2

    intruder = make_runtime(
        workspace=bind(make_checkout(scratch / 'c', uid=2001)),
        auth=first.auth,
        AGENTDEV_UID='2001',
        AGENTDEV_GID='2001',
    )
    intruder.run()
    assert intruder.wait() == 'failed'
    assert intruder.runtime()['latched'] == 'bootstrap'
    assert 'must all use AGENTDEV_UID=1000' in intruder.logs()
    assert json.loads(first.sh('cat ~/.codex/auth.json').stdout) == {'shared': True}


def test_unavailable_worktree_metadata_fails_preparation(make_runtime, scratch: Path):
    main = make_checkout(scratch / 'main', uid=os.geteuid())
    worktree = scratch / 'worktree'
    git(main, 'worktree', 'add', '-q', str(worktree), '-b', 'wt')
    own(worktree, 1000)
    runtime = make_runtime(workspace=bind(worktree))
    runtime.run()
    assert runtime.wait() == 'failed'
    assert 'mount the main repository' in runtime.logs()


def test_crashed_and_hung_services_recover(ready_runtime: Runtime):
    ready_runtime.sh('pkill -KILL -f -- --cbm-daemon-internal', user='root')
    ready_runtime.wait_unready_then_ready()
    ready_runtime.sh('codebase-memory-mcp daemon status >/dev/null')
    ready_runtime.sh('pkill -STOP -f "opencode serve"', user='root')
    ready_runtime.wait_unready_then_ready()
    shipped = ready_runtime.sh('opencode --version').stdout.strip()
    assert ready_runtime.api('GET', '/info')['version'] in shipped


def test_exhausted_recovery_latches_the_running_container(make_runtime, scratch: Path):
    runtime = make_runtime(
        workspace=bind(make_checkout(scratch)),
        AGENTDEV_RECOVERY_ATTEMPTS='1',
        AGENTDEV_HEALTHY_RESET='600',
    )
    runtime.run()
    assert runtime.wait() == 'ready', runtime.logs()[-4000:]
    for expected in ('ready', 'failed'):
        runtime.sh('pkill -KILL -f "xpra start"', user='root', check=False)
        deadline = time.monotonic() + 120
        while runtime.state() == 'ready' and time.monotonic() < deadline:
            time.sleep(0.5)
        assert runtime.wait() == expected, runtime.logs()[-4000:]
    assert runtime.runtime()['latched'] == 'xpra'
    assert 'xpra exhausted 1 recovery attempts' in runtime.logs()
    assert not opencode_answers(runtime)


def test_clean_stop_is_bounded(ready_runtime: Runtime):
    code, elapsed = ready_runtime.stop()
    assert code == 0
    assert elapsed < 90
    stops = [line for line in ready_runtime.logs().splitlines() if 'INFO stopped:' in line]
    assert stops and 'dockerd' in stops[-1]
