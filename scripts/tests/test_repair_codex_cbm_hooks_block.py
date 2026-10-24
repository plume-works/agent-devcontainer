from collections.abc import Iterator
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import tomllib

from cbm_pin import stage_pinned_cbm
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / '.devcontainer/scripts/repair-codex-cbm-hooks-block.py'
TMP_ROOT = REPO_ROOT / '.tmp'
# The longest base directory under which cbm 0.12.1's rendezvous socket still fits.
SOCKET_ROOT_LIMIT = 40
INSTALL = REPO_ROOT / '.devcontainer/scripts/codebase-memory-mcp-install.sh'
# cbm 0.12.1's own Codex hook tables, after a Codex write, with the opening marker gone.
ORPHANED = (Path(__file__).parent / 'fixtures/codex-config-orphaned-cbm-hooks.toml').read_text()
INSTALLED = '/home/agent/.local/bin'
OPEN = '# >>> codebase-memory-mcp SessionStart >>>\n'
CLOSE = '# <<< codebase-memory-mcp SessionStart <<<\n'
MCP_BLOCK = """\
# >>> codebase-memory-mcp MCP >>>
[mcp_servers.codebase-memory-mcp]
command = "/bin/cbm"
env_vars = ["CBM_CACHE_DIR"]

[mcp_servers.codebase-memory-mcp.tools.index_status]
approval_mode = "approve"
# <<< codebase-memory-mcp MCP <<<
"""
OWNED_HOOKS = """\
[[hooks.SessionStart]]
matcher = "startup|resume|clear|compact"

[[hooks.SessionStart.hooks]]
type = "command"
command = "'/bin/cbm' hook-augment"
timeout = 5

[[hooks.SubagentStart]]
matcher = "*"

[[hooks.SubagentStart.hooks]]
type = "command"
command = "'/bin/cbm' hook-augment"
timeout = 5
"""
FOREIGN = """\
[hooks.state]

# kept with the table it describes
[hooks.state."agentdev:hooks.json:session_start:0:0"]
trusted_hash = "sha256:abc"

[plugins."agentdev@agent-devcontainer"]
enabled = true
"""
HEADER = 'model = "gpt-5"\n'


@pytest.fixture
def codex_home(tmp_path: Path) -> Path:
    home = tmp_path / 'codex'
    home.mkdir()
    return home


def run_script(codex_home: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [SCRIPT],
        env=os.environ | {'CODEX_HOME': str(codex_home), 'CBM_INSTALL_DIR': INSTALLED},
        check=check,
        capture_output=True,
        text=True,
    )


def write_config(codex_home: Path, content: str, mode: int = 0o600) -> Path:
    config = codex_home / 'config.toml'
    config.write_bytes(content.encode())
    config.chmod(mode)
    return config


def owned_tables(text: str) -> str:
    """Return the hook tables of ``text`` between the first and last cbm hook table."""
    lines = text.splitlines(keepends=True)
    first = next(i for i, line in enumerate(lines) if line.startswith('[[hooks.'))
    last = max(i for i, line in enumerate(lines) if line.startswith('timeout = 5'))
    return ''.join(lines[first : last + 2])


def test_foreign_tables_move_below_the_closing_marker(codex_home: Path):
    original = HEADER + MCP_BLOCK + OPEN + OWNED_HOOKS + '\n' + FOREIGN + CLOSE
    config = write_config(codex_home, original)

    run_script(codex_home)

    repaired = config.read_text()
    assert repaired == HEADER + MCP_BLOCK + OPEN + OWNED_HOOKS + CLOSE + '\n' + FOREIGN
    assert tomllib.loads(repaired) == tomllib.loads(original)
    assert stat.S_IMODE(config.stat().st_mode) == 0o600


def test_foreign_tables_join_content_already_below_the_block(codex_home: Path):
    tail = '\n[tui]\nscreen_reader_detection_done = true\n'
    config = write_config(codex_home, OPEN + OWNED_HOOKS + '\n' + FOREIGN + CLOSE + tail)

    run_script(codex_home)

    assert config.read_text() == OPEN + OWNED_HOOKS + CLOSE + '\n' + FOREIGN + tail


def test_blank_lines_before_the_closing_marker_are_dropped(codex_home: Path):
    config = write_config(codex_home, OPEN + OWNED_HOOKS + '\n\n' + CLOSE)

    run_script(codex_home)

    assert config.read_text() == OPEN + OWNED_HOOKS + CLOSE


@pytest.mark.parametrize(
    'content',
    [
        pytest.param(HEADER + MCP_BLOCK + OPEN + OWNED_HOOKS + CLOSE, id='clean-block'),
        pytest.param(HEADER + MCP_BLOCK, id='no-hooks-block'),
    ],
)
def test_config_without_a_repairable_block_is_left_untouched(codex_home: Path, content: str):
    config = write_config(codex_home, content)
    before = config.stat().st_mtime_ns

    run_script(codex_home)

    assert config.read_text() == content
    assert config.stat().st_mtime_ns == before


def test_missing_config_is_not_created(codex_home: Path):
    run_script(codex_home)

    assert not (codex_home / 'config.toml').exists()


@pytest.mark.parametrize('newline', ['\n', '\r\n'], ids=['lf', 'crlf'])
def test_an_orphaned_closing_marker_loses_cbm_tables_and_keeps_codex_ones(
    codex_home: Path, newline: str
):
    original = ORPHANED.replace('\n', newline)
    config = write_config(codex_home, original, mode=0o640)

    result = run_script(codex_home)

    repaired = config.read_bytes().decode()
    expected = ORPHANED.replace(owned_tables(ORPHANED), '').replace(CLOSE, '')
    assert repaired == expected.replace('\n', newline)
    assert '[[hooks.' not in repaired and 'SessionStart' not in repaired
    parsed = tomllib.loads(repaired)
    assert parsed['marketplaces'] == tomllib.loads(original)['marketplaces']
    assert stat.S_IMODE(config.stat().st_mode) == 0o640
    assert 'repaired' in result.stdout

    before = config.stat().st_mtime_ns
    run_script(codex_home)
    assert config.read_bytes().decode() == repaired
    assert config.stat().st_mtime_ns == before


@pytest.mark.parametrize('newline', ['\n', '\r\n'], ids=['lf', 'crlf'])
def test_an_orphaned_opening_marker_is_removed_with_its_tables(codex_home: Path, newline: str):
    tables = owned_tables(ORPHANED)
    config = write_config(codex_home, (HEADER + OPEN + tables + FOREIGN).replace('\n', newline))

    run_script(codex_home)

    assert config.read_bytes().decode() == (HEADER + FOREIGN).replace('\n', newline)


def test_an_orphaned_block_keeps_the_comments_inside_its_tables(codex_home: Path):
    tables = owned_tables(ORPHANED).replace('type = "command"\n', 'type = "command"\n# mine\n', 1)
    config = write_config(codex_home, HEADER + OPEN + tables + FOREIGN)

    run_script(codex_home)

    assert config.read_text() == HEADER + '# mine\n' + FOREIGN


@pytest.mark.parametrize(
    'edit',
    [
        pytest.param(lambda t: t.replace('timeout = 5', 'timeout = 50', 1), id='edited-value'),
        pytest.param(lambda t: t.replace(f"'{INSTALLED}/", "'/opt/other/", 1), id='other-binary'),
        pytest.param(
            lambda t: t.replace('matcher = "*"', 'matcher = "*"\nextra = 1'), id='added-key'
        ),
        pytest.param(
            lambda t: t.replace(
                'timeout = 5\n\n[marketplaces', 'timeout = 5\n# note\nx = 1\n\n[marketplaces'
            ),
            id='key-after-comment',
        ),
        pytest.param(lambda t: OPEN + OWNED_HOOKS + '\n' + FOREIGN, id='foreign-hooks'),
    ],
)
def test_an_orphaned_block_with_a_foreign_hook_table_is_refused(codex_home: Path, edit):
    content = edit(ORPHANED)
    config = write_config(codex_home, content)
    before = config.stat().st_mtime_ns

    result = run_script(codex_home, check=False)

    assert result.returncode != 0
    assert '[[hooks.Session' in result.stderr or '[[hooks.Subagent' in result.stderr
    assert 'at line' in result.stderr
    assert config.read_bytes().decode() == content
    assert config.stat().st_mtime_ns == before


@pytest.fixture(scope='module')
def cbm_binary() -> Path:
    return stage_pinned_cbm()


def install(home: Path, cbm_binary: Path) -> subprocess.CompletedProcess[str]:
    env = {
        'PATH': f'{cbm_binary.parent}:{Path(shutil.which("uv")).parent}:/usr/bin:/bin',
        'HOME': str(home),
        'CODEX_HOME': str(home / '.codex'),
        'CBM_CACHE_DIR': str(home / '.cache/cbm'),
        'CBM_INSTALL_DIR': str(home / '.local/bin'),
        'CBM_RUNTIME_DIR': str(home.parent / 'rendezvous'),
    }
    return subprocess.run([INSTALL], env=env, capture_output=True, text=True, timeout=120)


def hook_events(hooks: dict) -> set[str]:
    return set(hooks.get('hooks', {}))


@pytest.fixture
def home() -> Iterator[Path]:
    # Private, so the install stays away from any live daemon of this account. CBM's
    # socket path must fit a Unix socket address, which a long checkout path overflows.
    TMP_ROOT.mkdir(exist_ok=True)
    base = TMP_ROOT if len(str(TMP_ROOT)) <= SOCKET_ROOT_LIMIT else Path('/tmp')
    root = Path(tempfile.mkdtemp(prefix='cbm-', dir=base))
    (root / 'rendezvous').mkdir(mode=0o700)
    (root / 'home').mkdir()
    yield root / 'home'
    shutil.rmtree(root, ignore_errors=True)


def test_a_first_install_registers_codex_hooks_in_a_new_hooks_json(home: Path, cbm_binary: Path):
    result = install(home, cbm_binary)
    assert result.returncode == 0, result.stdout + result.stderr

    hooks = json.loads((home / '.codex/hooks.json').read_text())
    assert hook_events(hooks) == {'SessionStart', 'SubagentStart'}
    config = (home / '.codex/config.toml').read_text()
    assert '[[hooks.' not in config and 'SessionStart' not in config


def test_an_install_moves_a_toml_hooks_block_into_hooks_json(home: Path, cbm_binary: Path):
    codex = home / '.codex'
    codex.mkdir()
    toml_block = ORPHANED.replace(INSTALLED, str(home / '.local/bin'))
    toml_block = toml_block.replace(
        '[[hooks.SessionStart]]\n', OPEN + '[[hooks.SessionStart]]\n', 1
    )
    (codex / 'config.toml').write_text(toml_block)
    kept = {'type': 'command', 'command': 'echo kept'}
    (codex / 'hooks.json').write_text(json.dumps({'hooks': {'Stop': [{'hooks': [kept]}]}}))

    result = install(home, cbm_binary)
    assert result.returncode == 0, result.stdout + result.stderr

    hooks = json.loads((codex / 'hooks.json').read_text())
    assert hook_events(hooks) == {'SessionStart', 'SubagentStart', 'Stop'}
    assert hooks['hooks']['Stop'][0]['hooks'] == [kept]
    config = (codex / 'config.toml').read_text()
    assert '[[hooks.' not in config and 'SessionStart' not in config
    assert tomllib.loads(config)['marketplaces']['agent-devcontainer']['source'] == '/opt/agentdev'

    files = [codex / 'config.toml', codex / 'hooks.json']
    before = [path.read_bytes() for path in files]
    rerun = install(home, cbm_binary)
    assert rerun.returncode == 0, rerun.stdout + rerun.stderr
    assert [path.read_bytes() for path in files] == before


def test_an_install_recovers_the_orphaned_deployment_state(home: Path, cbm_binary: Path):
    codex = home / '.codex'
    codex.mkdir()
    (codex / 'config.toml').write_text(ORPHANED.replace(INSTALLED, str(home / '.local/bin')))

    result = install(home, cbm_binary)
    assert result.returncode == 0, result.stdout + result.stderr

    assert hook_events(json.loads((codex / 'hooks.json').read_text())) == {
        'SessionStart',
        'SubagentStart',
    }
    config = (codex / 'config.toml').read_text()
    assert '[[hooks.' not in config and 'SessionStart' not in config
