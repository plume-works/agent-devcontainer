"""Codex's managed policy keys, written without disturbing the rest of config.toml."""

from pathlib import Path
import tomllib

from agentdev_runtime import codex_config


def test_a_new_config_gets_the_managed_keys(tmp_path: Path) -> None:
    codex_config.configure(tmp_path / 'codex')
    config = tmp_path / 'codex/config.toml'
    assert tomllib.loads(config.read_text()) == codex_config.MANAGED_SETTINGS
    assert config.stat().st_mode & 0o777 == 0o600
    assert (tmp_path / 'codex').stat().st_mode & 0o777 == 0o700


def test_existing_keys_are_replaced_and_comments_kept() -> None:
    current = '# leading\nsandbox_mode = "read-only"\nmodel = "x"\n'
    rendered = codex_config.render_config(current)
    assert '# leading' in rendered
    parsed = tomllib.loads(rendered)
    assert parsed['sandbox_mode'] == 'danger-full-access'
    assert parsed['approval_policy'] == 'never'
    assert parsed['model'] == 'x'


def test_new_keys_go_above_a_leading_comment_block() -> None:
    rendered = codex_config.render_config('# >>> tool >>>\n[tool]\na = 1\n# <<< tool <<<\n')
    assert rendered.index('approval_policy') < rendered.index('# >>> tool >>>')
