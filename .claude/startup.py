#!/usr/bin/env python3
"""
Set up a Claude Code cloud session's host to work on this repository.

`startup.py setup`, the environment setup script, registers the agentdev plugin, installs the
cloud-session instructions and environment, provisions the project toolchain on the host, and
installs the git hooks.
`startup.py resume`, the SessionStart hook, restarts the host dockerd and the agent proxy relay
that a host restart stops, and points Docker's client proxy at the relay.
Standard library only: the session host has no project environment until setup runs.
Design: architecture/cloud-session-host-toolchain.
"""

import argparse
from collections.abc import Callable, Mapping
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
RELAY_SCRIPT = REPO_ROOT / '.claude/agent-proxy-relay.py'
LOG_DIR = Path(os.environ.get('AGENTDEV_STARTUP_LOG_DIR') or '/var/log')
DOCKERD_LOG = LOG_DIR / 'dockerd.log'
RELAY_LOG = LOG_DIR / 'agent-proxy-relay.log'
RELAY_PIDFILE = Path('/var/run/agent-proxy-relay.pid')
# On the session's persistent disk, so they outlive the daemons that wrote them.
DAEMON_PIDFILES = {
    'dockerd': Path('/var/run/docker.pid'),
    'containerd': Path('/var/run/docker/containerd/containerd.pid'),
}
# Fixed, so containers keep one proxy address while the session proxy changes port.
RELAY_PORT = 3128
# Off 172.17.0.0/16, where a nested engine inside a container creates its own docker0.
DOCKER_BRIDGE_CIDR = '10.213.0.1/24'
RELAY_HOST = DOCKER_BRIDGE_CIDR.split('/')[0]
DOCKER_WAIT_SECONDS = 30
LOOPBACK_PROXY = re.compile(r'http://127\.0\.0\.1:(\d+)/?')
# The ansible playbook's roles that put every pre-commit hook's binary on PATH.
TOOLCHAIN_TAGS = 'dev_tools,uv_setup'
HOOK_TYPES = ('pre-commit', 'pre-push', 'pre-merge-commit', 'post-checkout')
# The session's placeholder GH_TOKEN fails zizmor's online audits:
# see bugs/zizmor-online-audits-fail-in-cloud-devcontainer.
SESSION_ENV = {'ZIZMOR_OFFLINE': 'true'}


class StartupError(Exception):
    """A step failed in a way the session cannot recover from."""


def log(message: str) -> None:
    """Announce a step on stderr."""
    print(f'\n==> {message}', file=sys.stderr, flush=True)


def run(*command: str, env: Mapping[str, str] | None = None) -> None:
    """Run a command in the checkout with its output on stderr, raising when it fails."""
    subprocess.run(command, cwd=REPO_ROOT, env=env, stdout=sys.stderr, check=True)


def output(*command: str) -> str:
    """Return a command's stripped stdout, or an empty string when it fails."""
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
    except FileNotFoundError:
        return ''
    return result.stdout.strip() if result.returncode == 0 else ''


def is_cloud_host(environ: Mapping[str, str]) -> bool:
    """Tell a cloud session's host from the devcontainer, which sets AGENTDEV_RUNTIME_MODE."""
    return environ.get('CLAUDE_CODE_REMOTE') == 'true' and not environ.get('AGENTDEV_RUNTIME_MODE')


def proxy_port(environ: Mapping[str, str]) -> int | None:
    """Return the port of the session's loopback agent proxy, if HTTPS_PROXY names one."""
    proxy = environ.get('HTTPS_PROXY') or environ.get('https_proxy') or ''
    match = LOOPBACK_PROXY.fullmatch(proxy)
    return int(match.group(1)) if match else None


def relay_alive(pid: int, target_port: int, proc: Path = Path('/proc')) -> bool:
    """
    Tell whether pid is still the relay to target_port.

    A dead relay's pid may be a zombie, with an empty command line, or reused by another
    process, so only the command line identifies it.
    """
    try:
        args = (proc / str(pid) / 'cmdline').read_bytes().split(b'\0')
    except OSError:
        return False
    return any(arg.endswith(b'agent-proxy-relay.py') for arg in args) and args[-3:-1] == [
        b'127.0.0.1',
        str(target_port).encode(),
    ]


def read_pidfile(pidfile: Path) -> tuple[int, int] | None:
    """Return the relay's (pid, target port) from its pid file, if it holds them."""
    try:
        pid, port = pidfile.read_text().split()
        return int(pid), int(port)
    except (OSError, ValueError):
        return None


def relay_running_for(target_port: int, pidfile: Path) -> bool:
    """Tell whether the recorded relay is alive and forwards to target_port."""
    recorded = read_pidfile(pidfile)
    return recorded is not None and recorded[1] == target_port and relay_alive(*recorded)


def stop_relay(pidfile: Path) -> None:
    """Stop the recorded relay, if it is still the relay, and forget it."""
    recorded = read_pidfile(pidfile)
    if recorded is not None and relay_alive(*recorded):
        os.kill(recorded[0], 15)
    pidfile.unlink(missing_ok=True)


def start_relay(listen_host: str, target_port: int, pidfile: Path, log_path: Path) -> None:
    """Start the relay in its own session, so it outlives this script and its hook."""
    with log_path.open('w') as log_file:
        relay = subprocess.Popen(
            [
                sys.executable,
                '-I',
                str(RELAY_SCRIPT),
                listen_host,
                str(RELAY_PORT),
                '127.0.0.1',
                str(target_port),
            ],
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    pidfile.write_text(f'{relay.pid} {target_port}\n')


def docker_ready() -> bool:
    """Tell whether the host Docker daemon answers."""
    return subprocess.run(['docker', 'info'], capture_output=True, check=False).returncode == 0


def process_running(pid: int, name: str, proc: Path = Path('/proc')) -> bool:
    """Tell whether pid is a running process whose program is called name."""
    try:
        argv0 = (proc / str(pid) / 'cmdline').read_bytes().split(b'\0')[0]
    except OSError:
        return False
    return Path(argv0.decode(errors='replace')).name == name


def remove_stale_daemon_pidfiles() -> None:
    """Remove pid files a worker restart left naming another process, which dockerd trusts."""
    for name, pidfile in DAEMON_PIDFILES.items():
        recorded = pidfile.read_text().strip() if pidfile.exists() else ''
        if not (recorded.isdigit() and process_running(int(recorded), name)):
            pidfile.unlink(missing_ok=True)


def start_docker() -> None:
    """Start the host dockerd on its own bridge subnet, unless it already runs."""
    if docker_ready():
        return
    remove_stale_daemon_pidfiles()
    log(f'Starting Docker daemon (log: {DOCKERD_LOG})')
    with DOCKERD_LOG.open('a') as log_file:
        dockerd = subprocess.Popen(
            ['dockerd', '--bip', DOCKER_BRIDGE_CIDR],
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    for _ in range(DOCKER_WAIT_SECONDS):
        if docker_ready():
            return
        if dockerd.poll() is not None and not docker_ready():
            raise StartupError(f'dockerd exited with {dockerd.returncode}; see {DOCKERD_LOG}')
        time.sleep(1)
    raise StartupError(f'Docker daemon not ready after {DOCKER_WAIT_SECONDS}s; see {DOCKERD_LOG}')


def docker_client_proxy(environ: Mapping[str, str]) -> dict[str, str]:
    """Return the Docker client proxy settings that send containers through the relay."""
    relay = f'http://{RELAY_HOST}:{RELAY_PORT}'
    no_proxy = environ.get('NO_PROXY') or environ.get('no_proxy') or ''
    return {'httpProxy': relay, 'httpsProxy': relay, 'noProxy': no_proxy}


def set_docker_client_proxy(proxy: dict[str, str] | None) -> None:
    """Set or clear the default proxy in ~/.docker/config.json, keeping its other settings."""
    target = Path.home() / '.docker/config.json'
    config = json.loads(target.read_text()) if target.exists() else {}
    proxies = config.get('proxies', {})
    if proxy is None:
        proxies.pop('default', None)
    else:
        proxies['default'] = proxy
    config['proxies'] = proxies
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(config, indent=2) + '\n')


def prepare_proxy_access(environ: Mapping[str, str]) -> None:
    """Relay the agent proxy onto the Docker bridge and point Docker's client proxy at it."""
    port = proxy_port(environ)
    if port is None:
        stop_relay(RELAY_PIDFILE)
        set_docker_client_proxy(None)
        print(
            'startup: warning: no loopback HTTPS_PROXY; containers get no proxy', file=sys.stderr
        )
        return
    if not relay_running_for(port, RELAY_PIDFILE):
        stop_relay(RELAY_PIDFILE)
        log(
            f'Relaying agent proxy {RELAY_HOST}:{RELAY_PORT} -> 127.0.0.1:{port} (log: {RELAY_LOG})'
        )
        start_relay(RELAY_HOST, port, RELAY_PIDFILE, RELAY_LOG)
    set_docker_client_proxy(docker_client_proxy(environ))


def register_plugin() -> None:
    """Register this checkout as the plugin marketplace and install agentdev."""
    log('Registering agent-devcontainer marketplace and installing agentdev')
    run('claude', 'plugin', 'marketplace', 'add', './')
    run('claude', 'plugin', 'install', 'agentdev@agent-devcontainer')


def add_cloud_instructions() -> None:
    """Install the cloud-session instructions as the user-level CLAUDE.md."""
    target = Path.home() / '.claude/CLAUDE.md'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / '.claude/CLAUDE.cloud.md', target)


def add_session_env() -> None:
    """Merge SESSION_ENV into the user-level Claude Code settings, which every tool inherits."""
    target = Path.home() / '.claude/settings.json'
    settings = json.loads(target.read_text()) if target.exists() else {}
    settings['env'] = {**settings.get('env', {}), **SESSION_ENV}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(settings, indent=2) + '\n')


def provision_toolchain(environ: Mapping[str, str]) -> None:
    """Install Ansible, then the pinned tools the image's dev_tools and uv_setup roles install."""
    log('Provisioning the project toolchain on the host')
    run('bash', 'docker/ansible/setup-ansible.sh')
    run(
        'ansible-playbook',
        'ansible/playbooks/setup-dev.yml',
        '--tags',
        TOOLCHAIN_TAGS,
        env={**environ, 'ANSIBLE_LOG_PATH': ''},
    )


def sync_project() -> None:
    """Create the project environment and install the git hooks from it."""
    log('Syncing the project environment and installing git hooks')
    run('uv', 'sync')
    hook_types = [arg for hook in HOOK_TYPES for arg in ('--hook-type', hook)]
    run('uv', 'run', 'pre-commit', 'install', '--install-hooks', *hook_types)


def timed(step: Callable[..., None], *args: object) -> None:
    """Run one setup step and report how long it took."""
    started = time.monotonic()
    step(*args)
    print(f'{step.__name__}: {time.monotonic() - started:.1f}s', file=sys.stderr)


def setup(environ: Mapping[str, str]) -> None:
    """Run the whole environment setup."""
    timed(register_plugin)
    add_cloud_instructions()
    add_session_env()
    timed(provision_toolchain, environ)
    timed(sync_project)
    log('Setup complete')


def resume(environ: Mapping[str, str]) -> None:
    """Restart what a host restart stopped; sessions inside a runtime container skip it."""
    if not is_cloud_host(environ):
        return
    start_docker()
    prepare_proxy_access(environ)


def main(argv: list[str]) -> int:
    """Parse the mode and run it."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument('mode', nargs='?', default='setup', choices=('setup', 'resume'))
    mode = parser.parse_args(argv).mode
    try:
        (setup if mode == 'setup' else resume)(os.environ)
    except (StartupError, subprocess.CalledProcessError, OSError, ValueError) as error:
        print(f'startup: error: {error}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
