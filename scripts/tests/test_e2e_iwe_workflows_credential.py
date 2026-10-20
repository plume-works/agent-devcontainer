"""The IWE workflow suite seeds test servers from the source without leaking a secret."""

import base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import importlib.util
import json
from pathlib import Path
import threading
import time

import pytest

REPO_ROOT = Path(__file__).parents[2]
_spec = importlib.util.spec_from_file_location(
    'e2e_iwe_workflows_credential',
    REPO_ROOT / 'scripts/e2e/iwe-workflows/opencode_credential.py',
)
cred = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(cred)

PASSWORD = 'fake-source-password'
ACCESS = 'fake-access-token-value'
REFRESH = 'fake-refresh-token-value'
METADATA = {'clientID': 'fake-client', 'scopes': ['a', 'b']}


def entry(expires_in: float, access: str = ACCESS) -> dict:
    """Build a fake active ``openai`` login expiring ``expires_in`` seconds from now."""
    return {
        'id': 'cred_fake',
        'integrationID': 'openai',
        'label': 'ChatGPT',
        'active': True,
        'value': {
            'type': 'oauth',
            'methodID': 'chatgpt-token-sharing',
            'refresh': REFRESH,
            'access': access,
            'expires': int((time.time() + expires_in) * 1000),
            'metadata': METADATA,
        },
    }


class FakeSource:
    """A stand-in OpenCode server recording every request it serves."""

    def __init__(self, version: str = '2.0.32') -> None:
        """Serve on a free localhost port."""
        self.version = version
        self.credentials = [entry(3600)]
        self.after_prompt: list[dict] | None = None
        self.calls: list[tuple[str, str, object]] = []
        self.posted: list[dict] = []
        fake = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: object) -> None:
                """Keep test output quiet."""

            def _reply(self, status: int, body: object = None) -> None:
                raw = b'' if body is None else json.dumps(body).encode()
                self.send_response(status)
                self.send_header('Content-Length', str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _handle(self) -> None:
                length = int(self.headers.get('Content-Length') or 0)
                body = json.loads(self.rfile.read(length)) if length else None
                fake.calls.append((self.command, self.path, body))
                token = base64.b64encode(f'opencode:{PASSWORD}'.encode()).decode()
                if self.headers.get('Authorization') != f'Basic {token}':
                    return self._reply(401, {'error': 'unauthorized'})
                route = (self.command, self.path)
                if route == ('GET', '/api/info'):
                    return self._reply(200, {'version': fake.version})
                if route == ('GET', '/api/credential'):
                    return self._reply(200, {'data': fake.credentials})
                if route == ('POST', '/api/credential'):
                    fake.posted.append(body)
                    return self._reply(409, {'echo': body})
                if route == ('POST', '/api/session'):
                    return self._reply(200, {'data': {'id': 'ses_fake'}})
                if route == ('POST', '/api/session/ses_fake/prompt'):
                    if fake.after_prompt is not None:
                        fake.credentials = fake.after_prompt
                    return self._reply(200, {'data': {}})
                if self.command in ('POST', 'DELETE') and self.path.startswith('/api/'):
                    return self._reply(204)
                return self._reply(404, {})

            do_GET = do_POST = do_DELETE = _handle

        self.httpd = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.httpd.server_address[1]}'
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def server(self, password: str = PASSWORD):
        """Return a client for this fake."""
        return cred.Server(self.url, password)

    def routes(self) -> list[tuple[str, str]]:
        """Return the method and path of every request served."""
        return [(method, path) for method, path, _ in self.calls]


@pytest.fixture
def source():
    """Run a fake source server for one test."""
    fake = FakeSource()
    yield fake
    fake.httpd.shutdown()


def test_source_reads_port_and_password_like_the_web_ui(tmp_path):
    """Port from ``AGENTDEV_OPENCODE_PORT``, password from the variable, then the file."""
    server = cred.source_from_environment(
        {'AGENTDEV_OPENCODE_PORT': '47021', 'OPENCODE_SERVER_PASSWORD': 'pw'}, tmp_path
    )
    assert server == cred.Server('http://127.0.0.1:47021', 'pw')

    (tmp_path / cred.PASSWORD_FILE).parent.mkdir(parents=True)
    (tmp_path / cred.PASSWORD_FILE).write_text('from-file\n')
    assert cred.source_from_environment({}, tmp_path) == cred.Server(
        'http://127.0.0.1:4096', 'from-file'
    )


def test_source_without_a_password_names_the_start_script(tmp_path):
    """No password anywhere means no source, and the reason says how to start one."""
    with pytest.raises(cred.SourceUnavailable, match='opencode-web-start.sh'):
        cred.source_from_environment({}, tmp_path)


def test_v2_api_counts_as_up(source):
    """An authenticated ``/api/info`` with a 2.x version is a usable source."""
    assert cred.require_v2(source.server()) == '2.0.32'


@pytest.mark.parametrize('case', ['v1', 'wrong-password', 'nothing-listening'])
def test_anything_else_is_unavailable(source, case):
    """A 1.x server, a rejected password, or a closed port all skip the OpenCode tests."""
    server = source.server()
    if case == 'v1':
        source.version = '1.19.3'
    elif case == 'wrong-password':
        server = source.server('wrong')
    else:
        source.httpd.shutdown()
        source.httpd.server_close()
    with pytest.raises(cred.SourceUnavailable, match='opencode-web-start.sh'):
        cred.require_v2(server)


def test_long_lived_token_is_used_without_a_refresh(source):
    """A token that outlives the budget needs no prompt to the source."""
    got = cred.fresh_credential(source.server(), budget=600)
    assert got['value']['access'] == ACCESS
    assert ('POST', '/api/session') not in source.routes()


def test_expiring_token_is_refreshed_in_a_throwaway_session(source):
    """A token expiring within the budget makes the source refresh it, then the session goes."""
    source.credentials = [entry(60)]
    source.after_prompt = [entry(3600, access='refreshed-access')]
    got = cred.fresh_credential(source.server(), budget=600)
    assert got['value']['access'] == 'refreshed-access'
    routes = source.routes()
    assert routes.index(('POST', '/api/session')) < routes.index(
        ('POST', '/api/session/ses_fake/prompt')
    )
    assert ('POST', '/api/experimental/session/ses_fake/wait') in routes
    assert routes[-2:] == [('DELETE', '/api/session/ses_fake'), ('GET', '/api/credential')]


def test_unrefreshed_token_fails_without_its_value(source):
    """A source that does not refresh fails the test, naming no credential value."""
    source.credentials = [entry(60)]
    with pytest.raises(cred.CredentialError) as raised:
        cred.fresh_credential(source.server(), budget=600)
    assert ACCESS not in str(raised.value)
    assert REFRESH not in str(raised.value)


def test_seed_withholds_the_refresh_token(source):
    """The seeded copy keeps method and metadata verbatim and never the refresh token."""
    seeded = cred.seed_value(entry(3600))
    assert seeded['value']['methodID'] == 'chatgpt-token-sharing'
    assert seeded['value']['metadata'] == METADATA
    assert seeded['value']['refresh'] == cred.WITHHELD
    assert seeded['value']['access'] == ACCESS
    assert seeded['activate'] is True
    assert REFRESH not in json.dumps(seeded)


def test_failed_credential_requests_never_echo_the_body(source):
    """A credential route's error leaves its response body, which may echo secrets, out."""
    with pytest.raises(cred.HttpError) as raised:
        cred.seed(source.server(), entry(3600))
    assert source.posted[0]['value']['refresh'] == cred.WITHHELD
    assert ACCESS not in str(raised.value)
    assert 'POST /api/credential -> 409' in str(raised.value)


def rendered(raised: pytest.ExceptionInfo) -> str:
    """Render a failure the way pytest reports it, with every frame's arguments and locals."""
    return str(raised.getrepr(funcargs=True, showlocals=True))


def test_server_repr_omits_the_password():
    """A server printed in a traceback or an assertion never shows its password."""
    assert PASSWORD not in repr(cred.Server('http://127.0.0.1:1', PASSWORD))


def test_a_failed_seed_renders_no_secret(source):
    """Seeding the source's own login and failing prints no token and no password."""
    login = cred.active_credential(source.server())
    with pytest.raises(cred.HttpError) as raised:
        cred.seed(source.server(), login)
    assert source.posted[0]['value']['access'] == ACCESS
    text = rendered(raised) + repr(login)
    assert [s for s in (ACCESS, REFRESH, PASSWORD) if s in text] == []


def test_a_failed_refresh_renders_no_secret(source):
    """A source that does not refresh fails with no token or password in the traceback."""
    source.credentials = [entry(60)]
    with pytest.raises(cred.CredentialError) as raised:
        cred.fresh_credential(source.server(), budget=600)
    text = rendered(raised)
    assert [s for s in (ACCESS, REFRESH, PASSWORD) if s in text] == []


def test_an_unreachable_target_renders_no_secret(source):
    """A connection failure drops urllib's frames, whose arguments hold the header and body."""
    login = cred.active_credential(source.server())
    source.httpd.shutdown()
    source.httpd.server_close()
    with pytest.raises(OSError) as raised:
        cred.seed(source.server(), login)
    text = rendered(raised)
    assert [s for s in (ACCESS, REFRESH, PASSWORD) if s in text] == []
    assert 'Authorization' not in text
