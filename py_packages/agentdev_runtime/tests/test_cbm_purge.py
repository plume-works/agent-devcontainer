"""Clearing codebase-memory-mcp's leftovers from persisted agent configuration."""

from __future__ import annotations

import json
from pathlib import Path

from agentdev_runtime import cbm_purge, settings as env
import pytest

BINARY = cbm_purge.BINARY
CBM_HOOK = {'type': 'command', 'command': f'/home/a/.local/bin/{BINARY}', 'args': ['hook-augment']}
USER_HOOK = {'type': 'command', 'command': '/home/a/my-hook'}
BLOCK = f'<!-- {BINARY}:start -->\n# Codebase Memory\n<!-- {BINARY}:end -->\n'
PLUGIN = f'// {BINARY}:start\nconst BIN = "x"\n// {BINARY}:end\n'


class Home:
    """A home holding what ``codebase-memory-mcp install`` writes, plus the user's own config."""

    def __init__(self, root: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        self.root = root
        self.claude = root / '.claude'
        self.opencode = root / '.config/opencode'
        self.claude_json = root / '.claude.json'
        monkeypatch.setenv('OPENCODE_CONFIG_DIR', str(self.opencode))
        self.settings = env.Settings(
            {
                'HOME': str(root),
                'AGENTDEV_CLAUDE_DIR': str(self.claude),
                'AGENTDEV_CLAUDE_JSON': str(self.claude_json),
            }
        )

    def write(self, path: Path, content: str) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def link(self, path: Path, content: str) -> Path:
        """Make ``path`` a symlink into the user's dotfiles; return the link's target."""
        target = self.write(self.root / 'dotfiles' / path.name, content)
        path.unlink(missing_ok=True)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.symlink_to(target)
        return target

    def install(self) -> None:
        settings = {
            'theme': 'dark',
            'hooks': {
                'PreToolUse': [
                    {'matcher': 'Grep|Glob|Bash', 'hooks': [CBM_HOOK]},
                    {'matcher': 'Bash', 'hooks': [USER_HOOK, CBM_HOOK]},
                ],
                'SubagentStart': [{'matcher': '*', 'hooks': [CBM_HOOK]}],
            },
        }
        self.write(self.claude / 'settings.json', json.dumps(settings))
        state = {'mcpServers': {BINARY: {'command': BINARY}, 'mine': {}}, 'projects': {'/w': {}}}
        target = self.write(self.claude / 'claude.json', json.dumps(state))
        self.claude_json.symlink_to(target)
        config = {'mcp': {BINARY: {'type': 'local'}}, 'plugin': ['/catalog']}
        self.write(self.opencode / 'opencode.json', json.dumps(config))
        self.write(self.opencode / 'AGENTS.md', f'my rules\n\n{BLOCK}')
        self.write(self.opencode / 'plugins/cbm-augment.ts', PLUGIN)
        for root in (self.claude, self.opencode):
            for name in cbm_purge.AGENTS:
                self.write(root / 'agents' / name, 'agent')
            self.write(root / 'agents/mine.md', 'agent')
            self.write(root / 'skills/codebase-memory/SKILL.md', 'skill')
            self.write(root / 'skills/mine/SKILL.md', 'skill')
        self.write(self.claude / 'hooks/cbm-session-reminder', 'hook')
        self.write(self.claude / 'hooks/mine', 'hook')
        self.write(self.root / '.local/bin' / BINARY, 'binary')
        self.write(self.root / '.local/bin/iwe', 'binary')
        self.write(self.root / '.cache' / BINARY / 'project.db', 'index')


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Home:
    return Home(tmp_path, monkeypatch)


def test_purge_removes_every_cbm_artifact_and_keeps_the_users(home: Home) -> None:
    home.install()

    cbm_purge.purge(home.settings)

    settings = json.loads((home.claude / 'settings.json').read_text())
    assert settings == {
        'theme': 'dark',
        'hooks': {'PreToolUse': [{'matcher': 'Bash', 'hooks': [USER_HOOK]}]},
    }
    assert json.loads(home.claude_json.read_text()) == {
        'mcpServers': {'mine': {}},
        'projects': {'/w': {}},
    }
    config = json.loads((home.opencode / 'opencode.json').read_text())
    assert config == {'plugin': ['/catalog']}
    assert (home.opencode / 'AGENTS.md').read_text().strip() == 'my rules'
    assert not (home.opencode / 'plugins/cbm-augment.ts').exists()
    for root in (home.claude, home.opencode):
        assert sorted(p.name for p in (root / 'agents').iterdir()) == ['mine.md']
        assert sorted(p.name for p in (root / 'skills').iterdir()) == ['mine']
    assert [p.name for p in (home.claude / 'hooks').iterdir()] == ['mine']
    assert [p.name for p in (home.root / '.local/bin').iterdir()] == ['iwe']
    assert not (home.root / '.cache' / BINARY).exists()


def test_purge_keeps_the_claude_json_symlink(home: Home) -> None:
    home.install()

    cbm_purge.purge(home.settings)

    assert home.claude_json.is_symlink()


def test_a_symlinked_agents_md_keeps_its_link_and_loses_the_block(home: Home) -> None:
    home.install()
    agents = home.opencode / 'AGENTS.md'
    target = home.link(agents, f'my rules\n\n{BLOCK}')

    cbm_purge.purge(home.settings)

    assert agents.is_symlink()
    assert agents.resolve() == target
    assert target.read_text().strip() == 'my rules'


@pytest.mark.parametrize('mode', [0o644, 0o640])
def test_an_edited_dotfiles_target_keeps_its_permissions(home: Home, mode: int) -> None:
    home.install()
    target = home.link(home.opencode / 'AGENTS.md', f'my rules\n\n{BLOCK}')
    target.chmod(mode)

    cbm_purge.purge(home.settings)

    assert target.stat().st_mode & 0o7777 == mode


def test_a_symlinked_agents_md_holding_only_the_block_keeps_its_link(home: Home) -> None:
    home.install()
    agents = home.opencode / 'AGENTS.md'
    target = home.link(agents, BLOCK)

    cbm_purge.purge(home.settings)

    assert agents.is_symlink()
    assert agents.resolve() == target
    assert BINARY not in target.read_text()


def test_a_symlinked_opencode_json_keeps_its_link_and_loses_the_server(home: Home) -> None:
    home.install()
    config = home.opencode / 'opencode.json'
    target = home.link(config, json.dumps({'mcp': {BINARY: {}, 'mine': {}}, 'theme': 'x'}))

    cbm_purge.purge(home.settings)

    assert config.is_symlink()
    assert config.resolve() == target
    assert json.loads(target.read_text()) == {'mcp': {'mine': {}}, 'theme': 'x'}


def test_a_second_purge_changes_nothing(home: Home, capsys: pytest.CaptureFixture[str]) -> None:
    home.install()
    cbm_purge.purge(home.settings)
    capsys.readouterr()

    cbm_purge.purge(home.settings)

    assert capsys.readouterr().out == ''


def test_a_home_without_cbm_is_left_untouched(home: Home) -> None:
    config = home.write(home.claude / 'settings.json', '{"theme":   "dark"}')

    cbm_purge.purge(home.settings)

    assert config.read_text() == '{"theme":   "dark"}'
    assert not home.claude_json.exists()
    assert not (home.opencode / 'opencode.json').exists()


def test_a_plugin_file_with_user_code_keeps_that_code(home: Home) -> None:
    plugin = home.write(home.opencode / 'plugins/cbm-augment.ts', f'const mine = 1\n{PLUGIN}')

    cbm_purge.purge(home.settings)

    assert plugin.read_text() == 'const mine = 1\n'


@pytest.mark.parametrize('content', ['not json', '[]', '{"hooks": {"Stop": ["bad"]}}'])
def test_an_unreadable_settings_file_warns_and_the_rest_still_runs(
    home: Home, content: str, capsys: pytest.CaptureFixture[str]
) -> None:
    home.install()
    settings = home.write(home.claude / 'settings.json', content)

    cbm_purge.purge(home.settings)

    assert settings.read_text() == content
    assert not (home.root / '.local/bin' / BINARY).exists()
    assert 'WARNING' in capsys.readouterr().err
