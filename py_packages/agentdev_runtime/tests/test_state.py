"""The on-disk shapes the controller writes and every reader parses."""

import json
from pathlib import Path

from agentdev_runtime import state
import pytest


def document(**overrides: object) -> dict:
    base = state.runtime_state(
        startup_id='s',
        profile='deploy',
        state='ready',
        ready=True,
        probes=['dbus'],
        latched=None,
        components={'dbus': state.component('ready')},
        retry=None,
        interval=2,
    )
    return {**base, **overrides}


def test_a_fresh_heartbeat_reads_as_its_state(tmp_path: Path) -> None:
    path = tmp_path / 'state.json'
    state.publish(path, document())
    name, loaded = state.current(path)
    assert name == 'ready'
    assert loaded['probes'] == ['dbus']


def test_three_intervals_without_a_heartbeat_is_stale(tmp_path: Path) -> None:
    path = tmp_path / 'state.json'
    state.write_json(path, document(heartbeat=100.0, interval=2))
    assert state.current(path, now=105.9)[0] == 'ready'
    assert state.current(path, now=106.0)[0] == 'stale'


@pytest.mark.parametrize('body', ['{', '[]', '{"heartbeat": "x"}'])
def test_a_damaged_state_file_is_unreadable(tmp_path: Path, body: str) -> None:
    path = tmp_path / 'state.json'
    path.write_text(body)
    assert state.current(path)[0] == 'unreadable'


def test_no_state_file_is_missing(tmp_path: Path) -> None:
    assert state.current(tmp_path / 'state.json') == ('missing', {})


def test_a_component_reason_is_kept_only_when_given() -> None:
    assert state.component('ready') == {'status': 'ready'}
    assert state.component('failed', 'x') == {'status': 'failed', 'reason': 'x'}


def test_a_retry_request_is_taken_once(tmp_path: Path) -> None:
    path = tmp_path / 'retry-request.json'
    request = state.retry_request('project')
    state.write_json(path, request)
    assert state.take_retry(path) == request
    assert not path.exists()
    assert state.take_retry(path) is None


def test_the_failure_record_keeps_the_output_tail() -> None:
    lines = [str(n) for n in range(state.OUTPUT_TAIL + 5)]
    record = state.failure(
        startup_id='s',
        component_name='project',
        reason='r',
        command=['x'],
        exit_status=4,
        output=lines,
    )
    assert record['output'] == lines[-state.OUTPUT_TAIL :]
    assert record['component'] == 'project'


def test_write_json_leaves_no_temporary_file(tmp_path: Path) -> None:
    path = tmp_path / 'state.json'
    state.write_json(path, {'a': 1})
    assert json.loads(path.read_text()) == {'a': 1}
    assert [p.name for p in tmp_path.iterdir()] == ['state.json']


def test_run_files_live_under_the_run_dir(tmp_path: Path) -> None:
    files = state.RunFiles(tmp_path)
    assert files.state == tmp_path / 'state.json'
    assert files.retry == tmp_path / 'retry-request.json'
    assert files.output('cbm') == tmp_path / 'output/cbm.json'
    assert state.failure_record(tmp_path) == tmp_path / '.local/state/agentdev/last-failure.json'
