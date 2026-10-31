"""Tests for the identity-aware agent-state primitives shared with the standalone runtime."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat
import subprocess
import time

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / '.devcontainer/scripts'
AGENT_STATE = SCRIPTS / 'setup-agent-state.sh'
GH_HELPER_SCRIPT = SCRIPTS / 'setup-gh-credential-helper.sh'
REAL_SCRIPTS = (
    'setup-agent-state.sh',
    'runtime-paths.sh',
    'link-codex-auth.sh',
)
STUBBED_SCRIPTS = (
    'runtime-cbm.sh',
    'codebase-memory-mcp-install.sh',
    'preapprove-claude-workspace.sh',
    'configure-codex.py',
    'configure-opencode.py',
    'reinstall-agentdev-codex.sh',
    'reinstall-agentdev-claude.sh',
    'reinstall-agentdev-opencode.sh',
)
TOKEN = 'ghs_injectedTokenValue0123456789'


def runtime_env(root: Path, **extra: str) -> dict[str, str]:
    """Return explicit standalone-style roots under ``root``."""
    home = root / 'home'
    return {
        'PATH': os.environ['PATH'],
        'HOME': str(home),
        'CODEX_HOME': str(home / '.codex'),
        'XDG_DATA_HOME': str(home / '.local/share'),
        'AGENTDEV_AGENTS_AUTH_DIR': str(root / 'auth'),
        'AGENTDEV_CLAUDE_DIR': str(home / '.claude'),
        'AGENTDEV_CLAUDE_JSON': str(home / '.claude.json'),
        **extra,
    }


@pytest.fixture
def scripts(tmp_path: Path) -> Path:
    """Copy the primitives beside stubs that log each call and the ~/.claude.json state."""
    directory = tmp_path / 'scripts'
    directory.mkdir()
    for name in REAL_SCRIPTS:
        shutil.copy2(SCRIPTS / name, directory / name)
    log = tmp_path / 'calls.log'
    for name in STUBBED_SCRIPTS:
        stub = directory / name
        stub.write_text(
            '#!/usr/bin/env bash\n'
            'link=plain; [[ -L "$AGENTDEV_CLAUDE_JSON" ]] && link=symlink\n'
            f'echo "{name} $* claude.json=$link" >> "{log}"\n'
            f'exit "${{STUB_EXIT_{name.split(".")[0].replace("-", "_").upper()}:-0}}"\n'
        )
        stub.chmod(0o755)
    return directory


def calls(tmp_path: Path) -> list[str]:
    log = tmp_path / 'calls.log'
    return log.read_text().splitlines() if log.exists() else []


def run_state(scripts: Path, root: Path, *args: str, **extra: str):
    return subprocess.run(
        [scripts / 'setup-agent-state.sh', *args],
        env=runtime_env(root, **extra),
        capture_output=True,
        text=True,
    )


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_defaults_are_the_devcontainer_root_layout():
    printed = subprocess.run(
        [
            'bash',
            '-c',
            f'source "{SCRIPTS}/runtime-paths.sh"; echo "$agentdev_auth_dir '
            '$agentdev_claude_dir $agentdev_claude_json $agentdev_codex_home '
            '$agentdev_opencode_data"',
        ],
        env={'PATH': os.environ['PATH'], 'HOME': '/root'},
        capture_output=True,
        text=True,
        check=True,
    ).stdout.split()
    assert printed == [
        '/root/.agents-auth',
        '/root/.claude',
        '/root/.claude.json',
        '/root/.codex',
        '/root/.local/share/opencode',
    ]


def test_links_explicit_roots_on_fresh_volumes(scripts: Path, tmp_path: Path):
    result = run_state(scripts, tmp_path, 'links')
    assert result.returncode == 0, result.stderr

    home, auth = tmp_path / 'home', tmp_path / 'auth'
    assert os.readlink(home / '.codex/auth.json') == str(auth / 'codex/auth.json')
    assert mode(auth / 'codex') == 0o700
    assert not (auth / 'opencode').exists()
    assert not (home / '.local/share/opencode/auth.json').exists()


def test_migrates_regular_credentials_and_preserves_other_config(scripts: Path, tmp_path: Path):
    home = tmp_path / 'home'
    (home / '.codex').mkdir(parents=True)
    (home / '.codex/auth.json').write_text('{"codex": 1}')
    (home / '.codex/config.toml').write_text('model = "keep"\n')
    (home / '.local/share/opencode').mkdir(parents=True)
    (home / '.local/share/opencode/auth.json').write_text('{"opencode": 1}')
    (home / '.local/share/opencode/storage.db').write_text('sessions')

    result = run_state(scripts, tmp_path, 'links')
    assert result.returncode == 0, result.stderr

    auth = tmp_path / 'auth'
    assert (auth / 'codex/auth.json').read_text() == '{"codex": 1}'
    assert mode(auth / 'codex/auth.json') == 0o600
    assert (home / '.codex/auth.json').is_symlink()
    assert (home / '.local/share/opencode/auth.json').read_text() == '{"opencode": 1}'
    assert (home / '.codex/config.toml').read_text() == 'model = "keep"\n'
    assert (home / '.local/share/opencode/storage.db').read_text() == 'sessions'


def test_repairs_destroyed_and_wrong_links(scripts: Path, tmp_path: Path):
    home, auth = tmp_path / 'home', tmp_path / 'auth'
    (auth / 'codex').mkdir(parents=True)
    (auth / 'codex/auth.json').write_text('shared')

    result = run_state(scripts, tmp_path, 'links')
    assert result.returncode == 0, result.stderr

    assert (home / '.codex/auth.json').read_text() == 'shared'


def test_standalone_create_order_migrates_the_users_claude_json(scripts: Path, tmp_path: Path):
    home = tmp_path / 'home'
    home.mkdir()
    (home / '.claude.json').write_text('{"user": true}')

    result = run_state(scripts, tmp_path, 'create', AGENTDEV_RUNTIME_MODE='deploy')
    assert result.returncode == 0, result.stderr

    assert (home / '.claude/claude.json').read_text() == '{"user": true}'
    assert os.readlink(home / '.claude.json') == str(home / '.claude/claude.json')
    assert [line.split()[0] for line in calls(tmp_path)] == ['preapprove-claude-workspace.sh']
    assert (home / '.codex/auth.json').is_symlink()
    for agent in ('claude', 'codex'):
        assert mode(tmp_path / 'auth' / agent) == 0o700
    assert sorted(p.name for p in (tmp_path / 'auth').iterdir()) == ['claude', 'codex']
    assert not (home / '.local/share/opencode/auth.json').exists()


def test_devcontainer_create_discards_the_image_file_and_tolerates_cbm_failure(
    scripts: Path, tmp_path: Path
):
    home = tmp_path / 'home'
    (home / '.claude').mkdir(parents=True)
    (home / '.claude/claude.json').write_text('{"volume": true}')
    (home / '.claude.json').write_text('{"image": true}')

    result = run_state(scripts, tmp_path, 'create', STUB_EXIT_CODEBASE_MEMORY_MCP_INSTALL='1')
    assert result.returncode == 0, result.stderr

    assert 'codebase-memory-mcp install failed' in result.stderr
    assert (home / '.claude.json').read_text() == '{"volume": true}'
    assert calls(tmp_path)[0] == 'codebase-memory-mcp-install.sh  claude.json=symlink'


def test_standalone_cbm_step_installs_after_create_links_claude_json(
    scripts: Path, tmp_path: Path
):
    assert run_state(scripts, tmp_path, 'create', AGENTDEV_RUNTIME_MODE='deploy').returncode == 0
    result = run_state(scripts, tmp_path, 'cbm', AGENTDEV_RUNTIME_MODE='deploy')
    assert result.returncode == 0, result.stderr
    assert calls(tmp_path)[-1] == 'runtime-cbm.sh install claude.json=symlink'


def test_standalone_cbm_step_fails_when_cbm_install_fails(scripts: Path, tmp_path: Path):
    result = run_state(
        scripts,
        tmp_path,
        'cbm',
        AGENTDEV_RUNTIME_MODE='deploy',
        STUB_EXIT_RUNTIME_CBM='1',
    )
    assert result.returncode == 1


def test_catalog_passes_the_scope_only_to_claude(scripts: Path, tmp_path: Path):
    result = run_state(scripts, tmp_path, 'catalog', '/opt/catalog', 'user')
    assert result.returncode == 0, result.stderr
    assert [line.rsplit(' claude.json', 1)[0] for line in calls(tmp_path)] == [
        'reinstall-agentdev-codex.sh /opt/catalog',
        'reinstall-agentdev-claude.sh /opt/catalog user',
        'reinstall-agentdev-opencode.sh /opt/catalog',
    ]


def test_hooks_keep_their_call_order():
    post_start = (SCRIPTS / 'postStartCommand.sh').read_text()
    assert post_start.index('agentdev-runtime xpra') < post_start.index(
        'devcontainer-ready.sh" --no-wait'
    )
    ready = (SCRIPTS / 'devcontainer-ready.sh').read_text()
    assert ready.index('setup-agent-state.sh" links') < ready.index('agent-policy')
    assert ready.rstrip().endswith('"$script_dir/run-agentdev-hooks.sh" started')
    created = (SCRIPTS / 'devcontainer-created.sh').read_text()
    assert created.index('setup-agent-state.sh" create') < created.index(
        'runtime-workspace.sh" project'
    )
    assert created.index('runtime-workspace.sh" project') < created.index(
        'setup-agent-state.sh" catalog'
    )


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

    setup = subprocess.run(
        [GH_HELPER_SCRIPT], env=env, cwd=not_yet_cloned, capture_output=True, text=True
    )
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

    setup = subprocess.run([GH_HELPER_SCRIPT], env=env, capture_output=True, text=True)
    assert setup.returncode == 0, setup.stderr
    assert 'Configured gh as the git credential helper.' in setup.stdout


@pytest.mark.parametrize('second', ['catalog', 'agent-policy', 'cbm'])
def test_concurrent_config_writers_take_turns(scripts: Path, tmp_path: Path, second: str):
    log = tmp_path / 'calls.log'
    slow = scripts / 'reinstall-agentdev-codex.sh'
    slow.write_text(f'#!/usr/bin/env bash\necho begin >> "{log}"\nsleep 1\necho end >> "{log}"\n')
    for name in ('configure-codex.py', 'runtime-cbm.sh'):
        (scripts / name).write_text(f'#!/usr/bin/env bash\necho other >> "{log}"\n')
    env = runtime_env(tmp_path, AGENTDEV_RUNTIME_MODE='deploy')
    args = {
        'catalog': ['catalog', '/opt/catalog'],
        'agent-policy': ['agent-policy'],
        'cbm': ['cbm'],
    }
    first = subprocess.Popen(
        [scripts / 'setup-agent-state.sh', 'catalog', '/opt/catalog'], env=env
    )
    deadline = time.monotonic() + 10
    while 'begin' not in calls(tmp_path) and time.monotonic() < deadline:
        time.sleep(0.05)
    result = run_state(scripts, tmp_path, *args[second], AGENTDEV_RUNTIME_MODE='deploy')
    assert first.wait(timeout=30) == 0
    assert result.returncode == 0, result.stderr
    lines = [line for line in calls(tmp_path) if line in {'begin', 'end', 'other'}]
    assert lines[:2] == ['begin', 'end'], lines
    assert (tmp_path / 'home/.local/state/agentdev/agent-config.lock').exists()
