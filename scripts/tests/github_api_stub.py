"""A local HTTP stub of the GitHub Actions runs API that a test starts and owns."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading
from urllib.parse import parse_qs, urlsplit

REPOSITORY = 'owner/repo'
RUN_ID = '900'
WORKFLOW_ID = 42


@dataclass
class ActionsApi:
    """The runs one workflow has, served the way the REST API lists them."""

    runs: list[dict] = field(default_factory=list)
    fail: bool = False
    requests: list[str] = field(default_factory=list)
    url: str = ''

    def env(self) -> dict[str, str]:
        """Return the environment a CI step reading this API would have."""
        return {
            'GITHUB_API_URL': self.url,
            'GITHUB_REPOSITORY': REPOSITORY,
            'GITHUB_RUN_ID': RUN_ID,
            'GH_TOKEN': 'token',
        }

    def respond(self, path: str) -> tuple[int, object]:
        """Return the status and body for one GET."""
        self.requests.append(path)
        if self.fail:
            return 500, {'message': 'stub failure'}
        parts = urlsplit(path)
        prefix = f'/repos/{REPOSITORY}/actions'
        if parts.path == f'{prefix}/runs/{RUN_ID}':
            own = next((run for run in self.runs if str(run['id']) == RUN_ID), {})
            return 200, {'id': int(RUN_ID), 'workflow_id': WORKFLOW_ID, **own}
        if parts.path == f'{prefix}/workflows/{WORKFLOW_ID}/runs':
            query = {key: values[0] for key, values in parse_qs(parts.query).items()}
            runs = [
                run
                for run in self.runs
                if run.get('head_branch', 'main') == query.get('branch')
                and ('status' not in query or run.get('conclusion') == query['status'])
            ]
            runs.sort(key=lambda run: run['created_at'], reverse=True)
            return 200, {'total_count': len(runs), 'workflow_runs': runs}
        return 404, {'message': 'Not Found'}


@contextmanager
def serve(api: ActionsApi) -> Iterator[ActionsApi]:
    """Serve api on a local port for the duration of the block."""

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            status, body = api.respond(self.path)
            payload = json.dumps(body).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_: object) -> None:
            """Keep the test output quiet."""

    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    api.url = f'http://127.0.0.1:{server.server_port}'
    try:
        yield api
    finally:
        server.shutdown()
        server.server_close()


def run(run_id: int, created_at: str, *, conclusion: str | None, sha: str = '') -> dict:
    """Return a push run on main as the API lists it."""
    return {
        'id': run_id,
        'head_branch': 'main',
        'head_sha': sha or f'{run_id:040x}',
        'created_at': created_at,
        'status': 'completed' if conclusion else 'in_progress',
        'conclusion': conclusion,
    }
