"""Tests for `agentdev-runtime state` and `catalog install`: identity-aware agent state."""

from __future__ import annotations

import inspect
import os
from pathlib import Path
import stat
import subprocess
import sys
import time

from agentdev_runtime import agent_state, catalog, cbm, claude_state, lifecycle
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
        'CODEX_HOME': str(home / '.codex'),
        'XDG_DATA_HOME': str(home / '.local/share'),
        'XDG_CONFIG_HOME': str(home / '.config'),
        'AGENTDEV_AGENTS_AUTH_DIR': str(root / 'auth'),
        'AGENTDEV_CLAUDE_DIR': str(home / '.claude'),
        'AGENTDEV_CLAUDE_JSON': str(home / '.claude.json'),
        'AGENTDEV_SKIP_CLAUDE_PREAPPROVE': '1',
        **extra,
    }


class Recorder:
    """Stands in for the CBM install and the pre-approval, recording each call in order."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
        self.calls: list[str] = []
        self.cbm_status = 0
        self.claude_json = Path(settings.get('AGENTDEV_CLAUDE_JSON'))

        def link_state() -> str:
            return 'symlink' if self.claude_json.is_symlink() else 'plain'

        def configure_agents(_settings: Settings, _install_dir: Path, _path: str = '') -> int:
            self.calls.append(f'cbm configure claude.json={link_state()}')
            return self.cbm_status

        def install(_daemon: cbm.Daemon) -> int:
            self.calls.append(f'cbm install claude.json={link_state()}')
            return self.cbm_status

        monkeypatch.setattr(cbm, 'configure_agents', configure_agents)
        monkeypatch.setattr(cbm, 'install', install)
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
        settings.get('CODEX_HOME'),
        f'{settings.get("XDG_DATA_HOME")}/opencode',
    ] == [
        '/root/.agents-auth',
        '/root/.claude',
        '/root/.claude.json',
        '/root/.codex',
        '/root/.local/share/opencode',
    ]


def run_links(tmp_path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*STATE, 'links'], env=runtime_env(tmp_path), capture_output=True, text=True
    )


def test_links_explicit_roots_on_fresh_volumes(tmp_path: Path):
    result = run_links(tmp_path)
    assert result.returncode == 0, result.stderr

    home, auth = tmp_path / 'home', tmp_path / 'auth'
    assert os.readlink(home / '.codex/auth.json') == str(auth / 'codex/auth.json')
    assert mode(auth / 'codex') == 0o700
    assert not (auth / 'opencode').exists()
    assert not (home / '.local/share/opencode/auth.json').exists()


def test_migrates_regular_credentials_and_preserves_other_config(tmp_path: Path):
    home = tmp_path / 'home'
    (home / '.codex').mkdir(parents=True)
    (home / '.codex/auth.json').write_text('{"codex": 1}')
    (home / '.codex/config.toml').write_text('model = "keep"\n')
    (home / '.local/share/opencode').mkdir(parents=True)
    (home / '.local/share/opencode/auth.json').write_text('{"opencode": 1}')
    (home / '.local/share/opencode/storage.db').write_text('sessions')

    result = run_links(tmp_path)
    assert result.returncode == 0, result.stderr

    auth = tmp_path / 'auth'
    assert (auth / 'codex/auth.json').read_text() == '{"codex": 1}'
    assert mode(auth / 'codex/auth.json') == 0o600
    assert (home / '.codex/auth.json').is_symlink()
    assert (home / '.local/share/opencode/auth.json').read_text() == '{"opencode": 1}'
    assert (home / '.codex/config.toml').read_text() == 'model = "keep"\n'
    assert (home / '.local/share/opencode/storage.db').read_text() == 'sessions'


def test_repairs_destroyed_and_wrong_links(tmp_path: Path):
    home, auth = tmp_path / 'home', tmp_path / 'auth'
    (auth / 'codex').mkdir(parents=True)
    (auth / 'codex/auth.json').write_text('shared')
    (home / '.codex').mkdir(parents=True)
    (home / '.codex/auth.json').symlink_to(tmp_path / 'elsewhere')

    result = run_links(tmp_path)
    assert result.returncode == 0, result.stderr

    assert (home / '.codex/auth.json').read_text() == 'shared'


def test_standalone_create_order_migrates_the_users_claude_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    home = tmp_path / 'home'
    home.mkdir()
    (home / '.claude.json').write_text('{"user": true}')
    settings = settings_for(tmp_path, DEPLOY)
    recorder = Recorder(monkeypatch, settings)

    agent_state.create(settings)

    assert (home / '.claude/claude.json').read_text() == '{"user": true}'
    assert os.readlink(home / '.claude.json') == str(home / '.claude/claude.json')
    assert recorder.calls == ['preapprove']
    assert (home / '.codex/auth.json').is_symlink()
    for agent in ('claude', 'codex'):
        assert mode(tmp_path / 'auth' / agent) == 0o700
    assert sorted(p.name for p in (tmp_path / 'auth').iterdir()) == ['claude', 'codex']
    assert not (home / '.local/share/opencode/auth.json').exists()


def test_devcontainer_create_discards_the_image_file_and_tolerates_cbm_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    home = tmp_path / 'home'
    (home / '.claude').mkdir(parents=True)
    (home / '.claude/claude.json').write_text('{"volume": true}')
    (home / '.claude.json').write_text('{"image": true}')
    settings = settings_for(tmp_path)
    recorder = Recorder(monkeypatch, settings)
    recorder.cbm_status = 1

    agent_state.create(settings)

    assert 'codebase-memory-mcp install failed' in capsys.readouterr().err
    assert (home / '.claude.json').read_text() == '{"volume": true}'
    assert recorder.calls == ['cbm configure claude.json=symlink', 'preapprove']


def test_standalone_cbm_step_installs_after_create_links_claude_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    settings = settings_for(tmp_path, DEPLOY)
    recorder = Recorder(monkeypatch, settings)
    agent_state.create(settings)
    agent_state.install_cbm(settings)
    assert recorder.calls[-1] == 'cbm install claude.json=symlink'


def test_standalone_cbm_step_fails_when_cbm_install_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    settings = settings_for(tmp_path, DEPLOY)
    Recorder(monkeypatch, settings).cbm_status = 1
    with pytest.raises(agent_state.StateError):
        agent_state.install_cbm(settings)


def test_catalog_passes_the_scope_only_to_claude(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []
    monkeypatch.setattr(catalog, 'codex', lambda _s, root: calls.append(f'codex {root}'))
    monkeypatch.setattr(
        catalog, 'claude', lambda root, scope: calls.append(f'claude {root} {scope}')
    )
    monkeypatch.setattr(catalog, 'opencode', lambda _s, root: calls.append(f'opencode {root}'))
    monkeypatch.setenv('HOME', str(tmp_path / 'home'))
    assert catalog.main(['install', '/opt/catalog', '--claude-scope', 'user']) == 0
    assert catalog.main(['install', '/opt/catalog']) == 0
    assert calls == [
        'codex /opt/catalog',
        'claude /opt/catalog user',
        'opencode /opt/catalog',
        'codex /opt/catalog',
        'claude /opt/catalog local',
        'opencode /opt/catalog',
    ]


@pytest.mark.parametrize('missing', [catalog.CLAUDE_MANIFEST, catalog.CODEX_MANIFEST, None])
def test_a_catalog_is_complete_only_with_every_client_manifest(tmp_path: Path, missing):
    for manifest in (catalog.CLAUDE_MANIFEST, catalog.CODEX_MANIFEST):
        if manifest != missing:
            (tmp_path / manifest).parent.mkdir(parents=True, exist_ok=True)
            (tmp_path / manifest).write_text('{}')
    (tmp_path / catalog.OPENCODE_BRIDGE).mkdir(parents=True)
    assert catalog.complete(tmp_path) is (missing is None)


def test_hooks_keep_their_call_order():
    ready = inspect.getsource(lifecycle.ready)
    assert ready.index('link_codex_auth') < ready.index('apply_agent_policy')
    assert ready.rstrip().endswith("hooks.run(settings, 'started')")
    created = inspect.getsource(lifecycle.created)
    assert created.index('agent_state.create') < created.index('.project()')
    assert created.index('.project()') < created.index('catalog.install')
    create = inspect.getsource(agent_state.create)
    assert create.index('link_claude_json') < create.index('install_cbm')


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


@pytest.mark.parametrize('second', ['agent-policy', 'cbm'])
def test_concurrent_config_writers_take_turns(tmp_path: Path, second: str):
    log = tmp_path / 'calls.log'
    env = runtime_env(tmp_path, AGENTDEV_RUNTIME_MODE='deploy', AGENTDEV_CBM_BIN='/nonexistent')
    first = subprocess.Popen([sys.executable, '-c', HOLD_LOCK, str(log)], env=env)
    deadline = time.monotonic() + 10
    while not log.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    subprocess.run([*STATE, second], env=env, capture_output=True, text=True)
    finished = time.time()
    assert first.wait(timeout=30) == 0
    assert log.read_text().splitlines() == ['begin', 'end']
    assert log.stat().st_mtime <= finished
    assert (tmp_path / 'home/.local/state/agentdev/agent-config.lock').exists()
