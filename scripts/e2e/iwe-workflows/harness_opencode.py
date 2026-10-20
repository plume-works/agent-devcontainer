"""
Drive one isolated OpenCode 2.x server per test over its HTTP API.

The server gets its own ``HOME``, ``XDG_*``, config directory, and password,
loads the agentdev bridge from the clone's own catalog, and is seeded with the
source's login before any session starts.
"""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import secrets
import shutil
import signal
import socket
import subprocess
import time
from typing import Any
import urllib.parse

from clone import Clone, FIXTURES
from opencode_credential import HttpError, seed, Server

MODEL = {'providerID': 'openai', 'id': 'gpt-6.1-sol'}
# No one answers the question tool here; denying it makes questions plain text.
PERMISSIONS = [{'action': 'question', 'resource': '*', 'effect': 'deny'}]
READY_TIMEOUT = 30.0
CATALOG_TIMEOUT = 60.0
READY_COMMAND = 'agentdev:iwe-ship'
# The suffix of the provider's refusal codes for a login over its usage limit.
USAGE_LIMIT_CODE = 'usage_limit_exceeded'
PAGE = 200
# One wait request is renewed until the test's deadline; the server may end it early.
WAIT_SLICE = 300.0
_INHERITED_CONFIG = (
    'OPENCODE_CONFIG',
    'OPENCODE_CONFIG_CONTENT',
    'OPENCODE_SERVER_USERNAME',
    'OPENCODE_PURE',
    'OPENCODE_DISABLE_PROJECT_CONFIG',
)


def free_port() -> int:
    """Return a localhost port nothing is listening on right now."""
    with socket.socket() as probe:
        probe.bind(('127.0.0.1', 0))
        return probe.getsockname()[1]


def render_config(clone: Clone) -> dict[str, Any]:
    """Return the server config: the fixture's permissions and small model, the clone's bridge."""
    catalog = clone.path / '.agents/plugins/agentdev'
    text = (FIXTURES / 'opencode.json').read_text()
    text = text.replace('@WORK@', str(clone.path.parent)).replace('@CATALOG@', str(catalog))
    return json.loads(text)


def isolated_env(root: Path, password: str) -> dict[str, str]:
    """Return an environment whose OpenCode state and git identity all live under ``root``."""
    env = {k: v for k, v in os.environ.items() if k not in _INHERITED_CONFIG}
    env.update(
        HOME=str(root / 'home'),
        XDG_CONFIG_HOME=str(root / 'config'),
        XDG_DATA_HOME=str(root / 'data'),
        XDG_CACHE_HOME=str(root / 'cache'),
        XDG_STATE_HOME=str(root / 'state'),
        OPENCODE_CONFIG_DIR=str(root / 'config/opencode'),
        OPENCODE_SERVER_PASSWORD=password,
        OPENCODE_DISABLE_EXTERNAL_SKILLS='1',
        OPENCODE_DISABLE_CLAUDE_CODE_SKILLS='1',
        GIT_AUTHOR_NAME='e2e',
        GIT_AUTHOR_EMAIL='e2e@example.invalid',
        GIT_COMMITTER_NAME='e2e',
        GIT_COMMITTER_EMAIL='e2e@example.invalid',
    )
    for key in ('HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME', 'XDG_STATE_HOME'):
        Path(env[key]).mkdir(parents=True, exist_ok=True)
    Path(env['OPENCODE_CONFIG_DIR']).mkdir(parents=True, exist_ok=True)
    return env


@dataclass
class Transcript:
    """Every message of one session, as the server returned them."""

    path: Path
    messages: list[dict[str, Any]]
    timed_out: bool = False

    def assistant_parts(self) -> list[dict[str, Any]]:
        """Return the content parts of every assistant message."""
        return [
            part
            for message in self.messages
            if message.get('type') == 'assistant'
            for part in message.get('content') or []
        ]

    def errors(self) -> list[dict[str, Any]]:
        """Return the error of every assistant message that failed."""
        return [
            message['error']
            for message in self.messages
            if message.get('type') == 'assistant' and message.get('error')
        ]

    def completed(self) -> bool:
        """Whether the agent answered with text and no assistant message failed."""
        return not self.errors() and any(
            part.get('type') == 'text' for part in self.assistant_parts()
        )

    def auth_expired(self) -> bool:
        """Whether a model call failed on the seeded login."""
        return '"provider.auth"' in json.dumps(self.messages)

    def usage_limited(self) -> bool:
        """Whether the provider refused a model call because the login is over its usage limit."""
        return USAGE_LIMIT_CODE in json.dumps(self.messages)

    def failure_reason(self, budget: float) -> str | None:
        """Explain why the run failed, or return ``None`` for a clean, timely completion."""
        if self.usage_limited():
            return f'the seeded login is over its usage limit ({USAGE_LIMIT_CODE}); wait for it to reset'
        if self.auth_expired():
            return 'budget exhausted: the seeded login expired (provider.auth)'
        if self.timed_out:
            return f'budget exhausted: still running after {budget:.0f}s, interrupted'
        if errors := self.errors():
            error = errors[-1]
            return f'assistant message failed: {error.get("type")}: {error.get("message", "")}'
        if not self.completed():
            return 'no assistant text'
        return None

    def calls(self, tool: str) -> list[dict[str, Any]]:
        """Return the input of every call to ``tool``."""
        return [
            (part.get('state') or {}).get('input') or {}
            for part in self.assistant_parts()
            if part.get('type') == 'tool' and part.get('name') == tool
        ]

    def excerpt(self, tool: str | None = None, limit: int = 4000) -> str:
        """Return the tail of the transcript, or of one tool's calls, for a failure message."""
        if tool is not None:
            text = '\n'.join(json.dumps(call) for call in self.calls(tool)) or f'(no {tool} calls)'
        else:
            text = '\n'.join(
                part.get('text', '')
                for part in self.assistant_parts()
                if part.get('type') == 'text'
            )
        return f'{self.path}:\n{text[-limit:]}'


@dataclass
class OpenCodeServer:
    """One running ``opencode serve`` process and the clone it serves."""

    clone: Clone
    root: Path
    process: subprocess.Popen
    server: Server
    log: Path
    sessions: list[str] = field(default_factory=list)

    def stop(self) -> None:
        """Kill the server's whole process group, whatever state it is in."""
        if self.process.poll() is None:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                # The group exited between the poll and the kill.
                return
            self.process.wait()

    def _located(self, path: str) -> str:
        query = urllib.parse.urlencode({'location[directory]': str(self.clone.path)})
        return f'{path}?{query}'

    def commands(self) -> list[str]:
        """Return the command names served for the clone."""
        data = self.server.request('GET', self._located('/api/command'))['data']
        return [command.get('name') for command in data]

    def wait_for_catalog(self, timeout: float = CATALOG_TIMEOUT) -> None:
        """Wait until the bridge serves ``agentdev:*`` commands for the clone."""
        # The bridge activates for a directory on its first request there.
        deadline = time.monotonic() + timeout
        while READY_COMMAND not in self.commands():
            if time.monotonic() > deadline:
                raise RuntimeError(f'{READY_COMMAND} never served for {self.clone.path}')
            self.check_alive()
            time.sleep(0.5)

    def check_alive(self) -> None:
        if self.process.poll() is not None:
            raise RuntimeError(f'opencode exited {self.process.returncode}; see {self.log}')

    def run(self, name: str, command: str, text: str, budget: float) -> Transcript:
        """Run one command in a fresh session located in the clone, and save its transcript."""
        deadline = time.monotonic() + budget
        session = self.server.request(
            'POST',
            '/api/session',
            {
                'model': MODEL,
                'location': {'directory': str(self.clone.path)},
                'permissions': PERMISSIONS,
            },
        )['data']['id']
        self.sessions.append(session)
        self.server.request(
            'POST', f'/api/session/{session}/command', {'name': command, 'text': text}
        )
        timed_out = not self._wait(session, deadline)
        if timed_out:
            self.server.request('POST', f'/api/session/{session}/interrupt')
        transcript = Transcript(
            self.clone.path.parent / 'transcripts' / f'{name}.jsonl',
            self.messages(session),
            timed_out=timed_out,
        )
        transcript.path.parent.mkdir(parents=True, exist_ok=True)
        transcript.path.write_text(''.join(json.dumps(m) + '\n' for m in transcript.messages))
        return transcript

    def _wait(self, session: str, deadline: float) -> bool:
        """Wait for the session to go idle; return False when the deadline passes first."""
        while (left := deadline - time.monotonic()) > 0:
            self.check_alive()
            try:
                self.server.request(
                    'POST',
                    f'/api/experimental/session/{session}/wait',
                    timeout=min(left, WAIT_SLICE),
                )
                return True
            except TimeoutError:
                continue
            except HttpError as error:
                if error.status != 503:
                    raise
        return False

    def messages(self, session: str) -> list[dict[str, Any]]:
        """Return every message of the session, oldest first, across pages."""
        query: dict[str, Any] = {'limit': PAGE, 'order': 'asc'}
        messages: list[dict[str, Any]] = []
        while True:
            path = f'/api/session/{session}/message?{urllib.parse.urlencode(query)}'
            page = self.server.request('GET', path)
            messages.extend(page['data'])
            cursor = (page.get('cursor') or {}).get('next')
            if not cursor or len(page['data']) < PAGE:
                return messages
            query = {'limit': PAGE, 'cursor': cursor}


def start_server(clone: Clone, login: dict[str, Any], binary: str) -> OpenCodeServer:
    """Start, seed, and wait for an isolated server serving the clone's catalog."""
    resolved = shutil.which(binary)
    if resolved is None:
        raise FileNotFoundError(f'no OpenCode binary {binary!r}; set OPENCODE_BIN')
    root = clone.path.parent / 'opencode'
    password = secrets.token_urlsafe(24)
    env = isolated_env(root, password)
    config = Path(env['OPENCODE_CONFIG_DIR']) / 'opencode.json'
    config.write_text(json.dumps(render_config(clone), indent=2))
    port = free_port()
    log = root / 'server.log'
    with log.open('w') as out:
        process = subprocess.Popen(
            [os.path.abspath(resolved), 'serve', '--hostname', '127.0.0.1', '--port', str(port)],
            cwd=clone.path,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
    harness = OpenCodeServer(
        clone=clone,
        root=root,
        process=process,
        server=Server(f'http://127.0.0.1:{port}', password),
        log=log,
    )
    try:
        _wait_ready(harness)
        seed(harness.server, login)
        harness.wait_for_catalog()
    except BaseException:
        harness.stop()
        raise
    return harness


def _wait_ready(harness: OpenCodeServer) -> None:
    deadline = time.monotonic() + READY_TIMEOUT
    while True:
        harness.check_alive()
        try:
            harness.server.request('GET', '/api/info', timeout=2.0)
            return
        except (OSError, HttpError, ValueError):
            if time.monotonic() > deadline:
                raise RuntimeError(f'opencode never answered; see {harness.log}') from None
            time.sleep(0.2)
