"""Tests for the standalone OpenCode server command and supervised Xpra behind a proxy."""

from __future__ import annotations

import base64
from collections.abc import Iterator
from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time
import urllib.error
import urllib.request
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

REPO_ROOT = Path(__file__).resolve().parents[2]
COMMAND = REPO_ROOT / '.devcontainer/scripts/opencode-web-command.sh'
START_XPRA = REPO_ROOT / 'docker/desktop/start-xpra.sh'
PASSWORD = 'p@ss "quoted" \\ word'
XPRA_SECRET = 'xpra-ingress-secret'


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


@pytest.fixture
def scratch() -> Iterator[Path]:
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'ingress-{uuid4().hex[:8]}'
    (root / 'home').mkdir(parents=True)
    (root / 'workspace').mkdir()
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def fake_tools(root: Path) -> Path:
    """Write an opencode that records its start and a browser opener that must not run."""
    bin_dir = root / 'bin'
    bin_dir.mkdir()
    (bin_dir / 'opencode').write_text(
        f'#!/bin/sh\necho "$PWD|$DISPLAY|$*" > "{root}/opencode.log"\n'
    )
    (bin_dir / 'xdg-open').write_text(f'#!/bin/sh\ntouch "{root}/browser-opened"\n')
    for tool in bin_dir.iterdir():
        tool.chmod(0o755)
    return bin_dir


def command_env(root: Path, bin_dir: Path | None = None, **extra: str) -> dict[str, str]:
    path = f'{bin_dir}:{os.environ["PATH"]}' if bin_dir else os.environ['PATH']
    return {
        'PATH': path,
        'HOME': str(root / 'home'),
        'DEV_WORKSPACE_FOLDER': str(root / 'workspace'),
        'DISPLAY': ':100',
        **extra,
    }


@pytest.mark.parametrize('password', [None, ''])
def test_serve_requires_a_nonempty_password(scratch: Path, password: str | None):
    env = command_env(scratch, fake_tools(scratch))
    if password is not None:
        env['OPENCODE_SERVER_PASSWORD'] = password
    result = subprocess.run([COMMAND, 'serve'], env=env, capture_output=True, text=True)
    assert result.returncode == 1
    assert 'OPENCODE_SERVER_PASSWORD must be set' in result.stderr
    assert not (scratch / 'opencode.log').exists()


def test_serve_binds_the_proxy_network_and_keeps_display(scratch: Path):
    env = command_env(scratch, fake_tools(scratch), OPENCODE_SERVER_PASSWORD='x')
    result = subprocess.run([COMMAND, 'serve'], env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    workdir, display, args = (scratch / 'opencode.log').read_text().strip().split('|')
    assert (workdir, display) == (str(scratch / 'workspace'), ':100')
    assert args == 'serve --port 4096 --hostname 0.0.0.0'


def test_coder_pane_serves_without_display(scratch: Path):
    for password, host in (('', '127.0.0.1'), ('x', '0.0.0.0')):
        printed = subprocess.run(
            [COMMAND, 'coder-pane'],
            capture_output=True,
            text=True,
            check=True,
            env=command_env(scratch, OPENCODE_SERVER_PASSWORD=password),
        ).stdout.strip()
        assert f'exec env -u DISPLAY opencode serve --port 4096 --hostname {host}' in printed


def request(
    port: int, path: str, *, auth: str | None, method: str = 'GET', body: dict | None = None
) -> tuple[int, bytes]:
    req = urllib.request.Request(f'http://127.0.0.1:{port}{path}', method=method)
    if auth is not None:
        req.add_header('Authorization', 'Basic ' + base64.b64encode(auth.encode()).decode())
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req, data, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except (urllib.error.URLError, ConnectionError):
        return 0, b''


def websocket_status(
    port: int, path: str, auth: str | None = None, protocol: str | None = None
) -> str:
    """Send a WebSocket upgrade and return the response status line."""
    headers = [
        f'GET {path} HTTP/1.1',
        f'Host: 127.0.0.1:{port}',
        'Upgrade: websocket',
        'Connection: Upgrade',
        f'Sec-WebSocket-Key: {base64.b64encode(os.urandom(16)).decode()}',
        'Sec-WebSocket-Version: 13',
    ]
    if auth is not None:
        headers.append('Authorization: Basic ' + base64.b64encode(auth.encode()).decode())
    if protocol is not None:
        headers.append(f'Sec-WebSocket-Protocol: {protocol}')
    with socket.create_connection(('127.0.0.1', port), timeout=10) as conn:
        conn.sendall(('\r\n'.join(headers) + '\r\n\r\n').encode())
        return conn.recv(4096).split(b'\r\n', 1)[0].decode()


def wait_for(predicate, timeout: float = 60) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.3)
    return False


@pytest.fixture
def opencode_server(scratch: Path) -> Iterator[tuple[Path, int, dict[str, str]]]:
    if shutil.which('opencode') is None:
        pytest.skip('requires opencode')
    port = free_port()
    subprocess.run(['git', 'init', '-q'], cwd=scratch / 'workspace', check=True)
    bin_dir = scratch / 'bin'
    bin_dir.mkdir()
    (bin_dir / 'xdg-open').write_text(f'#!/bin/sh\ntouch "{scratch}/browser-opened"\n')
    (bin_dir / 'xdg-open').chmod(0o755)
    env = command_env(
        scratch, bin_dir, OPENCODE_SERVER_PASSWORD=PASSWORD, AGENTDEV_OPENCODE_PORT=str(port)
    )
    server = subprocess.Popen(
        [COMMAND, 'serve'], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    try:
        ready = wait_for(lambda: subprocess.run([COMMAND, 'probe'], env=env).returncode == 0)
        assert ready, 'authenticated readiness never passed'
        yield scratch, port, env
    finally:
        server.terminate()
        server.wait(timeout=30)


def test_opencode_rejects_api_requests_without_its_password(opencode_server):
    _, port, env = opencode_server
    assert request(port, '/api/info', auth=None)[0] == 401
    assert request(port, '/api/info', auth='opencode:wrong')[0] == 401
    status, body = request(port, '/api/info', auth=f'opencode:{PASSWORD}')
    shipped = subprocess.run(
        ['opencode', '--version'], capture_output=True, text=True, check=True
    ).stdout
    assert status == 200 and json.loads(body)['version'] in shipped
    assert subprocess.run([COMMAND, 'probe'], env=env).returncode == 0
    wrong = {**env, 'OPENCODE_SERVER_PASSWORD': 'wrong'}
    assert subprocess.run([COMMAND, 'probe'], env=wrong).returncode != 0


def test_opencode_serves_its_web_ui_and_websockets_at_the_root(opencode_server):
    root, port, _ = opencode_server
    auth = f'opencode:{PASSWORD}'
    status, page = request(port, '/', auth=None)
    assert status == 200 and re.search(rb'<title\b[^>]*>OpenCode</title>', page)
    asset = page.split(b'src="', 1)[1].split(b'"', 1)[0].decode()
    assert request(port, asset, auth=None)[0] == 200
    marker = root / 'display.txt'
    status, body = request(
        port,
        '/api/pty',
        auth=auth,
        method='POST',
        body={
            'command': 'bash',
            'args': ['-c', f'echo "$DISPLAY" > {marker}; sleep 30'],
        },
    )
    assert status == 200, body
    pty = json.loads(body)['data']['id']
    connect = f'/api/pty/{pty}/connect'
    assert websocket_status(port, connect, auth).startswith('HTTP/1.1 101')
    assert websocket_status(port, connect).split()[1] == '401'
    assert wait_for(marker.exists, 10)
    assert marker.read_text().strip() == ':100', 'agent child processes keep DISPLAY'
    assert not (root / 'browser-opened').exists()


def xpra_env(scratch: Path, password: str | None) -> dict[str, str]:
    env = {
        'PATH': os.environ['PATH'],
        'HOME': str(scratch / 'home'),
        'XPRA_HOST': '127.0.0.1',
        'XDG_RUNTIME_DIR': str(scratch / 'run'),
    }
    if password is not None:
        env['XPRA_PASSWORD'] = password
    (scratch / 'run').mkdir(mode=0o700, exist_ok=True)
    return env


@contextmanager
def supervised_xpra(scratch: Path, password: str | None) -> Iterator[tuple[int, dict[str, str]]]:
    if shutil.which('xpra') is None:
        pytest.skip('requires xpra')
    port = free_port()
    display = f':{200 + (os.getpid() + port) % 500}'
    env = xpra_env(scratch, password)
    server = subprocess.Popen(
        [START_XPRA, '--supervised', '--port', str(port), '--display', display],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        assert wait_for(lambda: request(port, '/', auth=None)[0] == 200, 90)
        yield port, {**env, 'XPRA_DISPLAY': display, 'XPRA_PID': str(server.pid)}
    finally:
        server.terminate()
        try:
            server.wait(timeout=30)
        except subprocess.TimeoutExpired:
            server.kill()


@pytest.fixture
def xpra(scratch: Path) -> Iterator[tuple[int, dict[str, str]]]:
    with supervised_xpra(scratch, XPRA_SECRET) as server:
        yield server


def xpra_session(scratch: Path, port: int, password: str | None) -> int:
    """Open an Xpra client session over TCP and return the client's exit status."""
    args = ['xpra', 'info', f'tcp://127.0.0.1:{port}/']
    if password is not None:
        secret = scratch / f'client-{uuid4().hex[:8]}'
        secret.write_text(password)
        args.append(f'--password-file={secret}')
    env = {'PATH': os.environ['PATH'], 'HOME': str(scratch / 'home')}
    return subprocess.run(
        args, env=env, stdin=subprocess.DEVNULL, capture_output=True, timeout=60
    ).returncode


def test_supervised_xpra_serves_its_client_but_sessions_need_the_password(xpra, scratch: Path):
    port, env = xpra
    status, page = request(port, '/', auth=None)
    assert status == 200 and b'<html' in page.lower()
    # The HTML5 client negotiates Xpra's binary subprotocol, then authenticates inside it.
    assert websocket_status(port, '/', protocol='binary').split()[1] == '101'
    assert xpra_session(scratch, port, None) != 0
    assert xpra_session(scratch, port, 'wrong') != 0
    assert xpra_session(scratch, port, XPRA_SECRET) == 0
    cmdline = Path(f'/proc/{env["XPRA_PID"]}/cmdline').read_bytes()
    assert b'xpra' in cmdline and XPRA_SECRET.encode() not in cmdline


def test_supervised_xpra_without_a_password_keeps_sessions_open(scratch: Path):
    with supervised_xpra(scratch, None) as (port, _):
        assert xpra_session(scratch, port, None) == 0


def test_supervised_xpra_refuses_to_duplicate_a_live_session(xpra):
    port, env = xpra
    duplicate = subprocess.run(
        [START_XPRA, '--supervised', '--port', str(free_port()), '--display', env['XPRA_DISPLAY']],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert duplicate.returncode == 1
    assert 'already live' in duplicate.stdout
    assert request(port, '/', auth=None)[0] == 200


def test_supervised_xpra_reclaims_the_display_after_a_crash(scratch: Path):
    if shutil.which('xpra') is None:
        pytest.skip('requires xpra')
    port, display = free_port(), f':{700 + os.getpid() % 200}'
    env = xpra_env(scratch, XPRA_SECRET)
    command = [START_XPRA, '--supervised', '--port', str(port), '--display', display]
    crashed = subprocess.Popen(
        command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    replacement = None
    try:
        assert wait_for(lambda: request(port, '/', auth=None)[0] == 200, 90)
        crashed.kill()
        crashed.wait(timeout=30)
        replacement = subprocess.Popen(
            command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        assert wait_for(lambda: request(port, '/', auth=None)[0] == 200, 90)
        assert replacement.poll() is None
    finally:
        for process in (crashed, replacement):
            if process is not None and process.poll() is None:
                process.terminate()
                process.wait(timeout=30)
