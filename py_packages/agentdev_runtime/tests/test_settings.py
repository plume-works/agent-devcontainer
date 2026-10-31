"""The settings module: one default per variable, profile-keyed where profiles differ."""

from pathlib import Path

from agentdev_runtime.settings import BY_NAME, DEPLOY, DEVCONTAINER, Settings, VARIABLES
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
    assert Settings({'AGENTDEV_RUN_DIR': '/x'}).get('AGENTDEV_RUN_DIR') == '/x'


def test_an_empty_value_takes_the_default() -> None:
    assert Settings({'AGENTDEV_RUN_DIR': ''}).get('AGENTDEV_RUN_DIR') == '/run/agentdev'


@pytest.mark.parametrize(
    ('mode', 'expected'),
    [(DEVCONTAINER, '/root/.agents-auth'), (DEPLOY, '/var/lib/agentdev/auth')],
)
def test_the_profile_keys_a_disputed_default(mode: str, expected: str) -> None:
    assert Settings({'AGENTDEV_RUNTIME_MODE': mode}).get('AGENTDEV_AGENTS_AUTH_DIR') == expected


def test_an_unknown_mode_resolves_devcontainer_defaults() -> None:
    assert Settings({'AGENTDEV_RUNTIME_MODE': 'bogus'}).get('AGENTDEV_USER') == 'root'


def test_derived_defaults_follow_the_runtime_account() -> None:
    settings = Settings({'AGENTDEV_RUNTIME_MODE': DEPLOY})
    assert settings.get('AGENTDEV_HOME') == '/home/agent'
    assert settings.get('CODEX_HOME') == '/home/agent/.codex'
    assert settings.get('OPENCODE_CONFIG_DIR') == '/home/agent/.config/opencode'
    assert settings.get('XDG_RUNTIME_DIR') == '/run/user/1000'


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


@pytest.mark.parametrize('raw', ['0', '-1', 'nan', 'inf', 'x'])
def test_positive_rejects_and_keeps_the_default(raw: str) -> None:
    settings = Settings({'AGENTDEV_RECOVERY_BACKOFF': raw})
    assert settings.positive('AGENTDEV_RECOVERY_BACKOFF') == 1
    assert settings.errors


def test_count_parses_and_rejects() -> None:
    assert Settings({'AGENTDEV_RECOVERY_ATTEMPTS': '5'}).count('AGENTDEV_RECOVERY_ATTEMPTS') == 5
    settings = Settings({'AGENTDEV_RECOVERY_ATTEMPTS': '1.5'})
    assert settings.count('AGENTDEV_RECOVERY_ATTEMPTS') == 3
    assert settings.errors


def test_required_and_choice() -> None:
    settings = Settings({'AGENTDEV_CLAUDE_RC_MODE': 'bad'})
    assert settings.required('AGENTDEV_RUNTIME_MODE', (DEVCONTAINER, DEPLOY)) == ''
    assert settings.choice('AGENTDEV_CLAUDE_RC_MODE', ('session', 'server')) == ''
    assert len(settings.errors) == 2


def test_numeric_defaults_parse() -> None:
    for variable in VARIABLES:
        default = variable.default
        if isinstance(default, str) and default.isdigit():
            assert Settings({}).count(variable.name) == int(default)
    assert BY_NAME['AGENTDEV_STOP_TIMEOUT'].default == '30'


def test_home_derived_defaults_follow_the_caller_home() -> None:
    settings = Settings({'AGENTDEV_RUNTIME_MODE': DEPLOY, 'HOME': '/sandbox'})
    assert settings.get('CBM_INSTALL_DIR') == '/sandbox/.local/bin'
    assert settings.get('CODEX_HOME') == '/sandbox/.codex'
