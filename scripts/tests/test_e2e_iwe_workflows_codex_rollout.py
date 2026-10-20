"""The Codex harness reads commands and publish runs from the session rollouts."""

import importlib.util
import json
from pathlib import Path
import sys

import pytest

REPO_ROOT = Path(__file__).parents[2]
SUITE = REPO_ROOT / 'scripts/e2e/iwe-workflows'
sys.path.insert(0, str(SUITE))
_spec = importlib.util.spec_from_file_location(
    'e2e_iwe_workflows_harness_codex_rollout', SUITE / 'harness_codex.py'
)
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)
_scenarios_spec = importlib.util.spec_from_file_location(
    'e2e_iwe_workflows_scenarios', SUITE / 'scenarios.py'
)
scenarios = importlib.util.module_from_spec(_scenarios_spec)
_scenarios_spec.loader.exec_module(scenarios)
sys.path.remove(str(SUITE))

THREAD = '01a15699-fbe2-71c3-a988-7ecdc0d01826'
CHILD = '01a15699-0000-7000-8000-000000000001'
CATALOG = '/root/.codex/plugins/cache/agentdev/4.2.0'
SKILL_BODY = (
    '<skill>\n<name>agentdev:iwe-implement</name>\n'
    f'Read [the iwe-implementer rulebook](../../{scenarios.RULEBOOK}) in session.\n</skill>'
)


def skill_injection() -> dict:
    """Return the user message Codex records when a skill's body is loaded."""
    content = [{'type': 'input_text', 'text': SKILL_BODY}]
    return {
        'type': 'response_item',
        'payload': {'type': 'message', 'role': 'user', 'content': content},
    }


def command_execution(cmd: str) -> dict:
    """Return the event Codex records once a shell command finishes."""
    item = {'type': 'CommandExecution', 'command': ['/bin/bash', '-lc', cmd]}
    return {'type': 'event_msg', 'payload': {'type': 'item_completed', 'item': item}}


def exec_function_call(cmd: str) -> dict:
    """Return an ``exec_command`` function call carrying ``cmd``."""
    arguments = json.dumps({'cmd': cmd, 'workdir': '/w/clone'}, separators=(',', ':'))
    payload = {'type': 'function_call', 'name': 'exec_command', 'arguments': arguments}
    return {'type': 'response_item', 'payload': payload}


def write_rollout(sessions: Path, thread: str, events: list[dict]) -> None:
    """Write one session rollout as Codex names it, under a dated directory."""
    day = sessions / '2026/10/20'
    day.mkdir(parents=True, exist_ok=True)
    rollout = day / f'rollout-2026-10-20T00-00-00-{thread}.jsonl'
    rollout.write_text(
        ''.join(json.dumps(event, separators=(',', ':')) + '\n' for event in events)
    )


def transcript(sessions: Path):
    """Return a transcript whose ``--json`` stream started ``THREAD``."""
    events = [{'type': 'thread.started', 'thread_id': THREAD}, {'type': 'turn.completed'}]
    return harness.CodexTranscript(Path('run.jsonl'), events, False, 0, sessions=sessions)


def test_a_skill_body_naming_the_rulebook_is_not_a_command(tmp_path):
    """The rulebook path inside a loaded skill's text is not a command that read it."""
    write_rollout(tmp_path, THREAD, [skill_injection()])
    assert transcript(tmp_path).commands() == []


@pytest.mark.parametrize('event', [command_execution, exec_function_call])
def test_a_command_reading_the_rulebook_counts(tmp_path, event):
    """The finished-command event and the function call each record the read."""
    read = f"sed -n '1,260p' {CATALOG}/{scenarios.RULEBOOK}"
    write_rollout(tmp_path, THREAD, [skill_injection(), event(read)])
    assert [cmd for cmd in transcript(tmp_path).commands() if scenarios.RULEBOOK in cmd] != []
