"""The Codex hooks-block repair: foreign tables leave the block, an orphan loses cbm's own."""

from pathlib import Path

from agentdev_runtime import codex_hooks
import pytest

BINARY = '/home/agent/.local/bin/codebase-memory-mcp'
OPEN = codex_hooks.OPEN_MARKER + '\n'
CLOSE = codex_hooks.CLOSE_MARKER + '\n'
FOREIGN = '[plugins."agentdev@agent-devcontainer"]\nenabled = true\n'


def owned() -> str:
    lines = []
    for header, keys in codex_hooks.canonical_tables(BINARY).items():
        lines += [header, *keys, '']
    return '\n'.join(lines)


def test_a_config_without_markers_is_unchanged() -> None:
    assert codex_hooks.repair('model = "x"\n', BINARY) == 'model = "x"\n'


def test_foreign_tables_inside_a_complete_block_move_below_it() -> None:
    current = OPEN + owned() + '\n' + FOREIGN + CLOSE
    repaired = codex_hooks.repair(current, BINARY)
    block, after = repaired.split(CLOSE)
    assert FOREIGN not in block
    assert FOREIGN.strip() in after


def test_an_orphaned_block_of_canonical_tables_is_removed() -> None:
    repaired = codex_hooks.repair(FOREIGN + '\n' + owned() + CLOSE, BINARY)
    assert '[[hooks.' not in repaired
    assert codex_hooks.CLOSE_MARKER not in repaired
    assert FOREIGN.strip() in repaired


def test_an_orphan_claiming_a_foreign_hook_is_refused() -> None:
    edited = owned().replace('timeout = 5', 'timeout = 9', 1)
    with pytest.raises(codex_hooks.ForeignHook):
        codex_hooks.repair(edited + CLOSE, BINARY)


def test_repair_config_skips_a_missing_config(tmp_path: Path) -> None:
    assert codex_hooks.repair_config(tmp_path, '/x') == 0


def test_repair_config_keeps_the_file_mode(tmp_path: Path) -> None:
    config = tmp_path / 'config.toml'
    config.write_text(OPEN + owned() + FOREIGN + CLOSE)
    config.chmod(0o640)
    assert codex_hooks.repair_config(tmp_path, str(Path(BINARY).parent)) == 0
    assert config.stat().st_mode & 0o777 == 0o640
    assert config.read_text().index(FOREIGN.strip()) > config.read_text().index(CLOSE.strip())
