"""
The IWE workflow suite's isolated OpenCode server, against a real 2.x binary.

Model-free: the login is made up and sessions name a provider that does not
exist. Skipped unless ``OPENCODE_BIN`` names an OpenCode 2.x binary.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import uuid

import pytest

REPO_ROOT = Path(__file__).parents[2]
SUITE = REPO_ROOT / 'scripts/e2e/iwe-workflows'
BINARY = os.environ.get('OPENCODE_BIN', '')


def binary_version() -> str:
    """Return the ``OPENCODE_BIN`` version, or an empty string when there is none."""
    if not BINARY or shutil.which(BINARY) is None:
        return ''
    result = subprocess.run([BINARY, '--version'], capture_output=True, text=True, check=False)
    return result.stdout.strip().removeprefix('opencode v')


pytestmark = pytest.mark.skipif(
    not binary_version().startswith('2.'), reason='set OPENCODE_BIN to an OpenCode 2.x binary'
)


@pytest.fixture(scope='module')
def suite_modules():
    """Import the suite's modules the way its conftest does."""
    sys.path.insert(0, str(SUITE))
    try:
        import clone
        import harness_opencode

        yield clone, harness_opencode
    finally:
        sys.path.remove(str(SUITE))
        for name in ('clone', 'harness_opencode', 'opencode_credential'):
            sys.modules.pop(name, None)


def start(suite_modules, work: Path):
    """Start one isolated server on a fresh clone under ``work`` with a made-up login."""
    clone, harness = suite_modules
    fixture = clone.build_fixture_repo(REPO_ROOT, work / 'fixture')
    repo = clone.make_clone(fixture, work / 'test', fixture.base)
    login = {
        'integrationID': 'openai',
        'label': 'fake',
        'active': True,
        'value': {
            'type': 'oauth',
            'methodID': 'chatgpt-token-sharing',
            'refresh': 'fake-refresh',
            'access': 'fake-access',
            'expires': int((time.time() + 3600) * 1000),
            'metadata': {'clientID': 'fake'},
        },
    }
    harness.MODEL = {'providerID': 'e2e-no-such-provider', 'id': 'none'}
    return harness.start_server(repo, login, BINARY)


@pytest.fixture(scope='module')
def work():
    """Provide a scratch directory under ./.tmp for this module's servers."""
    path = REPO_ROOT / '.tmp' / f'e2e-iwe-workflows-server-{uuid.uuid4().hex}'
    yield path
    shutil.rmtree(path, ignore_errors=True)


@pytest.fixture(scope='module')
def server(suite_modules, work):
    """Share one server across the tests that only talk to it."""
    started = start(suite_modules, work / 'shared')
    yield started
    started.stop()


def test_server_is_isolated_and_serves_the_clone_catalog(server):
    """State lives under the test directory, and the bridge loads from the clone."""
    env = Path(f'/proc/{server.process.pid}/environ').read_bytes().split(b'\0')
    home = next(v for v in env if v.startswith(b'HOME=')).decode().removeprefix('HOME=')
    assert Path(home).is_relative_to(server.clone.path.parent)
    config = json.loads((server.root / 'config/opencode/opencode.json').read_text())
    assert config['plugin'] == [
        str(server.clone.path / '.agents/plugins/agentdev/.opencode-plugin')
    ]
    assert config['small_model'] == 'openai/gpt-6-luna'
    assert 'agentdev:iwe-ship' in server.commands()
    login = server.server.request('GET', '/api/credential')['data'][0]['value']
    assert login['refresh'] == 'withheld'


def test_run_saves_every_message_beside_the_clone(server, suite_modules):
    """A command runs in a session located in the clone and its paged transcript is saved."""
    _, harness = suite_modules
    transcript = server.run('ship', 'agentdev:iwe-ship', 'data/plans/20261008-e2e-hello', 60)
    assert not transcript.timed_out
    assert transcript.path == server.clone.path.parent / 'transcripts/ship.jsonl'
    saved = [json.loads(line) for line in transcript.path.read_text().splitlines()]
    assert saved == transcript.messages
    assert any(m.get('type') == 'user' for m in saved)

    page = harness.PAGE
    harness.PAGE = 1
    try:
        assert server.messages(server.sessions[-1]) == transcript.messages
    finally:
        harness.PAGE = page
    session = server.server.request('GET', f'/api/session/{server.sessions[-1]}')['data']
    assert session['location']['directory'] == str(server.clone.path)


def test_a_session_outliving_the_deadline_is_interrupted(server):
    """Past the suite's deadline the session is interrupted and reported as timed out."""
    transcript = server.run('late', 'agentdev:iwe-explore', 'anything', 0.01)
    assert transcript.timed_out


def test_stop_kills_the_process_group(suite_modules, work):
    """Teardown kills the server's whole process group."""
    server = start(suite_modules, work / 'stopped')
    group = server.process.pid
    server.stop()
    members = [
        pid
        for pid in os.listdir('/proc')
        if pid.isdigit()
        and Path(f'/proc/{pid}/stat').exists()
        and Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[-1].split()[2] == str(group)
    ]
    assert members == []
