#!/usr/bin/env python3

"""
Install this plugin's agents into Codex as generated TOML agents.

Codex reads custom agents only from ``agents/*.toml`` under its home directory,
never from a plugin, so every catalog install runs this after ``codex plugin
add``. Contract: see spec/catalog-lifecycle.

Usage:
  install-codex-agents.py [--plugin-root <dir>]

Writes ``${CODEX_HOME:-~/.codex}/agents/agentdev-<stem>.toml`` for each
``<plugin-root>/agents/<stem>.agent.md`` (default plugin root: the one shipping
this script), then removes every other ``agentdev-*.toml`` there.

Results (RESULT / exit code):
  SUCCESS          0  Every agent installed; stale agentdev agents removed.
  SCRIPT_FAILURE   1  Unexpected failure.
  PREFLIGHT_ERROR  2  Bad usage, or the plugin root has no agents/ directory.
  INVALID_AGENT    3  An agent file lacks frontmatter or a description;
                      nothing was written.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import result_codes as rc  # noqa: E402  (path set above so the plugin's bin/ resolves)

PREFLIGHT_ERROR = 2
INVALID_AGENT = 3

OWNED_PREFIX = 'agentdev-'
AGENT_SUFFIX = '.agent.md'
WRITE_TOOLS = frozenset({'Edit', 'Write'})


class InvalidAgentError(ValueError):
    """An agent file Codex could not be given as a TOML agent."""


def parse_agent(path: Path) -> tuple[dict[str, str], str]:
    """Split an agent file into its single-line frontmatter fields and its body."""
    text = path.read_text(encoding='utf-8')
    if not text.startswith('---\n'):
        raise InvalidAgentError(f'{path}: missing YAML frontmatter')
    frontmatter, separator, body = text[4:].partition('\n---\n')
    if not separator:
        raise InvalidAgentError(f'{path}: unterminated YAML frontmatter')
    fields: dict[str, str] = {}
    for line in frontmatter.splitlines():
        key, colon, value = line.partition(':')
        if colon and key.strip():
            fields[key.strip()] = value.strip().strip('"\'')
    if not fields.get('description'):
        raise InvalidAgentError(f'{path}: frontmatter has no description')
    return fields, body.strip()


def toml_string(value: str) -> str:
    """Render `value` as a TOML basic string."""
    # JSON's escapes are a subset of TOML's, except that TOML also forbids a raw DEL.
    return json.dumps(value, ensure_ascii=False).replace('\x7f', '\\u007f')


def render_agent(stem: str, fields: dict[str, str], body: str) -> str:
    """Render the Codex TOML agent for one catalog agent."""
    tools = {tool.strip() for tool in fields.get('tools', '').split(',')}
    sandbox = 'workspace-write' if tools & WRITE_TOOLS else 'read-only'
    return (
        f'name = {toml_string(stem)}\n'
        f'description = {toml_string(fields["description"])}\n'
        f'sandbox_mode = {toml_string(sandbox)}\n'
        f'developer_instructions = {toml_string(body)}\n'
    )


def codex_agents_dir() -> Path:
    """Resolve the directory Codex reads user-scoped agents from."""
    codex_home = os.environ.get('CODEX_HOME') or str(Path.home() / '.codex')
    return Path(codex_home) / 'agents'


def write_if_changed(target: Path, content: str) -> None:
    """Replace `target` with `content` atomically, leaving an identical file alone."""
    if target.exists() and target.read_text(encoding='utf-8') == content:
        return
    staging = target.with_name(f'.{target.name}.tmp')
    staging.write_text(content, encoding='utf-8')
    os.replace(staging, target)


def main() -> int:
    """Install every catalog agent and prune the ones the catalog dropped."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument('--plugin-root', type=Path, default=Path(__file__).resolve().parents[1])
    arguments = parser.parse_args()

    source_dir = arguments.plugin_root / 'agents'
    if not source_dir.is_dir():
        print(f'ERROR: {source_dir} is not a directory', file=sys.stderr)
        return PREFLIGHT_ERROR

    try:
        rendered = {
            f'{OWNED_PREFIX}{path.name.removesuffix(AGENT_SUFFIX)}.toml': render_agent(
                path.name.removesuffix(AGENT_SUFFIX), *parse_agent(path)
            )
            for path in sorted(source_dir.glob(f'*{AGENT_SUFFIX}'))
        }
    except InvalidAgentError as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return INVALID_AGENT

    target_dir = codex_agents_dir()
    target_dir.mkdir(parents=True, exist_ok=True)
    for name, content in rendered.items():
        write_if_changed(target_dir / name, content)
        print(f'INSTALLED={target_dir / name}')
    for stale in sorted(target_dir.glob(f'{OWNED_PREFIX}*.toml')):
        if stale.name not in rendered:
            stale.unlink()
            print(f'REMOVED={stale}')
    return 0


if __name__ == '__main__':
    rc.RESULT_CODES[INVALID_AGENT] = 'INVALID_AGENT'
    rc.install()
    rc.run(main)
