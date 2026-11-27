"""Run scripts/review-run-report.py against fixture Claude Code transcripts."""

from __future__ import annotations

from collections.abc import Iterator
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/review-run-report.py'
_SPEC = importlib.util.spec_from_file_location('review_run_report', SCRIPT)
assert _SPEC and _SPEC.loader
_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _MODULE  # dataclasses resolve their module through sys.modules
_SPEC.loader.exec_module(_MODULE)
NOT_RECORDED = _MODULE.NOT_RECORDED
AGENT_TOOL = sorted(_MODULE.AGENT_TOOLS)[0]
HANDBACK_TOOL = _MODULE.HANDBACK_TOOL
SESSION = 'session-1'
PR_FACTS = {
    'baseRefOid': 'aaa111',
    'headRefOid': 'bbb222',
    'title': 'Fixture title',
    'body': 'Fixture body.',
}


def assistant(model: str, *blocks: dict) -> dict:
    """Return an assistant transcript record."""
    return {'type': 'assistant', 'message': {'model': model, 'content': list(blocks)}}


def text(value: str) -> dict:
    """Return a text content block."""
    return {'type': 'text', 'text': value}


def agent_call(call_id: str, description: str, model: str, prompt: str) -> dict:
    """Return an Agent tool_use block."""
    return {
        'type': 'tool_use',
        'id': call_id,
        'name': AGENT_TOOL,
        'input': {
            'description': description,
            'model': model,
            'prompt': prompt,
            'subagent_type': 'general-purpose',
        },
    }


def tool_result(call_id: str, content: str, result: dict | None = None) -> dict:
    """Return a user record carrying one tool result."""
    record = {
        'type': 'user',
        'message': {
            'content': [{'type': 'tool_result', 'tool_use_id': call_id, 'content': content}]
        },
    }
    if result is not None:
        record['toolUseResult'] = result
    return record


def agent_result(agent_id: str, returned: str, model: str) -> dict:
    """Return the toolUseResult Claude Code records for a finished subagent."""
    return {
        'agentId': agent_id,
        'status': 'completed',
        'resolvedModel': model,
        'content': [text(returned)],
    }


@pytest.fixture
def root() -> Iterator[Path]:
    """Yield a scratch directory, removed on teardown."""
    path = TMP_ROOT / f'review-run-report-{uuid4().hex}'
    path.mkdir(parents=True)
    yield path
    shutil.rmtree(path)


def write_transcripts(root: Path, main: list[dict], subagents: dict[str, list[dict]]) -> Path:
    """Lay out a projects directory with one session and its subagent transcripts."""
    project = root / 'projects' / '-repo'
    (project / SESSION / 'subagents').mkdir(parents=True)
    lines = '\n'.join(json.dumps(record) for record in main)
    (project / f'{SESSION}.jsonl').write_text(lines + '\n', encoding='utf-8')
    for agent_id, records in subagents.items():
        path = project / SESSION / 'subagents' / f'agent-{agent_id}.jsonl'
        path.write_text('\n'.join(json.dumps(r) for r in records) + '\n', encoding='utf-8')
    return root / 'projects'


def report(root: Path, transcripts: Path) -> str:
    """Run the script and return the report text."""
    output = root / 'out' / 'review-run-report.md'
    subprocess.run(
        [sys.executable, '-I', str(SCRIPT), '--transcripts', str(transcripts), '--output',
         str(output)],
        check=True,
        capture_output=True,
        text=True,
    )  # fmt: skip
    return output.read_text(encoding='utf-8')


def section(body: str, heading: str) -> str:
    """Return one `## ` section of the report."""
    return body.split(f'## {heading}\n', 1)[1].split('\n## ', 1)[0]


def full_run() -> list[dict]:
    """Return a main transcript with a pass, a dropped validation, and a confirmed one."""
    return [
        assistant('claude-big-1', {'type': 'tool_use', 'id': 'gh', 'name': 'Bash', 'input': {}}),
        tool_result('gh', 'hint: use gh event listen\n' + json.dumps(PR_FACTS, indent=2)),
        assistant('claude-big-1', text('Effort tier: full — 40 changed code lines.')),
        assistant('claude-big-1', agent_call('c1', 'Correctness pass', 'opus', 'Find bugs.')),
        tool_result(
            'c1',
            'hand-back',
            agent_result('a1', 'Issue: race in x.\nDropped:\n- style nit — not a bug', 'big'),
        ),
        assistant('claude-big-1', text('Merge:\n- discarded y — empty Trigger')),
        assistant(
            'claude-big-1',
            agent_call('v1', 'Validate race', 'sonnet', 'Check race.'),
            agent_call('v2', 'Validate z', 'sonnet', 'Check z.'),
        ),
        tool_result('v1', 'hand-back', agent_result('a2', 'CONFIRM — race holds.', 'light')),
        tool_result('v2', 'hand-back', agent_result('a3', 'DROP: path — no caller.', 'light')),
        assistant('claude-big-1', text('Published REQUEST_CHANGES with one comment.')),
    ]


def test_full_run_reports_every_section(root: Path) -> None:
    """A full run fills the run facts, passes, merge, validation, and publish."""
    transcripts = write_transcripts(
        root,
        full_run(),
        {'a1': [assistant('claude-big-2', text('x'))], 'a2': [assistant('claude-light-2')]},
    )
    body = report(root, transcripts)
    run = section(body, 'Run')
    assert 'Effort tier: full — 40 changed code lines.' in run
    assert '`claude-big-1`' in run
    assert '`aaa111..bbb222`' in run
    assert 'Fixture title' in run and '> Fixture body.' in run
    passes = section(body, 'Passes')
    assert 'Correctness pass' in passes and 'Validate' not in passes
    assert 'Requested model: `opus`' in passes
    assert 'Resolved model: `big`' in passes
    assert 'Served models: `claude-big-2`' in passes
    assert '> - style nit — not a bug' in passes
    assert '> - discarded y — empty Trigger' in section(body, 'Merge')
    validation = section(body, 'Validation')
    assert 'CONFIRM — race holds.' in validation and 'DROP: path — no caller.' in validation
    assert 'Served models: `claude-light-2`' in validation
    assert 'Published REQUEST_CHANGES' in section(body, 'Final message')


def test_prompts_are_written_beside_the_report(root: Path) -> None:
    """Each subagent's prompt gets its own file, linked from the report."""
    body = report(root, write_transcripts(root, full_run(), {}))
    prompt = root / 'out' / 'prompts' / '01-correctness-pass.md'
    assert prompt.read_text(encoding='utf-8') == '# Correctness pass\n\nFind bugs.\n'
    assert '(prompts/01-correctness-pass.md)' in body
    assert (root / 'out' / 'prompts' / '03-validate-z.md').is_file()


def test_missing_facts_read_not_recorded(root: Path) -> None:
    """A fast-approve run with no tier line, PR facts, or subagents still reports."""
    transcripts = write_transcripts(
        root, [assistant('claude-light-1', text('Approved: version bump only.'))], {}
    )
    body = report(root, transcripts)
    run = section(body, 'Run')
    assert f'Effort tier: {NOT_RECORDED}' in run
    assert f'Revision range: {NOT_RECORDED}' in run
    assert section(body, 'Passes').strip() == 'None.'
    assert section(body, 'Validation').strip() == 'None.'
    assert f'> {NOT_RECORDED}' in section(body, 'Merge')
    assert 'Approved: version bump only.' in section(body, 'Final message')


def test_pass_without_dropped_list_and_missing_subagent_file(root: Path) -> None:
    """A pass with no `Dropped:` and no transcript file reports both as not recorded."""
    main = [
        assistant('m', agent_call('c1', 'Compliance pass', 'sonnet', 'Check rules.')),
        tool_result('c1', 'hand-back', agent_result('gone', 'No issues.', 'light')),
    ]
    passes = section(report(root, write_transcripts(root, main, {})), 'Passes')
    assert f'Served models: {NOT_RECORDED}' in passes
    assert passes.split('**Dropped by the pass**', 1)[1].strip() == f'> {NOT_RECORDED}'


def test_no_transcript_writes_a_stub(root: Path) -> None:
    """An empty projects directory still yields a report naming the gap."""
    (root / 'projects').mkdir()
    assert 'No session transcript' in report(root, root / 'projects')


def test_batched_validator_is_grouped_under_validation(root: Path) -> None:
    """A light-tier batch returning numbered verdict lines counts as a validator."""
    main = [
        assistant('m', agent_call('v1', 'Validate batch', 'sonnet', 'Check all.')),
        tool_result(
            'v1',
            'hand-back',
            agent_result('b', '1. CONFIRM — a\n2. DROP: path — b', 'l'),
        ),
    ]
    body = report(root, write_transcripts(root, main, {}))
    assert section(body, 'Passes').strip() == 'None.'
    assert '2. DROP: path — b' in section(body, 'Validation')


def handback(message: str) -> dict:
    """Return a subagent assistant record that hands its report back."""
    block = {'type': 'tool_use', 'name': HANDBACK_TOOL, 'input': {'message': message}}
    return assistant('claude-light-3', block)


def test_handback_report_and_marked_up_tags(root: Path) -> None:
    """A report handed back by tool call, with Markdown-marked tags, is read whole."""
    main = [
        assistant('m', text('**Effort tier:** light — docs in `docs/test_run_x.md`')),
        assistant('m', agent_call('c1', 'Compliance pass', 'sonnet', 'Check rules.')),
        tool_result('c1', 'hand-back', agent_result('h1', 'See the hand-back.', 'light')),
        assistant('m', text('## Merge\n- nothing collapsed')),
    ]
    report_text = 'One finding: quotes `DROP TABLE x`.\n## Dropped\n- nit — no rule'
    body = report(root, write_transcripts(root, main, {'h1': [handback(report_text)]}))
    assert 'Effort tier: light — docs in `docs/test_run_x.md`' in section(body, 'Run')
    passes = section(body, 'Passes')
    assert 'quotes `DROP TABLE x`' in passes and 'See the hand-back.' not in passes
    assert '> - nit — no rule' in passes.split('**Dropped by the pass**', 1)[1]
    assert section(body, 'Validation').strip() == 'None.'
    assert '> - nothing collapsed' in section(body, 'Merge')


def test_newest_session_wins_and_truncated_lines_are_skipped(root: Path) -> None:
    """With two sessions the newest is reported, and a cut-off line does not stop it."""
    transcripts = write_transcripts(root, [assistant('old', text('Old session.'))], {})
    newest = transcripts / '-repo' / 'session-2.jsonl'
    record = json.dumps(assistant('new', text('New session.')))
    newest.write_text(record + '\n{"type": "assist', encoding='utf-8')
    old = transcripts / '-repo' / f'{SESSION}.jsonl'
    os.utime(old, (1, 1))
    body = report(root, transcripts)
    assert 'session-2.jsonl' in section(body, 'Run')
    assert 'New session.' in section(body, 'Final message')


def thinking(note: str) -> dict:
    """Return a thinking content block."""
    return {'type': 'thinking', 'thinking': note}


def test_reasoning_notes_stand_in_for_missing_tagged_lines(root: Path) -> None:
    """With no `Effort tier:` or `Merge:` line, the matching reasoning notes are reported."""
    main = [
        assistant('m', thinking('Early note.')),
        assistant('m', thinking('Full effort: a new script.')),
        assistant('m', agent_call('c1', 'Correctness pass', 'opus', 'Find bugs.')),
        tool_result('c1', 'hand-back', agent_result('a1', 'Issue: x.\nDropped: none', 'big')),
        assistant('m', thinking('')),
        assistant('m', thinking('Merged two duplicates into one.')),
        assistant('m', agent_call('v1', 'Validate x', 'sonnet', 'Check x.')),
        tool_result('v1', 'hand-back', agent_result('a2', 'DROP: path — no caller.', 'light')),
        assistant('m', thinking('Publishing now.')),
    ]
    body = report(root, write_transcripts(root, main, {}))
    tier = f'Effort tier: {NOT_RECORDED}; reasoning note before the passes: Full effort'
    assert tier in section(body, 'Run')
    merge = section(body, 'Merge')
    assert 'Merged two duplicates into one.' in merge
    assert 'Early note.' not in merge and 'Publishing now.' not in merge


def test_tagged_lines_win_over_reasoning_notes(root: Path) -> None:
    """A written `Effort tier:` or `Merge:` line is reported instead of any note."""
    main = [
        assistant('m', thinking('Note.'), text('Effort tier: light — docs only')),
        assistant('m', agent_call('c1', 'Pass', 'sonnet', 'Check.')),
        tool_result('c1', 'hand-back', agent_result('a1', 'No issues.\nDropped: none', 'l')),
        assistant('m', thinking('Merge note.'), text('Merge: nothing discarded or collapsed')),
    ]
    body = report(root, write_transcripts(root, main, {}))
    assert '- Effort tier: light — docs only' in section(body, 'Run')
    merge = section(body, 'Merge')
    assert 'nothing discarded or collapsed' in merge and 'Merge note.' not in merge
