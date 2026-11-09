"""OpenCode's managed permission policy, keeping the user's other settings."""

import json
from pathlib import Path

from agentdev_runtime import opencode_config
import pytest


def test_a_new_config_allows_everything(tmp_path: Path) -> None:
    opencode_config.configure(tmp_path)
    config = json.loads((tmp_path / 'opencode.json').read_text())
    assert config['permission'] == {'*': 'allow', 'external_directory': {'/**': 'allow'}}
    assert config['$schema'] == opencode_config.SCHEMA


def test_jsonc_wins_and_unmanaged_keys_survive(tmp_path: Path) -> None:
    (tmp_path / 'opencode.jsonc').write_text(
        '{\n  // mine\n  "theme": "x",\n  "permission": {"bash": "ask", "*": "deny"},\n}\n'
    )
    opencode_config.configure(tmp_path)
    config = json.loads((tmp_path / 'opencode.jsonc').read_text())
    assert config['theme'] == 'x'
    assert config['permission']['bash'] == 'ask'
    assert config['permission']['*'] == 'allow'
    assert not (tmp_path / 'opencode.json').exists()


def test_a_non_object_config_is_refused(tmp_path: Path) -> None:
    (tmp_path / 'opencode.json').write_text('[]')
    with pytest.raises(ValueError):
        opencode_config.configure(tmp_path)


def test_a_configured_file_keeps_its_key_order(tmp_path: Path) -> None:
    opencode_config.configure(tmp_path)
    config = tmp_path / 'opencode.json'
    document = json.loads(config.read_text())
    document['plugin'] = ['/catalog/.opencode-plugin']
    document['mcp'] = {'server': {'type': 'local'}}
    config.write_text(json.dumps(document, indent=2) + '\n')
    before = config.read_bytes()
    opencode_config.configure(tmp_path)
    assert config.read_bytes() == before


def test_a_config_without_experimental_gains_the_depth(tmp_path: Path) -> None:
    (tmp_path / 'opencode.json').write_text('{"theme": "x"}')
    opencode_config.configure(tmp_path)
    config = json.loads((tmp_path / 'opencode.json').read_text())
    assert config['experimental'] == {'subagent_depth': opencode_config.SUBAGENT_DEPTH}


def test_other_experimental_keys_keep_their_values_and_order(tmp_path: Path) -> None:
    (tmp_path / 'opencode.json').write_text(
        '{"experimental": {"a": 1, "subagent_depth": 2, "b": true}, "theme": "x"}'
    )
    opencode_config.configure(tmp_path)
    config = json.loads((tmp_path / 'opencode.json').read_text())
    assert list(config) == ['$schema', 'experimental', 'theme', 'permission']
    assert list(config['experimental'].items()) == [
        ('a', 1),
        ('subagent_depth', opencode_config.SUBAGENT_DEPTH),
        ('b', True),
    ]


def test_a_changed_depth_is_restored(tmp_path: Path) -> None:
    (tmp_path / 'opencode.json').write_text('{"experimental": {"subagent_depth": 1}}')
    opencode_config.configure(tmp_path)
    config = json.loads((tmp_path / 'opencode.json').read_text())
    assert config['experimental']['subagent_depth'] == opencode_config.SUBAGENT_DEPTH
