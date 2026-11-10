"""Tests for `agentdev-runtime state` and `catalog install`: identity-aware agent state."""

from __future__ import annotations

import inspect
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

from agentdev_runtime import agent_state, catalog, cbm_purge, claude_state, lifecycle
from agentdev_runtime.settings import DEPLOY, DEVCONTAINER, Settings
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GH_HELPER = [sys.executable, '-m', 'agentdev_runtime', 'git', 'credential-helper']
STATE = [sys.executable, '-m', 'agentdev_runtime', 'state']
TOKEN = 'ghs_injectedTokenValue0123456789'


def runtime_env(root: Path, **extra: str) -> dict[str, str]:
    """Return explicit standalone-style roots under ``root``."""
    home = root / 'home'
    return {
        'PATH': os.environ['PATH'],
        'HOME': str(home),
        'XDG_DATA_HOME': str(home / '.local/share'),
        'XDG_CONFIG_HOME': str(home / '.config'),
        'AGENTDEV_AGENTS_AUTH_DIR': str(root / 'auth'),
        'AGENTDEV_CLAUDE_DIR': str(home / '.claude'),
        'AGENTDEV_CLAUDE_JSON': str(home / '.claude.json'),
        'AGENTDEV_SKIP_CLAUDE_PREAPPROVE': '1',
        **extra,
    }


class Recorder:
    """Stands in for the CBM purge and the pre-approval, recording each call in order."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
        self.calls: list[str] = []
        self.claude_json = Path(settings.get('AGENTDEV_CLAUDE_JSON'))

        def link_state() -> str:
            return 'symlink' if self.claude_json.is_symlink() else 'plain'

        monkeypatch.setattr(
            cbm_purge,
            'purge',
            lambda _settings: self.calls.append(f'purge claude.json={link_state()}'),
        )
        monkeypatch.setattr(
            claude_state, 'preapprove', lambda _settings: self.calls.append('preapprove')
        )


def settings_for(tmp_path: Path, mode: str = DEVCONTAINER, **extra: str) -> Settings:
    return Settings(runtime_env(tmp_path, AGENTDEV_RUNTIME_MODE=mode, **extra))


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_devcontainer_defaults_are_the_root_layout():
    settings = Settings({'AGENTDEV_RUNTIME_MODE': DEVCONTAINER, 'HOME': '/root'})
    assert [
        settings.get('AGENTDEV_AGENTS_AUTH_DIR'),
        settings.get('AGENTDEV_CLAUDE_DIR'),
        settings.get('AGENTDEV_CLAUDE_JSON'),
        f'{settings.get("XDG_DATA_HOME")}/opencode',
    ] == [
        '/root/.agents-auth',
        '/root/.claude',
        '/root/.claude.json',
        '/root/.local/share/opencode',
    ]


@pytest.mark.parametrize('profile', [DEPLOY, DEVCONTAINER])
def test_create_replaces_the_claude_json_link_with_its_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, profile: str
):
    home = tmp_path / 'home'
    (home / '.claude').mkdir(parents=True)
    (home / '.claude/claude.json').write_text('{"volume": true}')
    (home / '.claude/claude.json').chmod(0o600)
    (home / '.claude.json').symlink_to(home / '.claude/claude.json')
    settings = settings_for(tmp_path, profile)
    recorder = Recorder(monkeypatch, settings)

    agent_state.create(settings)

    assert not (home / '.claude.json').is_symlink()
    assert (home / '.claude.json').read_text() == '{"volume": true}'
    assert mode(home / '.claude.json') == 0o600
    assert not (home / '.claude/claude.json').exists()
    assert recorder.calls == ['purge claude.json=plain', 'preapprove']
    assert mode(tmp_path / 'auth/claude') == 0o700
    assert sorted(p.name for p in (tmp_path / 'auth').iterdir()) == ['claude']


@pytest.mark.parametrize('profile', [DEPLOY, DEVCONTAINER])
def test_create_keeps_a_regular_claude_json_and_links_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, profile: str
):
    home = tmp_path / 'home'
    home.mkdir()
    (home / '.claude.json').write_text('{"user": true}')
    settings = settings_for(tmp_path, profile)
    recorder = Recorder(monkeypatch, settings)

    agent_state.create(settings)

    assert (home / '.claude.json').read_text() == '{"user": true}'
    assert not (home / '.claude/claude.json').exists()
    assert recorder.calls == ['purge claude.json=plain', 'preapprove']


def test_create_leaves_a_link_elsewhere_alone(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    home = tmp_path / 'home'
    home.mkdir()
    (tmp_path / 'dotfiles.json').write_text('{"dotfiles": true}')
    (home / '.claude.json').symlink_to(tmp_path / 'dotfiles.json')
    settings = settings_for(tmp_path, DEPLOY)
    Recorder(monkeypatch, settings)

    agent_state.create(settings)

    assert (home / '.claude.json').is_symlink()
    assert (tmp_path / 'dotfiles.json').read_text() == '{"dotfiles": true}'


def test_catalog_passes_the_scope_only_to_claude(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []
    monkeypatch.setattr(
        catalog, 'claude', lambda root, scope: calls.append(f'claude {root} {scope}')
    )
    monkeypatch.setattr(catalog, 'opencode', lambda _s, root: calls.append(f'opencode {root}'))
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    assert catalog.main(['install', '/opt/catalog', '--claude-scope', 'user']) == 0
    assert catalog.main(['install', '/opt/catalog']) == 0
    assert calls == [
        'claude /opt/catalog user',
        'opencode /opt/catalog',
        'claude /opt/catalog local',
        'opencode /opt/catalog',
    ]


@pytest.mark.parametrize('missing', [catalog.CLAUDE_MANIFEST, catalog.OPENCODE_BRIDGE, None])
def test_a_catalog_is_complete_only_with_every_client_manifest(tmp_path: Path, missing):
    if missing != catalog.CLAUDE_MANIFEST:
        (tmp_path / catalog.CLAUDE_MANIFEST).parent.mkdir(parents=True)
        (tmp_path / catalog.CLAUDE_MANIFEST).write_text('{}')
    if missing != catalog.OPENCODE_BRIDGE:
        (tmp_path / catalog.OPENCODE_BRIDGE).mkdir(parents=True)
    assert catalog.complete(tmp_path) is (missing is None)


def test_hooks_keep_their_call_order():
    ready = inspect.getsource(lifecycle.ready)
    assert ready.index('credential_helper') < ready.index('apply_agent_policy')
    assert ready.rstrip().endswith("hooks.run(settings, 'started')")
    created = inspect.getsource(lifecycle.created)
    assert created.index('agent_state.create') < created.index('.project()')
    assert created.index('.project()') < created.index('catalog.install')


def fake_gh(directory: Path) -> None:
    """Write a gh that authenticates from an injected token, like the real CLI."""
    (directory / 'gh').write_text(
        '#!/bin/sh\n'
        'token="${GH_TOKEN:-$GITHUB_TOKEN}"\n'
        'case "$1 $2" in\n'
        '  "auth status") [ -n "$token" ] || [ "$GH_TEST_AUTHENTICATED" = 1 ]; exit ;;\n'
        '  "auth setup-git") git config --global '
        "credential.https://github.com.helper '!gh auth git-credential' ;;\n"
        '  "auth git-credential")\n'
        '    cat >/dev/null\n'
        '    printf "protocol=https\\nhost=github.com\\nusername=x-access-token\\n"\n'
        '    printf "password=%s\\n" "$token" ;;\n'
        'esac\n'
    )
    (directory / 'gh').chmod(0o755)


def gh_env(tmp_path: Path, **extra: str) -> dict[str, str]:
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir(exist_ok=True)
    fake_gh(bin_dir)
    (tmp_path / 'gitconfig').touch()
    return {
        'PATH': f'{bin_dir}:/usr/bin:/bin',
        'HOME': str(tmp_path / 'home'),
        'GIT_CONFIG_GLOBAL': str(tmp_path / 'gitconfig'),
        'GIT_CONFIG_NOSYSTEM': '1',
        'GIT_TERMINAL_PROMPT': '0',
        'AGENTDEV_KEYRING_ENV_FILE': str(tmp_path / 'absent.env'),
        **extra,
    }


def test_injected_token_authenticates_https_before_any_checkout_exists(tmp_path: Path):
    (tmp_path / 'home').mkdir()
    not_yet_cloned = tmp_path / 'empty'
    not_yet_cloned.mkdir()
    env = gh_env(tmp_path, GITHUB_TOKEN=TOKEN)

    setup = subprocess.run(GH_HELPER, env=env, cwd=not_yet_cloned, capture_output=True, text=True)
    assert setup.returncode == 0, setup.stderr

    filled = subprocess.run(
        ['git', 'credential', 'fill'],
        input='protocol=https\nhost=github.com\n\n',
        env=env,
        cwd=not_yet_cloned,
        capture_output=True,
        text=True,
        check=True,
    )
    assert f'password={TOKEN}' in filled.stdout.splitlines()
    assert TOKEN not in setup.stdout + setup.stderr
    persisted = [p for p in tmp_path.rglob('*') if p.is_file() and TOKEN in p.read_text()]
    assert persisted == []


def test_keyring_environment_file_location_is_configurable(tmp_path: Path):
    (tmp_path / 'home').mkdir()
    keyring_env = tmp_path / 'run/keyring.env'
    keyring_env.parent.mkdir()
    keyring_env.write_text('export GH_TEST_AUTHENTICATED=1\n')
    env = gh_env(tmp_path, AGENTDEV_KEYRING_ENV_FILE=str(keyring_env))

    setup = subprocess.run(GH_HELPER, env=env, capture_output=True, text=True)
    assert setup.returncode == 0, setup.stderr
    assert 'Configured gh as the git credential helper.' in setup.stdout


HOLD_LOCK = """
import sys, time
from pathlib import Path
from agentdev_runtime import agent_state, settings
log = Path(sys.argv[1])
with agent_state.config_lock(settings.Settings()):
    log.write_text('begin\\n')
    time.sleep(1)
    with log.open('a') as handle:
        handle.write('end\\n')
"""


def test_concurrent_config_writers_take_turns(tmp_path: Path):
    log = tmp_path / 'calls.log'
    env = runtime_env(tmp_path, AGENTDEV_RUNTIME_MODE='deploy')
    first = subprocess.Popen([sys.executable, '-c', HOLD_LOCK, str(log)], env=env)
    deadline = time.monotonic() + 10
    while not log.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    subprocess.run([*STATE, 'agent-policy'], env=env, capture_output=True, text=True)
    finished = time.time()
    assert first.wait(timeout=30) == 0
    assert log.read_text().splitlines() == ['begin', 'end']
    assert log.stat().st_mtime <= finished
    assert (tmp_path / 'home/.local/state/agentdev/agent-config.lock').exists()
