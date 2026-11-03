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
    scripts = '.agents/plugins/agentdev/skills/'
    return [
        'Bash(iwe *)',
        'Bash(git *)',
        'Bash(grep *)',
        'Bash(test *)',
        f'Bash({publish}*)',
        f'Bash(./{publish}*)',
        f'Bash({clone.path}/{publish}*)',
        f'Bash({scripts}*)',
        f'Bash(./{scripts}*)',
        f'Bash({clone.path}/{scripts}*)',
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

    def results(self) -> list[dict[str, Any]]:
        """Return every final result event."""
        return [event for event in self.events if event.get('type') == 'result']

    def completed(self) -> bool:
        """Whether the run reached a successful final result event."""
        return any(
            result.get('subtype') == 'success' and not result.get('is_error')
            for result in self.results()
        )

    def failure_reason(self, budget: float) -> str:
        """Explain why the run did not complete, for the run-completed assertion."""
        if self.timed_out:
            return f'budget exhausted: still running after {budget:.0f}s, killed'
        for result in self.results():
            if result.get('is_error') or result.get('subtype') != 'success':
                detail = result.get('result') or '; '.join(map(str, result.get('errors') or []))
                return f'result {result.get("subtype")}: {detail}'
        return f'no result event (claude exited {self.returncode})'

    def calls(self, tool: str) -> list[dict[str, Any]]:
        """Return the input of every call to ``tool``, subagents' included."""
        return [
            block.get('input') or {}
            for event in self.events
            if event.get('type') == 'assistant'
            for block in (event.get('message') or {}).get('content') or []
            if block.get('type') == 'tool_use' and block.get('name') == tool
        ]

    def agent_prompts(self, agent: str) -> list[str]:
        """Return the prompt of every dispatch of the catalog agent ``agent``."""
        return [
            str(call.get('prompt', ''))
            for call in self.calls('Agent')
            if re.search(rf'{re.escape(agent)}$', str(call.get('subagent_type') or ''))
        ]

    def agent_results(self, agent: str) -> list[str]:
        """Return the report of every finished dispatch of the catalog agent ``agent``."""
        ids = {
            block.get('id')
            for event in self.events
            if event.get('type') == 'assistant'
            for block in (event.get('message') or {}).get('content') or []
            if block.get('type') == 'tool_use'
            and block.get('name') == 'Agent'
            and re.search(
                rf'{re.escape(agent)}$', str((block.get('input') or {}).get('subagent_type'))
            )
        }
        return [
            content
            if isinstance(content, str)
            else '\n'.join(part.get('text', '') for part in content if isinstance(part, dict))
            for event in self.events
            if event.get('type') == 'user'
            for block in (event.get('message') or {}).get('content') or []
            if isinstance(block, dict)
            and block.get('type') == 'tool_result'
            and block.get('tool_use_id') in ids
            for content in [block.get('content') or '']
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
            env={**os.environ, 'PATH': clone.agent_path(os.environ.get('PATH', ''))},
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
