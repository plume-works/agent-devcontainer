"""
Turn one replay's raw output into a run record.

Usage: extract.py <run-dir> <projects-dir> <out-json>

<run-dir> is what run.sh wrote (log.jsonl, out/); <projects-dir> is
~/.claude/projects, where Claude Code keeps each subagent's own transcript.
"""

import json
from pathlib import Path
import re
import sys

ROLES = (
    ('validator', r'valid'),
    ('metadata', r'metadata|description|pr-gen'),
    ('compliance', r'complian|convention|claude\.md|agents\.md'),
    ('durable-knowledge', r'durable|docs? pass|documentation'),
    ('correctness', r'correct|bug|secur|logic|introduced-code'),
)


def role_of(description: str) -> str:
    """Classify a subagent by the description the orchestrator gave it."""
    for role, pattern in ROLES:
        if re.search(pattern, description, re.IGNORECASE):
            return role
    return 'other'


def read_jsonl(path: Path) -> list[dict]:
    """Read a JSON-lines file, skipping lines that are not JSON."""
    events = []
    for line in path.read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return events


def text_of(content) -> str:
    """Join the text blocks of a message's content."""
    if isinstance(content, str):
        return content
    return '\n'.join(
        block.get('text', '') for block in content or [] if block.get('type') == 'text'
    )


def subagent_record(transcript: Path) -> dict:
    """Summarize one subagent: what it was asked to be, which model ran, what it returned."""
    meta = json.loads(transcript.with_suffix('.meta.json').read_text())
    models, output = set(), ''
    for event in read_jsonl(transcript):
        if event.get('type') != 'assistant':
            continue
        message = event.get('message', {})
        if message.get('model'):
            models.add(message['model'])
        text = text_of(message.get('content'))
        if text.strip():
            output = text
    return {
        'description': meta.get('description', ''),
        'role': role_of(meta.get('description', '')),
        'requested_model': meta.get('model'),
        'actual_models': sorted(models),
        'output': output,
    }


def main() -> None:
    """Write the run record for one replay."""
    run_dir, projects, out = (Path(arg) for arg in sys.argv[1:4])
    events = read_jsonl(run_dir / 'log.jsonl')
    init = next(e for e in events if e.get('subtype') == 'init')
    result = next((e for e in events if e.get('type') == 'result'), {})
    slug = re.sub(r'[^A-Za-z0-9]', '-', init['cwd'])
    session_dir = projects / slug / init['session_id'] / 'subagents'
    transcripts = sorted(session_dir.glob('*.jsonl'), key=lambda p: p.stat().st_mtime)
    review_file = run_dir / 'out' / 'review.json'
    candidates_file = run_dir / 'out' / 'candidates.json'
    record = {
        'run': run_dir.name,
        'orchestrator_model': init.get('model'),
        'claude_code_version': init.get('claude_code_version'),
        'cost_usd': round(result.get('total_cost_usd', 0), 2),
        'duration_s': round(result.get('duration_ms', 0) / 1000),
        'cost_by_model': {
            model: round(usage.get('costUSD', 0), 2)
            for model, usage in result.get('modelUsage', {}).items()
        },
        'subagents': [subagent_record(t) for t in transcripts],
        'review': json.loads(review_file.read_text()) if review_file.exists() else None,
        'candidates': (
            json.loads(candidates_file.read_text()) if candidates_file.exists() else None
        ),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(record, indent=1, ensure_ascii=False) + '\n')


if __name__ == '__main__':
    main()
