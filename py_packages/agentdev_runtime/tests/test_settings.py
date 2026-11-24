"""The settings module: one default per variable."""

from pathlib import Path

from agentdev_runtime.settings import BY_NAME, Settings, VARIABLES
import pytest

README = Path(__file__).resolve().parents[1] / 'README.md'


def test_every_variable_is_declared_once() -> None:
    names = [variable.name for variable in VARIABLES]
    assert len(names) == len(set(names))


def test_the_readme_lists_every_variable() -> None:
    text = README.read_text()
    missing = [v.name for v in VARIABLES if f'| `{v.name}` ' not in text]
    assert not missing


def test_environment_wins_over_the_default() -> None:
    assert Settings({'AGENTDEV_HOOKS_ROOT': '/x'}).get('AGENTDEV_HOOKS_ROOT') == '/x'


def test_an_empty_value_takes_the_default() -> None:
    assert (
        Settings({'AGENTDEV_HOOKS_ROOT': ''}).get('AGENTDEV_HOOKS_ROOT') == '/etc/agentdev/hooks'
    )


def test_derived_defaults_follow_the_runtime_account() -> None:
    settings = Settings({'AGENTDEV_USER': 'dev'})
    assert settings.get('AGENTDEV_HOME') == '/home/dev'
    assert settings.get('CLAUDE_CONFIG_DIR') == '/home/dev/.claude'
    assert settings.get('OPENCODE_CONFIG_DIR') == '/home/dev/.config/opencode'


def test_securestorage_follows_the_claude_dir() -> None:
    settings = Settings({'AGENTDEV_CLAUDE_DIR': '/c'})
    assert settings.get('CLAUDE_SECURESTORAGE_CONFIG_DIR') == '/c'


def test_an_undeclared_variable_is_refused() -> None:
    with pytest.raises(KeyError):
        Settings({}).get('AGENTDEV_NOT_A_SETTING')


@pytest.mark.parametrize('raw', ['1', 'true', 'YES', 'on'])
def test_boolean_true_words(raw: str) -> None:
    settings = Settings({'AGENTDEV_SKIP_XPRA': raw})
    assert settings.boolean('AGENTDEV_SKIP_XPRA') is True
    assert settings.errors == []


def test_boolean_rejects_other_words() -> None:
    settings = Settings({'AGENTDEV_SKIP_XPRA': 'maybe'})
    assert settings.boolean('AGENTDEV_SKIP_XPRA') is False
    assert settings.errors and 'AGENTDEV_SKIP_XPRA' in settings.errors[0]


def test_the_firewall_default_is_off() -> None:
    assert Settings({}).boolean('ENABLE_FIREWALL') is False


def test_numeric_defaults_parse() -> None:
    for variable in VARIABLES:
        default = variable.default
        if isinstance(default, str) and default.isdigit():
            assert float(Settings({}).get(variable.name)) == int(default)
    assert BY_NAME['AGENTDEV_READY_TIMEOUT'].default == '900'


def test_home_derived_defaults_follow_the_caller_home() -> None:
    settings = Settings({'AGENTDEV_USER': 'dev', 'HOME': '/sandbox'})
    assert settings.get('CLAUDE_CONFIG_DIR') == '/sandbox/.claude'
