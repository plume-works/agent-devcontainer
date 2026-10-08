#!/usr/bin/env python3

"""Behavior tests for the bin/install-codex-agents.py Codex agent installer."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tomllib

import pytest

SCRIPT_PATH = 'bin/install-codex-agents.py'

READ_ONLY_AGENT = """---
name: Fixture Reviewer
description: Review a file and report findings: never edits.
tools: Bash, Read, Grep, Glob, Skill
---

# Fixture Reviewer

Read the file named in your prompt.
Report "quoted" findings with a backslash \\ and a tab\there.
"""

WRITING_AGENT = """---
name: Fixture Writer
description: Write the code a failing test asks for.
tools: Bash, Read, Edit, Write, Grep, Glob
---

Make the failing test pass — nothing more.
"""


def make_plugin(root: Path, agents: dict[str, str]) -> Path:
    """Create a fixture plugin root whose agents/ holds `agents` by stem."""
    agents_dir = root / 'plugin' / 'agents'
    agents_dir.mkdir(parents=True, exist_ok=True)
    for stale in agents_dir.glob('*.agent.md'):
        stale.unlink()
    for stem, text in agents.items():
        (agents_dir / f'{stem}.agent.md').write_text(text)
    return root / 'plugin'


def run_installer(
    plugin_root: Path, fixture_root: Path, fixture: Path, codex_home: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run the installer for `fixture` with CODEX_HOME set unless `codex_home` is None."""
    environment = {key: value for key, value in os.environ.items() if key != 'CODEX_HOME'}
    environment['HOME'] = str(fixture_root / 'home')
    if codex_home is not None:
        environment['CODEX_HOME'] = str(codex_home)
    return subprocess.run(
        [sys.executable, str(plugin_root / SCRIPT_PATH), '--plugin-root', str(fixture)],
        capture_output=True,
        text=True,
        env=environment,
        check=False,
    )


def read_agent(codex_home: Path, stem: str) -> dict[str, object]:
    """Parse the generated TOML agent for `stem`."""
    return tomllib.loads((codex_home / 'agents' / f'agentdev-{stem}.toml').read_text())


def test_writes_one_toml_agent_per_catalog_agent(plugin_root: Path, plugin_tmp_path: Path):
    """Each agent file becomes a parseable TOML agent carrying its description and body."""
    fixture = make_plugin(plugin_tmp_path, {'fixture-reviewer': READ_ONLY_AGENT})
    codex_home = plugin_tmp_path / 'codex'

    result = run_installer(plugin_root, plugin_tmp_path, fixture, codex_home)

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines()[-1] == 'RESULT=SUCCESS'
    agent = read_agent(codex_home, 'fixture-reviewer')
    assert agent['name'] == 'fixture-reviewer'
    assert agent['description'] == 'Review a file and report findings: never edits.'
    body = READ_ONLY_AGENT.split('---\n', 2)[2].strip()
    assert agent['developer_instructions'] == body


@pytest.mark.parametrize(
    ('text', 'sandbox'),
    [(READ_ONLY_AGENT, 'read-only'), (WRITING_AGENT, 'workspace-write')],
)
def test_sandbox_mode_follows_the_write_tools(
    plugin_root: Path, plugin_tmp_path: Path, text: str, sandbox: str
):
    """An agent granted Edit or Write may write the workspace; any other is read-only."""
    fixture = make_plugin(plugin_tmp_path, {'fixture': text})
    codex_home = plugin_tmp_path / 'codex'

    assert run_installer(plugin_root, plugin_tmp_path, fixture, codex_home).returncode == 0
    assert read_agent(codex_home, 'fixture')['sandbox_mode'] == sandbox


def test_removes_agents_the_catalog_no_longer_has(plugin_root: Path, plugin_tmp_path: Path):
    """A dropped agent's file disappears while the remaining agents stay current."""
    codex_home = plugin_tmp_path / 'codex'
    both = {'fixture-reviewer': READ_ONLY_AGENT, 'fixture-writer': WRITING_AGENT}
    assert (
        run_installer(
            plugin_root, plugin_tmp_path, make_plugin(plugin_tmp_path, both), codex_home
        ).returncode
        == 0
    )

    fixture = make_plugin(plugin_tmp_path, {'fixture-reviewer': READ_ONLY_AGENT})
    result = run_installer(plugin_root, plugin_tmp_path, fixture, codex_home)

    assert result.returncode == 0, result.stderr
    assert not (codex_home / 'agents' / 'agentdev-fixture-writer.toml').exists()
    assert read_agent(codex_home, 'fixture-reviewer')['name'] == 'fixture-reviewer'


def test_leaves_files_it_does_not_own(plugin_root: Path, plugin_tmp_path: Path):
    """A user's own agent, without the agentdev- prefix, is never touched."""
    codex_home = plugin_tmp_path / 'codex'
    user_agent = codex_home / 'agents' / 'codebase-memory.toml'
    user_agent.parent.mkdir(parents=True)
    user_agent.write_text('name = "codebase-memory"\n')

    fixture = make_plugin(plugin_tmp_path, {'fixture-reviewer': READ_ONLY_AGENT})
    assert run_installer(plugin_root, plugin_tmp_path, fixture, codex_home).returncode == 0

    assert user_agent.read_text() == 'name = "codebase-memory"\n'


def test_a_second_run_produces_identical_files(plugin_root: Path, plugin_tmp_path: Path):
    """Reinstalling the same catalog leaves every generated file byte-identical."""
    codex_home = plugin_tmp_path / 'codex'
    fixture = make_plugin(
        plugin_tmp_path, {'fixture-reviewer': READ_ONLY_AGENT, 'fixture-writer': WRITING_AGENT}
    )
    assert run_installer(plugin_root, plugin_tmp_path, fixture, codex_home).returncode == 0
    first = {path.name: path.read_bytes() for path in (codex_home / 'agents').iterdir()}

    assert run_installer(plugin_root, plugin_tmp_path, fixture, codex_home).returncode == 0
    second = {path.name: path.read_bytes() for path in (codex_home / 'agents').iterdir()}

    assert second == first


def test_defaults_to_the_home_codex_directory(plugin_root: Path, plugin_tmp_path: Path):
    """Without CODEX_HOME the agents land in ~/.codex/agents."""
    fixture = make_plugin(plugin_tmp_path, {'fixture-reviewer': READ_ONLY_AGENT})

    result = run_installer(plugin_root, plugin_tmp_path, fixture)

    assert result.returncode == 0, result.stderr
    assert read_agent(plugin_tmp_path / 'home' / '.codex', 'fixture-reviewer')


def test_rejects_an_agent_without_a_description(plugin_root: Path, plugin_tmp_path: Path):
    """An agent Codex could not describe fails the install and writes nothing."""
    fixture = make_plugin(plugin_tmp_path, {'broken': '---\nname: Broken\n---\n\nBody.\n'})
    codex_home = plugin_tmp_path / 'codex'

    result = run_installer(plugin_root, plugin_tmp_path, fixture, codex_home)

    assert result.returncode == 3
    assert result.stdout.splitlines()[-1] == 'RESULT=INVALID_AGENT'
    assert not (codex_home / 'agents').exists()


def test_rejects_a_plugin_root_without_agents(plugin_root: Path, plugin_tmp_path: Path):
    """A plugin root with no agents/ directory is a usage error, not an empty catalog."""
    result = run_installer(plugin_root, plugin_tmp_path, plugin_tmp_path, plugin_tmp_path / 'c')

    assert result.returncode == 2
    assert result.stdout.splitlines()[-1] == 'RESULT=PREFLIGHT_ERROR'


def test_installs_the_shipped_catalog_agents(plugin_root: Path, plugin_tmp_path: Path):
    """Every agent this plugin ships converts, so a reinstall never fails on the real catalog."""
    codex_home = plugin_tmp_path / 'codex'

    result = run_installer(plugin_root, plugin_tmp_path, plugin_root, codex_home)

    assert result.returncode == 0, result.stderr
    shipped = {path.name.removesuffix('.agent.md') for path in (plugin_root / 'agents').iterdir()}
    installed = {
        path.name.removeprefix('agentdev-').removesuffix('.toml')
        for path in (codex_home / 'agents').iterdir()
    }
    assert installed == shipped
