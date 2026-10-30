import json
import os
from pathlib import Path
import shutil
import subprocess
import uuid

import pytest
from scratch import TMP_ROOT

REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / '.devcontainer/scripts/claude-remote-control-pin.sh'
ID_FILE_NAME = 'remote-control-session-id'
STORED_ID = '11111111-2222-4333-8444-555555555555'
NEW_ID = '66666666-7777-4888-9999-aaaaaaaaaaaa'


@pytest.fixture
def config_dir():
    path = TMP_ROOT / f'claude-remote-control-pin-{uuid.uuid4().hex}'
    path.mkdir(parents=True)
    yield path / 'claude-config'
    shutil.rmtree(path)


def run_pin(config_dir: Path, stdin: str) -> subprocess.CompletedProcess[str]:
    env = os.environ | {'CLAUDE_CONFIG_DIR': str(config_dir)}
    return subprocess.run([SCRIPT], env=env, input=stdin, text=True, capture_output=True)


def hook_input(**fields: str) -> str:
    return json.dumps({'hook_event_name': 'SessionStart', **fields})


def test_clear_pins_the_new_conversation(config_dir):
    config_dir.mkdir()
    (config_dir / ID_FILE_NAME).write_text(f'{STORED_ID}\n')
    result = run_pin(config_dir, hook_input(session_id=NEW_ID, source='clear'))
    assert result.returncode == 0, result.stderr
    assert (config_dir / ID_FILE_NAME).read_text() == f'{NEW_ID}\n'
    assert [path.name for path in config_dir.iterdir()] == [ID_FILE_NAME]


def test_creates_the_config_directory_and_pin(config_dir):
    result = run_pin(config_dir, hook_input(session_id=NEW_ID, source='clear'))
    assert result.returncode == 0, result.stderr
    assert (config_dir / ID_FILE_NAME).read_text() == f'{NEW_ID}\n'


@pytest.mark.parametrize(
    'stdin',
    [
        hook_input(session_id='', source='clear'),
        hook_input(source='clear'),
        'not json',
    ],
    ids=['empty-session-id', 'missing-session-id', 'invalid-json'],
)
def test_unusable_input_leaves_the_pin_unchanged(config_dir, stdin):
    config_dir.mkdir()
    (config_dir / ID_FILE_NAME).write_text(f'{STORED_ID}\n')
    result = run_pin(config_dir, stdin)
    assert result.returncode == 0, result.stderr
    assert result.stderr
    assert (config_dir / ID_FILE_NAME).read_text() == f'{STORED_ID}\n'
