"""
Seed per-test OpenCode servers from the web UI server's ChatGPT credential.

Only the source server ever holds or rotates the real refresh token; each test
server gets the access token with ``refresh`` withheld. No credential value is
ever placed in an exception message, a log, or a transcript.
"""

import base64
from dataclasses import dataclass
import json
import os
from pathlib import Path
import time
from typing import Any
import urllib.error
import urllib.request

PORT_ENV = 'AGENTDEV_OPENCODE_PORT'
DEFAULT_PORT = 4096
PASSWORD_ENV = 'OPENCODE_SERVER_PASSWORD'
PASSWORD_FILE = '.local/share/opencode/agentdev-server-password'
USERNAME = 'opencode'
START_SCRIPT = '.devcontainer/scripts/opencode-web-start.sh'
INTEGRATION = 'openai'
WITHHELD = 'withheld'
REFRESH_MODEL = {'providerID': 'openai', 'id': 'gpt-6-luna'}
REFRESH_PROMPT = 'Reply with the single word: ok'
REQUEST_TIMEOUT = 30.0
# Epoch values above this are milliseconds.
_MILLISECONDS_FLOOR = 10**12


class SourceUnavailable(RuntimeError):
    """No authenticated OpenCode 2.x server answers where the web UI runs."""


class CredentialError(RuntimeError):
    """The source has no usable credential; the message never carries its value."""


class HttpError(RuntimeError):
    """An OpenCode HTTP request failed."""

    def __init__(self, method: str, path: str, status: int, detail: str) -> None:
        """Record the failed request; ``detail`` must never carry a secret."""
        super().__init__(f'{method} {path} -> {status}{": " + detail if detail else ""}')
        self.status = status


@dataclass(frozen=True)
class Server:
    """An OpenCode server reached over HTTP with Basic auth."""

    url: str
    password: str

    def request(
        self,
        method: str,
        path: str,
        body: Any = None,
        *,
        timeout: float = REQUEST_TIMEOUT,
        secret: bool = False,
    ) -> Any:
        """Send one request and return its decoded JSON body, or ``None`` when empty."""
        data = None if body is None else json.dumps(body).encode()
        token = base64.b64encode(f'{USERNAME}:{self.password}'.encode()).decode()
        headers = {'Authorization': f'Basic {token}', 'Accept': 'application/json'}
        if data is not None:
            headers['Content-Type'] = 'application/json'
        req = urllib.request.Request(self.url + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                raw = response.read()
        except urllib.error.HTTPError as error:
            detail = '' if secret else error.read().decode(errors='replace')[:2000]
            raise HttpError(method, path, error.code, detail) from None
        if not raw:
            return None
        return json.loads(raw)


def source_from_environment(
    environ: dict[str, str] | None = None, home: Path | None = None
) -> Server:
    """Locate the web UI server the way ``opencode-web-start.sh`` configures it."""
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else home
    port = environ.get(PORT_ENV) or str(DEFAULT_PORT)
    password = environ.get(PASSWORD_ENV)
    if not password:
        password_file = home / PASSWORD_FILE
        if password_file.is_file():
            password = password_file.read_text().strip()
    if not password:
        raise SourceUnavailable(
            f'no {PASSWORD_ENV} and no {password_file}; start the web UI with {START_SCRIPT}'
        )
    return Server(f'http://127.0.0.1:{port}', password)


def require_v2(server: Server) -> str:
    """
    Return the server's version, or raise unless an authenticated 2.x server answers.

    v2 serves its web UI page outside ``/api/`` with status 200 and no password,
    so only an authenticated ``/api/info`` shows the API is up.
    """
    try:
        info = server.request('GET', '/api/info', timeout=5.0)
    except (OSError, HttpError, ValueError) as error:
        raise SourceUnavailable(
            f'no OpenCode 2.x API at {server.url} ({error}); start it with {START_SCRIPT}'
        ) from None
    version = str(info.get('version', '')) if isinstance(info, dict) else ''
    if not version.startswith('2.'):
        raise SourceUnavailable(
            f'{server.url} is not OpenCode 2.x (version {version or "unknown"}); '
            f'start it with {START_SCRIPT}'
        )
    return version


def active_credential(server: Server) -> dict[str, Any]:
    """Return the active ``openai`` OAuth credential entry the source holds."""
    entries = server.request('GET', '/api/credential', secret=True)['data']
    for entry in entries:
        if entry.get('integrationID') == INTEGRATION and entry.get('active'):
            if entry['value'].get('type') != 'oauth':
                raise CredentialError(f'the active {INTEGRATION} credential is not a login')
            return entry
    raise CredentialError(f'{server.url} has no active {INTEGRATION} credential; log in there')


def seconds_left(entry: dict[str, Any], now: float | None = None) -> float:
    """Return how long the entry's access token stays valid."""
    now = time.time() if now is None else now
    expires = float(entry['value']['expires'])
    if expires > _MILLISECONDS_FLOOR:
        expires /= 1000
    return expires - now


def nudge_refresh(server: Server, timeout: float) -> None:
    """Make the source refresh its token with a one-word prompt in a throwaway session."""
    session = server.request(
        'POST',
        '/api/session',
        {
            'title': 'e2e credential refresh',
            'model': REFRESH_MODEL,
            'permissions': [{'action': '*', 'resource': '*', 'effect': 'deny'}],
        },
    )['data']['id']
    try:
        server.request('POST', f'/api/session/{session}/prompt', {'text': REFRESH_PROMPT})
        server.request('POST', f'/api/experimental/session/{session}/wait', timeout=timeout)
    finally:
        server.request('DELETE', f'/api/session/{session}')


def fresh_credential(server: Server, budget: float, refresh_timeout: float = 120.0) -> dict:
    """Return the active credential, refreshed first when it expires within ``budget``."""
    entry = active_credential(server)
    if seconds_left(entry) >= budget:
        return entry
    nudge_refresh(server, refresh_timeout)
    entry = active_credential(server)
    left = seconds_left(entry)
    if left < budget:
        raise CredentialError(
            f'the source did not refresh its {INTEGRATION} token: {left:.0f}s left, '
            f'{budget:.0f}s needed'
        )
    return entry


def seed_value(entry: dict[str, Any]) -> dict[str, Any]:
    """Return the payload that seeds a test server, the refresh token withheld."""
    value = entry['value']
    seeded = {
        'type': 'oauth',
        'methodID': value['methodID'],
        'access': value['access'],
        'expires': value['expires'],
        'refresh': WITHHELD,
    }
    if 'metadata' in value:
        seeded['metadata'] = value['metadata']
    return {
        'integrationID': entry['integrationID'],
        'label': entry.get('label') or 'e2e',
        'value': seeded,
        'activate': True,
    }


def seed(target: Server, entry: dict[str, Any]) -> None:
    """Store the withheld-refresh copy of ``entry`` as the target's active credential."""
    target.request('POST', '/api/credential', seed_value(entry), secret=True)
