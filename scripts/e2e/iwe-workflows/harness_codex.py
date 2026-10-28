"""
Drive ``codex exec`` in a clone and read what its JSON stream leaves out.

The ``--json`` stream shows only the orchestrator, so spawns and child commands
come from the session rollouts, found by thread id. Codex reads its installed
catalog, not the clone's, so the two must match before any run.
"""

from dataclasses import dataclass, field
import filecmp
import json
import os
from pathlib import Path
import re
import shlex
import signal
import subprocess
from typing import Any

from clone import Clone

REINSTALL = '.devcontainer/scripts/reinstall-agentdev-codex.sh'
# Only a command, alone or chained, that executes the script counts; reads of it do not.
# The chain prefix may hold escaped quotes, and an escaped newline separates commands.
PUBLISH_COMMAND = re.compile(
    r'cmd[\\"]*:[\\"]*((?:[^"\\]|\\.)*(&&|\|\||;|\||\\+n) *)?((ba)?sh )?(\./|[^ "\\]*/)?'
    r'bin/publish-e2e\.sh'
)
EXEC_TOOLS = ('exec_command', 'shell')
WORKFLOW_SKILL_FILE = re.compile(r'skills/iwe-(ship|ship-all|implement|implement-all)/SKILL\.md')
GATED = re.compile(r'^disable-model-invocation: true$', re.MULTILINE)


def codex_home() -> Path:
    """Return the user's Codex home, where sessions and the installed catalog live."""
    return Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex')


def installed_catalog() -> Path | None:
    """Return the newest installed agentdev catalog in Codex's plugin cache."""
    cache = codex_home() / 'plugins/cache'
    candidates = [p for p in cache.glob('*/agentdev/*') if p.is_dir()]
    if not candidates:
        return None

    def version(path: Path) -> list[Any]:
        return [int(part) if part.isdigit() else part for part in re.split(r'(\d+)', path.name)]

    return max(candidates, key=version)


def _differs(left: Path, right: Path, ignore: list[str]) -> bool:
    compare = filecmp.dircmp(left, right, ignore=ignore)
    if compare.left_only or compare.right_only or compare.funny_files:
        return True
    _, mismatch, errors = filecmp.cmpfiles(left, right, compare.common_files, shallow=False)
    if mismatch or errors:
        return True
    return any(_differs(left / sub, right / sub, ignore) for sub in compare.common_dirs)


def catalog_mismatch(clone: Clone) -> str | None:
    """Return why the installed catalog differs from the clone's, or ``None`` when it matches."""
    installed = installed_catalog()
    catalog = clone.path / '.agents/plugins/agentdev'
    hint = f'run {REINSTALL}'
    if installed is None:
        return f'codex: no installed agentdev catalog; {hint}'
    if _differs(installed / 'skills', catalog / 'skills', ['__pycache__']) or _differs(
        installed / 'agents', catalog / 'agents', []
    ):
        return f"codex: installed catalog {installed} differs from the clone's; {hint}"
    return None


def gated_skills(clone: Clone) -> list[str]:
    """Return the catalog skills that only an explicit invocation may run."""
    skills = clone.path / '.agents/plugins/agentdev/skills'
    return sorted(p.parent.name for p in skills.glob('*/SKILL.md') if GATED.search(p.read_text()))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    events = []
    for line in path.read_text().splitlines():
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            # A run killed mid-line leaves a partial last event; the rest still counts.
            continue
    return events


def _spawn_calls(rollout: Path) -> list[dict[str, Any]]:
    return [
        json.loads(payload.get('arguments') or '{}')
        for payload in (event.get('payload') or {} for event in _read_jsonl(rollout))
        if payload.get('type') == 'function_call' and payload.get('name') == 'spawn_agent'
    ]


def _publishes(rollouts: list[Path]) -> bool:
    return any(
        PUBLISH_COMMAND.search(line) for path in rollouts for line in path.read_text().splitlines()
    )


@dataclass
class CodexTranscript:
    """One run's ``--json`` stream and the rollouts its thread id leads to."""

    path: Path
    events: list[dict[str, Any]]
    timed_out: bool
    returncode: int | None
    sessions: Path = field(default_factory=lambda: codex_home() / 'sessions')

    def completed(self) -> bool:
        """Whether the run's turn completed."""
        return any(event.get('type') == 'turn.completed' for event in self.events)

    def thread(self) -> str | None:
        """Return the orchestrator's thread id."""
        for event in self.events:
            if event.get('type') == 'thread.started':
                return event.get('thread_id')
        return None

    def rollout(self) -> Path | None:
        """Return the orchestrator's session rollout."""
        thread = self.thread()
        if not thread:
            return None
        return next(iter(sorted(self.sessions.rglob(f'*{thread}.jsonl'))), None)

    def rollout_text(self) -> str:
        """Return the orchestrator's rollout, or nothing when there is none."""
        rollout = self.rollout()
        return rollout.read_text() if rollout else ''

    def children(self) -> list[Path]:
        """Return the rollouts of every agent this run spawned."""
        thread = self.thread()
        if not thread:
            return []
        needle = f'"parent_thread_id":"{thread}"'
        return [p for p in sorted(self.sessions.rglob('*.jsonl')) if needle in p.read_text()]

    def descendants(self) -> list[Path]:
        """Return the rollouts of every agent this run spawned, at any depth."""
        thread = self.thread()
        if not thread:
            return []
        parents: dict[str, tuple[str, Path]] = {}
        for path in sorted(self.sessions.rglob('*.jsonl')):
            with path.open() as rollout:
                first = rollout.readline()
            try:
                meta = json.loads(first).get('payload') or {}
            except json.JSONDecodeError:
                continue
            if meta.get('parent_thread_id') and meta.get('id'):
                parents[meta['id']] = (meta['parent_thread_id'], path)
        found, frontier = [], {thread}
        while frontier:
            level = [
                (child, path) for child, (parent, path) in parents.items() if parent in frontier
            ]
            found.extend(path for _, path in level)
            frontier = {child for child, _ in level}
        return found

    def _payloads(self) -> list[dict[str, Any]]:
        rollout = self.rollout()
        if rollout is None:
            return []
        return [event.get('payload') or {} for event in _read_jsonl(rollout)]

    def spawns(self) -> list[dict[str, Any]]:
        """Return the arguments of every ``spawn_agent`` call the orchestrator made."""
        rollout = self.rollout()
        return _spawn_calls(rollout) if rollout else []

    def commands(self) -> list[str]:
        """Return every shell command the orchestrator ran, as a finished command or a call."""
        found = []
        for payload in self._payloads():
            item = payload.get('item') or {}
            if payload.get('type') == 'item_completed' and item.get('type') == 'CommandExecution':
                found.append(shlex.join(item.get('command') or []))
            elif payload.get('type') == 'function_call' and payload.get('name') in EXEC_TOOLS:
                arguments = json.loads(payload.get('arguments') or '{}')
                command = arguments.get('cmd') or arguments.get('command') or ''
                found.append(command if isinstance(command, str) else shlex.join(command))
        return found

    def agent_results(self, agent: str) -> list[str]:
        """Return the final message of every spawned agent of the catalog type ``agent``."""
        results = []
        for child in self.children():
            events = _read_jsonl(child)
            roles = [
                (event.get('payload') or {}).get('agent_role')
                for event in events
                if event.get('type') == 'session_meta'
            ]
            if agent not in roles:
                continue
            results.extend(
                str(payload.get('last_agent_message') or '')
                for payload in (event.get('payload') or {} for event in events)
                if payload.get('type') == 'task_complete'
            )
        return results

    def agent_spawns(self, agent: str) -> int:
        """Return how many agents of the catalog type ``agent`` were spawned, at any depth."""
        calls = self.spawns() + [s for path in self.descendants() for s in _spawn_calls(path)]
        return sum(1 for spawn in calls if spawn.get('agent_type') == agent)

    def fresh_spawns(self, agent: str | None = None) -> bool:
        """Whether every orchestrator spawn, or each one of type ``agent``, had no conversation."""
        return all(
            spawn.get('fork_turns') == 'none'
            for spawn in self.spawns()
            if agent is None or spawn.get('agent_type') == agent
        )

    def ran_publish(self) -> bool:
        """Whether the orchestrator or any agent it spawned executed ``bin/publish-e2e.sh``."""
        rollout = self.rollout()
        return _publishes([rollout, *self.children()] if rollout else self.children())

    def child_ran_publish(self) -> bool:
        """Whether a spawned agent executed ``bin/publish-e2e.sh``."""
        return _publishes(self.children())

    def agent_lines(self) -> list[str]:
        """Return every line of the orchestrator's messages."""
        return [
            line
            for event in self.events
            if event.get('type') == 'item.completed'
            and (event.get('item') or {}).get('type') == 'agent_message'
            for line in str(event['item'].get('text', '')).splitlines()
        ]

    def excerpt(self, limit: int = 4000) -> str:
        """Return the tail of the orchestrator's messages and its rollout path."""
        text = '\n'.join(self.agent_lines())
        return f'{self.path} (rollout {self.rollout()}):\n{text[-limit:]}'


def run_codex(clone: Clone, name: str, prompt: str, budget: float) -> CodexTranscript:
    """Run one prompt with ``codex exec`` in the clone and save its JSON stream."""
    transcripts = clone.path.parent / 'transcripts'
    transcripts.mkdir(parents=True, exist_ok=True)
    path = transcripts / f'{name}.jsonl'
    with path.open('w') as out, (transcripts / f'{name}.err').open('w') as err:
        process = subprocess.Popen(
            # workspace-write keeps .git read-only; naming it as a root lets the run commit.
            [
                'codex',
                'exec',
                '-s',
                'workspace-write',
                '--add-dir',
                str(clone.path / '.git'),
                '--json',
                prompt,
            ],
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
    return CodexTranscript(path, _read_jsonl(path), timed_out, process.returncode)
