import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

import pytest
from scratch import TMP_ROOT

REPO_ROOT = Path(__file__).parents[2]
SCRIPT = [sys.executable, '-m', 'agentdev_runtime', 'remote-control', 'session']
PIN_SCRIPT = 'agentdev-runtime remote-control pin'
ID_FILE_NAME = 'remote-control-session-id'
STORED_ID = '11111111-2222-4333-8444-555555555555'
# Logs each call's arguments as a JSON array and fails `--resume` with $CLAUDE_TEST_RESUME_EXIT.
FAKE_CLAUDE = (
    '#!/bin/sh\n'
    'jq -cn \'$ARGS.positional\' --args -- "$@" >>"$CLAUDE_TEST_LOG"\n'
    'case "$*" in *--resume*) exit "$CLAUDE_TEST_RESUME_EXIT" ;; esac\n'
)


@pytest.fixture
def test_dir():
    path = TMP_ROOT / f'claude-remote-control-session-{uuid.uuid4().hex}'
    path.mkdir(parents=True)
    yield path
    shutil.rmtree(path)


def run_session(
    test_dir: Path, *args: str, stored_id: str | None = None, resume_exit: int = 0
) -> tuple[list[list[str]], Path]:
    config_dir = test_dir / 'claude-config'
    config_dir.mkdir()
    id_file = config_dir / ID_FILE_NAME
    if stored_id is not None:
        id_file.write_text(f'{stored_id}\n')
    fake_bin = test_dir / 'bin'
    fake_bin.mkdir()
    (fake_bin / 'claude').write_text(FAKE_CLAUDE)
    (fake_bin / 'claude').chmod(0o755)
    log = test_dir / 'claude.log'
    env = os.environ | {
        'PATH': f'{fake_bin}:{os.environ["PATH"]}',
        'CLAUDE_CONFIG_DIR': str(config_dir),
        'CLAUDE_TEST_LOG': str(log),
        'CLAUDE_TEST_RESUME_EXIT': str(resume_exit),
    }
    result = subprocess.run([*SCRIPT, *args], env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    return [json.loads(line) for line in log.read_text().splitlines()], id_file


EXPECTED_SETTINGS = {
    'hooks': {'SessionStart': [{'hooks': [{'type': 'command', 'command': PIN_SCRIPT}]}]}
}


def split_settings(call: list[str]) -> tuple[list[str], dict]:
    index = call.index('--settings')
    return call[:index] + call[index + 2 :], json.loads(call[index + 1])


def without_settings(calls: list[list[str]]) -> list[str]:
    return [' '.join(split_settings(call)[0]) for call in calls]


def stored(id_file: Path) -> str:
    return id_file.read_text().strip()


def test_first_start_pins_a_new_conversation(test_dir):
    calls, id_file = run_session(test_dir, 'agent-dev1')
    new_id = stored(id_file)
    assert str(uuid.UUID(new_id)) == new_id
    assert without_settings(calls) == [f'--remote-control agent-dev1 --session-id {new_id}']


def test_resumes_the_stored_conversation(test_dir):
    calls, id_file = run_session(test_dir, 'agent-dev1', stored_id=STORED_ID)
    assert without_settings(calls) == [f'--remote-control agent-dev1 --resume {STORED_ID}']
    assert stored(id_file) == STORED_ID


def test_failed_resume_pins_a_new_conversation(test_dir):
    calls, id_file = run_session(test_dir, 'agent-dev1', stored_id=STORED_ID, resume_exit=1)
    new_id = stored(id_file)
    assert new_id != STORED_ID
    assert without_settings(calls) == [
        f'--remote-control agent-dev1 --resume {STORED_ID}',
        f'--remote-control agent-dev1 --session-id {new_id}',
    ]


def test_without_a_name_runs_unnamed_remote_control(test_dir):
    calls, id_file = run_session(test_dir, stored_id=STORED_ID, resume_exit=1)
    assert without_settings(calls) == [
        f'--remote-control --resume {STORED_ID}',
        f'--remote-control --session-id {stored(id_file)}',
    ]


def test_every_call_runs_the_pin_hook_on_session_start(test_dir):
    calls, _ = run_session(test_dir, 'agent-dev1', stored_id=STORED_ID, resume_exit=1)
    assert [split_settings(call)[1] for call in calls] == [EXPECTED_SETTINGS] * 2
