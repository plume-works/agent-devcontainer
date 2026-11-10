#!/usr/bin/env python3
"""
Start or resume the devcontainer of a Claude Code cloud session.

`startup.py setup`, the environment setup script, registers the agentdev plugin, starts the
Docker daemon, and builds the devcontainer image; it has no session proxy, so it creates no
container.
`startup.py resume`, the SessionStart hook, restores what a worker restart stops.
Standard library only: the session host has no project environment.
Design: openspec/specs/cloud-session-devcontainer.
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
LOG_DIR = Path(os.environ.get('AGENTDEV_STARTUP_LOG_DIR') or '/var/log')
DOCKERD_LOG = LOG_DIR / 'dockerd.log'
RELAY_LOG = LOG_DIR / 'agent-proxy-relay.log'
RELAY_PIDFILE = Path('/var/run/agent-proxy-relay.pid')
# On the session's persistent disk, so they outlive the daemons that wrote them.
DAEMON_PIDFILES = {
    'dockerd': Path('/var/run/docker.pid'),
    'containerd': Path('/var/run/docker/containerd/containerd.pid'),
}
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


def cloud_env_text(environ: Mapping[str, str]) -> str:
    """Render cloud-session.env, which points the container at the relay."""
    relay = f'http://host.docker.internal:{RELAY_PORT}'
    no_proxy = environ.get('NO_PROXY') or environ.get('no_proxy') or ''
    token = environ.get('GH_TOKEN') or environ.get('GITHUB_TOKEN') or ''
    # The proxy honours GH_TOKEN only for in-scope repositories, so zizmor's online
    # audits get 401s: see bugs/zizmor-online-audits-fail-in-cloud-devcontainer.
    return (
        f'HTTPS_PROXY={relay}\nhttps_proxy={relay}\n'
        f'NO_PROXY={no_proxy}\nno_proxy={no_proxy}\n'
        f'GH_TOKEN={token}\n'
        'ZIZMOR_OFFLINE=true\n'
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


def devcontainer_ids(*flags: str) -> list[str]:
    """Return the IDs of this checkout's devcontainer, running only unless flags say otherwise."""
    label = f'label=devcontainer.local_folder={REPO_ROOT}'
    return output('docker', 'ps', '-q', *flags, '--filter', label).split()


def lacks_session_env(container: str) -> bool:
    """Tell whether the container's environment misses or differs from cloud-session.env."""
    if not CLOUD_ENV.exists():
        return False
    wanted = set(CLOUD_ENV.read_text().splitlines()) - {''}
    env = output('docker', 'inspect', '-f', '{{range .Config.Env}}{{println .}}{{end}}', container)
    return not wanted <= set(env.splitlines())


def devcontainer_up(environ: Mapping[str, str], *flags: str) -> None:
    """Run devcontainer up on the checkout with the host's git identity."""
    run(
        'devcontainer',
        'up',
        *flags,
        '--workspace-folder',
        str(REPO_ROOT),
        env={**environ, **git_identity()},
    )


def sync_devcontainer(environ: Mapping[str, str]) -> None:
    """
    Bring the devcontainer up, recreating it when it lacks cloud-session.env.

    A container's environment is fixed at creation, so only a new container picks up the file.
    """
    if any(lacks_session_env(container) for container in devcontainer_ids('-a')):
        log('Recreating the devcontainer, whose environment lacks cloud-session.env')
        devcontainer_up(environ, '--remove-existing-container')
    elif not devcontainer_ids():
        log('Bringing up devcontainer')
        devcontainer_up(environ)


def bring_devcontainer_up(environ: Mapping[str, str]) -> None:
    """Install the CLI, prepare proxy access, and bring the devcontainer up."""
    install_devcontainer_cli()
    prepare_proxy_access(environ)
    sync_devcontainer(environ)


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


def build_devcontainer(environ: Mapping[str, str]) -> None:
    """Install the CLI and build the devcontainer image, pulling what it needs."""
    log('Building devcontainer image')
    install_devcontainer_cli()
    # Bake's fs entitlement check off: see openspec/specs/cloud-session-devcontainer.
    run(
        'devcontainer',
        'build',
        '--workspace-folder',
        str(REPO_ROOT),
        env={**environ, 'BUILDX_BAKE_ENTITLEMENTS_FS': '0'},
    )


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
    timed(build_devcontainer, environ)
    log('Setup complete')


def resume(environ: Mapping[str, str]) -> None:
    """Restart whatever a worker restart stopped; the devcontainer's own sessions skip it."""
    if not is_cloud_host(environ):
        return
    start_docker()
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
