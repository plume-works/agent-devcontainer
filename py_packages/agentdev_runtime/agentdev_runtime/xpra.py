"""
Start an Xpra server with the HTML5 web client enabled.

``--supervised`` replaces this process with a foreground Xpra for the supervisor;
``--background`` starts a daemon and returns; ``--stop`` stops the session on the display.
Spec: xpra-port-forwarding.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time
from typing import NoReturn

from agentdev_runtime import settings as env

DEFAULT_PORT = '14500'
DEFAULT_DISPLAY = ':100'
USAGE = """\
Usage: agentdev-runtime xpra [--host HOST] [--port PORT] [--display DISPLAY] [--background|--supervised] [--stop]

Start an Xpra server with the HTML5 web client enabled.

Options:
  --port PORT       Container HTTP port for the HTML5 client (default: 14500)
  --host HOST       Host/IP to bind the Xpra server (default: XPRA_HOST or 127.0.0.1)
  --display DISPLAY X display (accepts :100 or 100; default: :100)
  --background      Start Xpra in the background and exit immediately
  --supervised      Replace this process with a foreground Xpra for a supervisor; a
                    missing xpra or an already-live session is an error
  --stop            Stop the Xpra server and clean up resources

Environment:
  XPRA_HOST         Override the default bind host
  XPRA_PASSWORD     When set, every TCP/WebSocket session must authenticate with it"""


def normalize_display(display: str) -> str:
    return display if display.startswith(':') else f':{display}'


def lock_pid(number: str) -> int | None:
    try:
        digits = re.sub(r'[^0-9]', '', Path(f'/tmp/.X{number}-lock').read_text())
    except OSError:
        return None
    return int(digits) if digits else None


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def session_running(display: str) -> bool:
    try:
        listed = subprocess.run(
            ['xpra', 'list'], capture_output=True, text=True, check=False
        ).stdout
    except OSError:
        return False
    return f'LIVE session at {display}' in listed


def port_in_use(port: str) -> bool:
    if shutil.which('lsof'):
        command = ['lsof', f'-iTCP:{port}', '-sTCP:LISTEN', '-n', '-P']
    elif shutil.which('fuser'):
        command = ['fuser', f'{port}/tcp']
    else:
        return False
    return subprocess.run(command, capture_output=True, check=False).returncode == 0


def ensure_display_lock_is_clear(display: str) -> None:
    number = display[1:]
    lock_file = Path(f'/tmp/.X{number}-lock')
    if not lock_file.is_file():
        return
    pid = lock_pid(number)
    if pid is not None and alive(pid):
        print(f'Error: display {display} is in use by PID {pid}.')
        print('Use --display with a different number, or stop the existing X server.')
        raise SystemExit(1)
    print(f'Removing stale X lock for display {display}: {lock_file}')
    lock_file.unlink(missing_ok=True)
    socket_file = Path(f'/tmp/.X11-unix/X{number}')
    if socket_file.is_socket():
        socket_file.unlink(missing_ok=True)


def reclaim_orphaned_display(display: str) -> None:
    """
    Stop an X server a killed Xpra left holding the display.

    Xpra starts its X server in a separate session, so with no live session on the display, a
    lock held by Xpra's own X server can only be such a leftover.
    """
    number = display[1:]
    pid = lock_pid(number)
    if pid is None or not alive(pid):
        return
    try:
        cmdline = Path(f'/proc/{pid}/cmdline').read_bytes().replace(b'\0', b' ').decode()
    except OSError:
        return
    # Xpra 3 names it Xvfb-for-Xpra-:N, Xpra 6 Xvfb-for-Xpra-N.
    if not re.search(rf'-for-Xpra-:?{re.escape(number)} ', cmdline):
        return
    print(f'Stopping X server PID {pid} left on {display} by a previous Xpra.')
    try:
        os.kill(pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    for _ in range(50):
        if not alive(pid):
            return
        time.sleep(0.1)
    try:
        os.kill(pid, signal.SIGKILL)
    except ProcessLookupError:
        return


def detect_gpu() -> bool:
    if (
        shutil.which('nvidia-smi')
        and subprocess.run(['nvidia-smi'], capture_output=True, check=False).returncode == 0
    ):
        print('NVIDIA GPU detected')
        return True
    dri = Path('/dev/dri')
    if dri.is_dir() and any(dri.iterdir()):
        print('DRI GPU device detected')
        return True
    print('No GPU detected, using software rendering')
    return False


def setup_gpu_rendering() -> None:
    if not shutil.which('vglrun'):
        print('Warning: VirtualGL not found, GPU acceleration will not be available')
        return
    os.environ['VGL_DISPLAY'] = ':0'
    print("GPU detected. Use 'vglrun <app>' for GPU-accelerated rendering (e.g., 'vglrun rviz2')")


def cleanup(display: str, port: str) -> NoReturn:
    print('Shutting down Xpra server...', flush=True)
    if shutil.which('xpra'):
        if session_running(display):
            subprocess.run(['xpra', 'stop', display], capture_output=True, check=False)
            time.sleep(1)
            if session_running(display):
                subprocess.run(['xpra', 'exit', display], capture_output=True, check=False)
        else:
            print(f'Xpra server on {display} is not running; nothing to stop.')
    if port_in_use(port):
        print(f'Warning: TCP port {port} is still in use after cleanup.')
    raise SystemExit(0)


def xpra_args(display: str, host: str, port: str, daemon: bool, encoders: str) -> list[str]:
    args = [
        display,
        f'--bind-tcp={host}:{port}',
        '--html=on',
        f'--daemon={"yes" if daemon else "no"}',
        '--mdns=no',
        '--notifications=no',
        '--start-new-commands=no',
        '--dbus-control=no',
        '--dbus-launch=',
        '--webcam=no',
        '--opengl=yes',
        f'--video-encoders={encoders}',
    ]
    # Xpra reads the secret from its own environment, so it never reaches the command line.
    if os.environ.get('XPRA_PASSWORD'):
        args.append('--tcp-auth=env:name=XPRA_PASSWORD')
    return args


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:
        print(f'Error: {message}')
        print(USAGE)
        raise SystemExit(1)


def parse(argv: list[str]) -> argparse.Namespace:
    parser = Parser(add_help=False, usage=USAGE)
    parser.add_argument('--host')
    parser.add_argument('--port', default=DEFAULT_PORT)
    parser.add_argument('--display', default=DEFAULT_DISPLAY)
    parser.add_argument('--background', action='store_true')
    parser.add_argument('--supervised', action='store_true')
    parser.add_argument('--stop', action='store_true')
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    settings = env.Settings()
    args = parse(argv)
    host = args.host or settings.get('XPRA_HOST')
    port = args.port
    display = normalize_display(args.display)
    if args.stop:
        cleanup(display, port)
    signal.signal(signal.SIGTERM, lambda *_: cleanup(display, port))
    signal.signal(signal.SIGINT, lambda *_: cleanup(display, port))
    print('==========================================')
    print('Xpra Server Startup')
    print('==========================================')
    print(f'Port: {port}')
    print(f'Display: {display}', flush=True)
    installed = shutil.which('xpra') is not None
    if args.supervised:
        if not installed:
            print('Error: xpra is not installed.')
            return 1
        if session_running(display):
            print(
                f'Error: an Xpra session is already live on {display}; refusing to start a duplicate.'
            )
            return 1
    if not installed:
        print('Warning: xpra not found. Skipping startup.')
        return 0
    if session_running(display):
        print(f'Xpra already running on {display}. Skipping startup.')
        return 0
    if args.supervised:
        reclaim_orphaned_display(display)
    ensure_display_lock_is_clear(display)
    if detect_gpu():
        setup_gpu_rendering()
    os.environ['DISPLAY'] = display
    print()
    print('Starting Xpra server...')
    print(f'HTML5 container address: http://{host}:{port}')
    print("For browser access, open the forwarded address in VS Code's Ports panel.")
    print(flush=True)
    start = [
        'xpra',
        'start',
        *xpra_args(display, host, port, args.background, settings.get('XPRA_VIDEO_ENCODERS')),
    ]
    if args.background:
        return background(start, display, Path(settings.get('XPRA_LOG_FILE')))
    if args.supervised:
        # The supervisor signals and reaps Xpra itself, so no process stays in between.
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        os.execvp(start[0], start)
    if subprocess.run(start, check=False).returncode != 0:
        print('Warning: Xpra failed to start. Check ~/.xpra/logs/ for details.')
        return 1
    return 0


def background(start: list[str], display: str, log_file: Path) -> int:
    print('Starting Xpra in background mode...', flush=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    if subprocess.run([*start, f'--log-file={log_file}'], check=False).returncode != 0:
        print(f'Warning: Xpra failed to start in background mode. Check {log_file}.')
        return 1
    for _ in range(10):
        if session_running(display):
            return 0
        time.sleep(1)
    if session_running(display):
        return 0
    print(f'Warning: Xpra background startup did not produce a live session on {display}.')
    print(f'Check {log_file} for diagnostics.')
    return 1
