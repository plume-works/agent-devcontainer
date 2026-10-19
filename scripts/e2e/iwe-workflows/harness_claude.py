"""
Drive headless Claude Code in a clone with the clone's own catalog.

Claude Code keeps the user's configuration and login. Its stream-json events
carry every tool call, subagents' included.
"""

from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import signal
import subprocess
from typing import Any

from clone import Clone


def allowed_tools(clone: Clone) -> list[str]:
    """Return the tools a run may use without a prompt nobody would answer."""
    publish = 'bin/publish-e2e.sh'
    return [
        'Bash(iwe *)',
        'Bash(git *)',
        'Bash(grep *)',
        'Bash(test *)',
        f'Bash({publish}*)',
        f'Bash(./{publish}*)',
        f'Bash({clone.path}/{publish}*)',
        'Read',
        'Edit',
        'Write',
        'Grep',
        'Glob',
        'Skill',
        'Agent',
    ]


@dataclass
class ClaudeTranscript:
    """Every stream-json event of one run."""

    path: Path
    events: list[dict[str, Any]]
    timed_out: bool
    returncode: int | None

    def completed(self) -> bool:
        """Whether the run reached its final result event."""
        return any(event.get('type') == 'result' for event in self.events)

    def calls(self, tool: str) -> list[dict[str, Any]]:
        """Return the input of every call to ``tool``, subagents' included."""
        return [
            block.get('input') or {}
            for event in self.events
            if event.get('type') == 'assistant'
            for block in (event.get('message') or {}).get('content') or []
            if block.get('type') == 'tool_use' and block.get('name') == tool
        ]

    def shipper_prompts(self) -> list[str]:
        """Return the prompt of every ``iwe-shipper`` dispatch."""
        return [
            str(call.get('prompt', ''))
            for call in self.calls('Agent')
            if re.search(r'iwe-shipper$', str(call.get('subagent_type') or ''))
        ]

    def excerpt(self, tool: str | None = None, limit: int = 4000) -> str:
        """Return the tail of the run's text, or of one tool's calls, for a failure message."""
        if tool is not None:
            text = '\n'.join(json.dumps(call) for call in self.calls(tool)) or f'(no {tool} calls)'
        else:
            text = '\n'.join(
                str(event.get('result', ''))
                if event.get('type') == 'result'
                else '\n'.join(
                    block.get('text', '')
                    for block in (event.get('message') or {}).get('content') or []
                    if block.get('type') == 'text'
                )
                for event in self.events
                if event.get('type') in ('assistant', 'result')
            )
        return f'{self.path}:\n{text[-limit:]}'


def run_claude(clone: Clone, name: str, prompt: str, budget: float) -> ClaudeTranscript:
    """Run one prompt headless in the clone and save its stream-json transcript."""
    transcripts = clone.path.parent / 'transcripts'
    transcripts.mkdir(parents=True, exist_ok=True)
    path = transcripts / f'{name}.jsonl'
    catalog = clone.path / '.agents/plugins/agentdev'
    # --allowedTools takes many values, so a single-value flag must end the list.
    args = [
        'claude',
        '-p',
        '--plugin-dir',
        str(catalog),
        '--allowedTools',
        *allowed_tools(clone),
        '--permission-mode',
        'acceptEdits',
        '--output-format',
        'stream-json',
        '--verbose',
        prompt,
    ]
    with path.open('w') as out, (transcripts / f'{name}.err').open('w') as err:
        process = subprocess.Popen(
            args,
            cwd=clone.path,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            start_new_session=True,
        )
        timed_out = False
        try:
            process.wait(timeout=budget)
        except subprocess.TimeoutExpired:
            timed_out = True
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
    events = []
    for line in path.read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            # A run killed mid-line leaves a partial last event; the rest still counts.
            continue
    return ClaudeTranscript(path, events, timed_out, process.returncode)
