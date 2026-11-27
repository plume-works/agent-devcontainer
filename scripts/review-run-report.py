#!/usr/bin/env python3
"""Build a pr-review run report from a Claude Code transcripts directory."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
import sys
from typing import Any

NOT_RECORDED = 'not recorded'
AGENT_TOOLS = {'Agent', 'Task'}
HANDBACK_TOOL = 'SubagentHandback'
VERDICT = re.compile(r'^[\s>*#\d.)-]*(CONFIRM|DROP)\b')
MARKUP = '[*_`]*'


@dataclass
class Dispatch:
    """One subagent call made by the main session."""

    tool_use_id: str
    arguments: dict[str, Any]
    result: dict[str, Any] = field(default_factory=dict)
    returned: str = ''
    served_models: list[str] = field(default_factory=list)


@dataclass
class Run:
    """Facts read from the main session transcript."""

    transcript: Path
    models: list[str] = field(default_factory=list)
    texts: list[str] = field(default_factory=list)
    pull_request: dict[str, Any] = field(default_factory=dict)
    dispatches: list[Dispatch] = field(default_factory=list)
    notes: list[tuple[int, str]] = field(default_factory=list)
    """Reasoning notes, each with the number of subagent calls made before it."""


def parse(argv: list[str]) -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--transcripts',
        required=True,
        type=Path,
        help='A Claude Code projects directory holding <project>/<session>.jsonl files.',
    )
    parser.add_argument(
        '--output',
        required=True,
        type=Path,
        help='Report path; subagent prompts go to a prompts/ directory beside it.',
    )
    return parser.parse_args(argv)


def read_records(path: Path) -> list[dict[str, Any]]:
    """Read a JSONL transcript, skipping lines that are not JSON objects."""
    records = []
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue  # a run killed mid-write leaves a truncated last line
        if isinstance(record, dict):
            records.append(record)
    return records


def text_of(content: Any) -> str:
    """Join the text blocks of a message or tool-result content value."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return '\n'.join(
            block.get('text', '')
            for block in content
            if isinstance(block, dict) and block.get('type') == 'text'
        )
    return ''


def add_model(models: list[str], record: dict[str, Any]) -> None:
    """Record the model that served an assistant message, once."""
    model = (record.get('message') or {}).get('model')
    if model and not model.startswith('<') and model not in models:
        models.append(model)


def main_transcript(root: Path) -> Path | None:
    """Return the newest top-level session transcript under a projects directory."""
    candidates = sorted(root.glob('*/*.jsonl'), key=lambda path: path.stat().st_mtime)
    return candidates[-1] if candidates else None


def pull_request_facts(text: str) -> dict[str, Any]:
    """Return the `gh pr view --json` object a tool result holds, or nothing."""
    decoder = json.JSONDecoder()
    for start in (m.start() for m in re.finditer(r'^\{', text, re.MULTILINE)):
        try:
            data, _ = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            continue  # gh may print hint lines before the JSON object
        if isinstance(data, dict) and {'baseRefOid', 'headRefOid'} <= data.keys():
            return data
    return {}


def read_run(transcript: Path) -> Run:
    """Collect the main session's models, texts, PR facts, and subagent calls."""
    run = Run(transcript=transcript)
    by_id: dict[str, Dispatch] = {}
    for record in read_records(transcript):
        message = record.get('message') or {}
        content = message.get('content')
        if record.get('type') == 'assistant':
            add_model(run.models, record)
            for block in content if isinstance(content, list) else []:
                if block.get('type') == 'text' and block.get('text', '').strip():
                    run.texts.append(block['text'])
                elif block.get('type') == 'thinking' and block.get('thinking', '').strip():
                    run.notes.append((len(run.dispatches), block['thinking'].strip()))
                elif block.get('type') == 'tool_use' and block.get('name') in AGENT_TOOLS:
                    dispatch = Dispatch(block.get('id', ''), block.get('input') or {})
                    by_id[dispatch.tool_use_id] = dispatch
                    run.dispatches.append(dispatch)
        elif record.get('type') == 'user' and isinstance(content, list):
            for block in content:
                if not isinstance(block, dict) or block.get('type') != 'tool_result':
                    continue
                dispatch = by_id.get(block.get('tool_use_id', ''))
                if dispatch is None:
                    run.pull_request = pull_request_facts(text_of(block.get('content'))) or (
                        run.pull_request
                    )
                    continue
                result = record.get('toolUseResult')
                dispatch.result = result if isinstance(result, dict) else {}
                dispatch.returned = text_of(dispatch.result.get('content')) or text_of(
                    block.get('content')
                )
    return run


def read_subagents(run: Run) -> None:
    """Read each subagent's own transcript for its served models and hand-back report."""
    subagents = run.transcript.with_suffix('') / 'subagents'
    for dispatch in run.dispatches:
        agent_id = dispatch.result.get('agentId')
        path = subagents / f'agent-{agent_id}.jsonl'
        if not agent_id or not path.is_file():
            continue
        for record in read_records(path):
            if record.get('type') != 'assistant':
                continue
            add_model(dispatch.served_models, record)
            for block in (record.get('message') or {}).get('content') or []:
                if isinstance(block, dict) and block.get('name') == HANDBACK_TOOL:
                    dispatch.returned = (block.get('input') or {}).get('message') or (
                        dispatch.returned
                    )


def tag_value(line: str, tag: str) -> str | None:
    """Return what follows `tag` when a line, Markdown markup aside, opens with it."""
    pattern = rf'[\s#>]*{MARKUP}{re.escape(tag)}{MARKUP}(?::{MARKUP}(?P<rest>.*)|\s*$)'
    match = re.match(pattern, line)
    if match is None:
        return None
    return (match.group('rest') or '').strip()


def tagged_line(texts: list[str], tag: str) -> str:
    """Return what follows the last line that opens with `tag`."""
    found = NOT_RECORDED
    for text in texts:
        for line in text.splitlines():
            value = tag_value(line, tag)
            if value is not None:
                found = value or NOT_RECORDED
    return found


def tagged_section(text: str, tag: str) -> str:
    """Return a text from its last line that opens with `tag` to its end."""
    lines = text.splitlines()
    for index in range(len(lines) - 1, -1, -1):
        if tag_value(lines[index], tag) is not None:
            return '\n'.join(lines[index:]).strip()
    return NOT_RECORDED


def is_validator(dispatch: Dispatch) -> bool:
    """Tell a validator by its return opening with a `CONFIRM` or `DROP` verdict line."""
    first = next((line for line in dispatch.returned.splitlines() if line.strip()), '')
    return bool(VERDICT.match(first))


def notes_at(run: Run, position: int) -> list[str]:
    """Return the reasoning notes written after exactly `position` subagent calls."""
    return [note for at, note in run.notes if at == position]


def effort_tier(run: Run) -> str:
    """Return the `Effort tier:` line, else the last reasoning note before the passes."""
    tier = tagged_line(run.texts, 'Effort tier')
    notes = notes_at(run, 0) if run.dispatches else []
    if tier == NOT_RECORDED and notes:
        return f'{NOT_RECORDED}; reasoning note before the passes: {notes[-1]}'
    return tier


def merge_section(run: Run, first_validator: int | None) -> str:
    """Return the last `Merge:` section, else the reasoning notes before validation."""
    sections = [tagged_section(text, 'Merge') for text in run.texts]
    recorded = [section for section in sections if section != NOT_RECORDED]
    if recorded:
        return recorded[-1]
    passes = first_validator if first_validator is not None else len(run.dispatches)
    notes = notes_at(run, passes) if passes else []
    if notes:
        return '\n\n'.join([f'{NOT_RECORDED}; reasoning notes before validation:', *notes])
    return NOT_RECORDED


def slug(text: str) -> str:
    """Make a short file-name-safe slug."""
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')[:60] or 'subagent'


def quoted(text: str) -> str:
    """Render text as a Markdown blockquote."""
    return '\n'.join(f'> {line}' if line else '>' for line in text.strip().splitlines()) or (
        f'> {NOT_RECORDED}'
    )


def models_text(models: list[str]) -> str:
    """Render a model list."""
    return ', '.join(f'`{model}`' for model in models) or NOT_RECORDED


def write_prompts(run: Run, prompts: Path) -> list[str]:
    """Write each dispatch's prompt to its own file; return the relative links."""
    links = []
    for number, dispatch in enumerate(run.dispatches, start=1):
        name = dispatch.arguments.get('description') or f'subagent {number}'
        prompt = dispatch.arguments.get('prompt') or dispatch.result.get('prompt') or ''
        path = prompts / f'{number:02d}-{slug(name)}.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'# {name}\n\n{prompt}\n', encoding='utf-8')
        links.append(f'{prompts.name}/{path.name}')
    return links


def dispatch_section(number: int, dispatch: Dispatch, link: str) -> list[str]:
    """Render one subagent's report section."""
    arguments, result = dispatch.arguments, dispatch.result
    resolved = [result['resolvedModel']] if result.get('resolvedModel') else []
    lines = [
        f'### {number:02d}. {arguments.get("description") or "subagent"}',
        '',
        f'- Agent type: `{arguments.get("subagent_type") or result.get("agentType") or "?"}`',
        f'- Requested model: `{arguments.get("model") or "session default"}`',
        f'- Resolved model: {models_text(resolved)}',
        f'- Served models: {models_text(dispatch.served_models)}',
        f'- Status: {result.get("status") or NOT_RECORDED}',
        f'- Prompt: [{link}]({link})',
        '',
        '**Returned**',
        '',
        quoted(dispatch.returned),
        '',
    ]
    if not is_validator(dispatch):
        lines += [
            '**Dropped by the pass**',
            '',
            quoted(tagged_section(dispatch.returned, 'Dropped')),
            '',
        ]
    return lines


def render(run: Run, links: list[str]) -> str:
    """Render the whole report."""
    pr = run.pull_request
    revisions = f'`{pr["baseRefOid"]}..{pr["headRefOid"]}`' if pr else NOT_RECORDED
    lines = [
        '# Review run report',
        '',
        '## Run',
        '',
        f'- Transcript: `{run.transcript.parent.name}/{run.transcript.name}`',
        f'- Effort tier: {effort_tier(run)}',
        f'- Orchestrator models: {models_text(run.models)}',
        f'- Revision range: {revisions}',
        f'- PR title: {pr.get("title") or NOT_RECORDED}',
        '',
        '**PR description**',
        '',
        quoted(pr.get('body') or NOT_RECORDED),
        '',
        '## Passes',
        '',
    ]
    validators = []
    for number, (dispatch, link) in enumerate(zip(run.dispatches, links), start=1):
        if is_validator(dispatch):
            validators.append((number, dispatch, link))
        else:
            lines += dispatch_section(number, dispatch, link)
    if len(validators) == len(run.dispatches):
        lines += ['None.', '']
    first_validator = validators[0][0] - 1 if validators else None
    merge = merge_section(run, first_validator)
    lines += ['## Merge', '', quoted(merge), '', '## Validation', '']
    for number, dispatch, link in validators:
        lines += dispatch_section(number, dispatch, link)
    if not validators:
        lines += ['None.', '']
    lines += ['## Final message', '', quoted(run.texts[-1] if run.texts else NOT_RECORDED), '']
    return '\n'.join(lines)


def main(argv: list[str]) -> int:
    """Write the report, or a stub naming why no transcript could be read."""
    args = parse(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    transcript = main_transcript(args.transcripts)
    if transcript is None:
        args.output.write_text(
            f'# Review run report\n\nNo session transcript under `{args.transcripts}`.\n',
            encoding='utf-8',
        )
        return 0
    run = read_run(transcript)
    read_subagents(run)
    links = write_prompts(run, args.output.parent / 'prompts')
    args.output.write_text(render(run, links), encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
