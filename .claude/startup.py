#!/usr/bin/env python3
"""
Start or resume the devcontainer of a Claude Code cloud session.

`startup.py setup`, the environment setup script, registers the agentdev plugin, starts the
Docker daemon, pre-pulls the pinned images, and brings the devcontainer up.
`startup.py resume`, the SessionStart hook, restores what a worker restart stops.
Standard library only: the session host has no project environment.
Design: architecture/cloud-session-devcontainer.
"""

import argparse
from collections.abc import Callable, Mapping
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
RELAY_SCRIPT = REPO_ROOT / '.claude/agent-proxy-relay.py'
CLOUD_ENV = REPO_ROOT / '.devcontainer/cloud-session.env'
PIN_DIR = REPO_ROOT / '.tmp/comp-pin'
LOG_DIR = Path(os.environ.get('AGENTDEV_STARTUP_LOG_DIR') or '/var/log')
DOCKERD_LOG = LOG_DIR / 'dockerd.log'
RELAY_LOG = LOG_DIR / 'agent-proxy-relay.log'
RELAY_PIDFILE = Path('/var/run/agent-proxy-relay.pid')
# Fixed, so the container's proxy address survives the session proxy changing port.
RELAY_PORT = 3128
# The devcontainer's nested engine claims 172.17.0.1, so the host bridge, which
# host.docker.internal resolves to, needs another subnet.
DOCKER_BRIDGE_CIDR = '10.213.0.1/24'
DOCKER_WAIT_SECONDS = 30
DEVCONTAINER_CLI_VERSION = '0.80.2'
LOOPBACK_PROXY = re.compile(r'http://127\.0\.0\.1:(\d+)/?')


class StartupError(Exception):
    """A step failed in a way the session cannot recover from."""


def log(message: str) -> None:
    """Announce a step on stderr, which keeps a SessionStart hook's stdout empty."""
    print(f'\n==> {message}', file=sys.stderr, flush=True)


def run(*command: str, env: Mapping[str, str] | None = None) -> None:
    """Run a command with its output on stderr, raising when it fails."""
    subprocess.run(command, cwd=REPO_ROOT, env=env, stdout=sys.stderr, check=True)


def output(*command: str) -> str:
    """Return a command's stripped stdout, or an empty string when it fails."""
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return result.stdout.strip() if result.returncode == 0 else ''


def is_cloud_host(environ: Mapping[str, str]) -> bool:
    """Tell a cloud session's host from the devcontainer, which sets AGENTDEV_RUNTIME_MODE."""
    return environ.get('CLAUDE_CODE_REMOTE') == 'true' and not environ.get('AGENTDEV_RUNTIME_MODE')


def proxy_port(environ: Mapping[str, str]) -> int | None:
    """Return the port of the session's loopback agent proxy, if HTTPS_PROXY names one."""
    proxy = environ.get('HTTPS_PROXY') or environ.get('https_proxy') or ''
    match = LOOPBACK_PROXY.fullmatch(proxy)
    return int(match.group(1)) if match else None


def cloud_env_text(environ: Mapping[str, str]) -> str:
    """Render cloud-session.env, which points the container at the relay."""
    relay = f'http://host.docker.internal:{RELAY_PORT}'
    no_proxy = environ.get('NO_PROXY') or environ.get('no_proxy') or ''
    token = environ.get('GH_TOKEN') or environ.get('GITHUB_TOKEN') or ''
    return (
        f'HTTPS_PROXY={relay}\nhttps_proxy={relay}\n'
        f'NO_PROXY={no_proxy}\nno_proxy={no_proxy}\n'
        f'GH_TOKEN={token}\n'
    )


def git_identity() -> dict[str, str]:
    """Map the host's git identity onto the variables Compose passes into the container."""
    identity = {}
    if name := output('git', 'config', '--get', 'user.name'):
        identity |= {'GIT_AUTHOR_NAME': name, 'GIT_COMMITTER_NAME': name}
    if email := output('git', 'config', '--get', 'user.email'):
        identity |= {'GIT_AUTHOR_EMAIL': email, 'GIT_COMMITTER_EMAIL': email}
    return identity


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


def start_docker() -> None:
    """Start the host dockerd on its own bridge subnet, unless it already runs."""
    if docker_ready():
        return
    log(f'Starting Docker daemon (log: {DOCKERD_LOG})')
    with DOCKERD_LOG.open('w') as log_file:
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
        if dockerd.poll() is not None:
            raise StartupError(f'dockerd exited with {dockerd.returncode}; see {DOCKERD_LOG}')
        time.sleep(1)
    raise StartupError(f'Docker daemon not ready after {DOCKER_WAIT_SECONDS}s; see {DOCKERD_LOG}')


def prepare_proxy_access(environ: Mapping[str, str]) -> None:
    """Relay the agent proxy onto the Docker bridge and point the container at the relay."""
    port = proxy_port(environ)
    if port is None:
        stop_relay(RELAY_PIDFILE)
        CLOUD_ENV.unlink(missing_ok=True)
        print(
            'startup: warning: no loopback HTTPS_PROXY; gh and git push stay unauthenticated',
            file=sys.stderr,
        )
        return
    if not relay_running_for(port, RELAY_PIDFILE):
        stop_relay(RELAY_PIDFILE)
        bridge = output(
            'docker', 'network', 'inspect', 'bridge', '-f', '{{(index .IPAM.Config 0).Gateway}}'
        )
        if not bridge:
            raise StartupError('cannot read the Docker bridge gateway')
        log(f'Relaying agent proxy {bridge}:{RELAY_PORT} -> 127.0.0.1:{port} (log: {RELAY_LOG})')
        start_relay(bridge, port, RELAY_PIDFILE, RELAY_LOG)
    CLOUD_ENV.write_text(cloud_env_text(environ))


def install_devcontainer_cli() -> None:
    """Install the pinned devcontainer CLI unless that version is already on PATH."""
    if output('devcontainer', '--version') != DEVCONTAINER_CLI_VERSION:
        run('bun', 'install', f'@devcontainers/cli@{DEVCONTAINER_CLI_VERSION}', '--global')


def devcontainer_running() -> bool:
    """Tell whether this checkout's devcontainer is running."""
    label = f'label=devcontainer.local_folder={REPO_ROOT}'
    return bool(output('docker', 'ps', '-q', '--filter', label))


def bring_devcontainer_up(environ: Mapping[str, str]) -> None:
    """Install the CLI, prepare proxy access, and run devcontainer up with the git identity."""
    log('Bringing up devcontainer')
    install_devcontainer_cli()
    prepare_proxy_access(environ)
    run(
        'devcontainer',
        'up',
        '--workspace-folder',
        str(REPO_ROOT),
        env={**environ, **git_identity()},
    )


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


def pull_pinned_images() -> None:
    """Pre-pull the images pinned in devcontainer-compose-pins.yml."""
    log('Pulling pinned devcontainer images')
    PIN_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / 'devcontainer-compose-pins.yml', PIN_DIR / 'docker-compose.yml')
    subprocess.run(['docker', 'compose', 'pull'], cwd=PIN_DIR, stdout=sys.stderr, check=True)


def timed(step: Callable[..., None], *args: object) -> None:
    """Run one setup step and report how long it took."""
    started = time.monotonic()
    step(*args)
    print(f'{step.__name__}: {time.monotonic() - started:.1f}s', file=sys.stderr)


def setup(environ: Mapping[str, str]) -> None:
    """Run the whole environment setup."""
    timed(register_plugin)
    add_cloud_instructions()
    timed(start_docker)
    timed(pull_pinned_images)
    timed(bring_devcontainer_up, environ)
    log('Startup complete')


def resume(environ: Mapping[str, str]) -> None:
    """Restart whatever a worker restart stopped; the devcontainer's own sessions skip it."""
    if not is_cloud_host(environ):
        return
    start_docker()
    if devcontainer_running():
        install_devcontainer_cli()
        prepare_proxy_access(environ)
    else:
        bring_devcontainer_up(environ)


def main(argv: list[str]) -> int:
    """Parse the mode and run it."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument('mode', nargs='?', default='setup', choices=('setup', 'resume'))
    mode = parser.parse_args(argv).mode
    try:
        (setup if mode == 'setup' else resume)(os.environ)
    except (StartupError, subprocess.CalledProcessError, OSError) as error:
        print(f'startup: error: {error}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
