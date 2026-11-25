"""Every environment value the runtime reads, parsed once, with one default per variable."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import os
from pathlib import Path

TRUE_WORDS = frozenset({'1', 'true', 'yes', 'on'})
FALSE_WORDS = frozenset({'0', 'false', 'no', 'off', ''})


@dataclass(frozen=True)
class Derived:
    """A default computed from other settings; ``text`` is how the README shows it."""

    text: str
    compute: Callable[[Settings], str]


Default = str | Derived


@dataclass(frozen=True)
class Variable:
    """One environment variable and its default."""

    name: str
    description: str
    default: Default = ''


def _home(s: Settings) -> str:
    user = s.get('AGENTDEV_USER')
    return '/root' if user == 'root' else f'/home/{user}'


def _workspace(s: Settings) -> str:
    return os.getcwd()


VARIABLES: tuple[Variable, ...] = (
    # Identity.
    Variable('AGENTDEV_USER', 'Runtime account name.', 'root'),
    Variable(
        'AGENTDEV_HOME',
        'Runtime account home.',
        Derived('`/root` for root, else `/home/$AGENTDEV_USER`', _home),
    ),
    Variable(
        'DEV_WORKSPACE_FOLDER',
        'Project checkout.',
        Derived('the working directory', _workspace),
    ),
    # Image-owned paths.
    Variable(
        'AGENTDEV_LIFECYCLE_DIR',
        'Per-container lifecycle markers.',
        '/var/lib/agentdev/lifecycle',
    ),
    Variable('AGENTDEV_HOOKS_ROOT', 'Derived-image lifecycle hook root.', '/etc/agentdev/hooks'),
    Variable(
        'AGENTDEV_EXTRA_CA_CERTS',
        'PEM bundle the bootstrap adds to the system trust store; absent or empty adds none.',
        '/etc/agentdev/extra-ca.crt',
    ),
    # Agent state.
    Variable(
        'AGENTDEV_AGENTS_AUTH_DIR',
        'Shared agent credential directory.',
        '/root/.agents-auth',
    ),
    Variable(
        'AGENTDEV_AUTH_LOCK_TIMEOUT',
        'Seconds the bootstrap waits for the shared-auth lock.',
        '60',
    ),
    Variable(
        'AGENTDEV_CONFIG_LOCK_TIMEOUT',
        'Seconds agent-state setup waits for the configuration lock.',
        '1800',
    ),
    Variable(
        'AGENTDEV_CLAUDE_DIR',
        'Claude configuration directory.',
        Derived('$HOME/.claude', lambda s: f'{s.home}/.claude'),
    ),
    Variable(
        'AGENTDEV_CLAUDE_JSON',
        'Claude state file.',
        Derived('$HOME/.claude.json', lambda s: f'{s.home}/.claude.json'),
    ),
    Variable(
        'AGENTDEV_CLAUDE_STATE_PATH',
        'Claude state file the workspace pre-approval edits.',
        Derived('$HOME/.claude.json', lambda s: f'{s.home}/.claude.json'),
    ),
    Variable(
        'CLAUDE_SECURESTORAGE_CONFIG_DIR',
        'Directory holding Claude `.credentials.json`.',
        Derived('$AGENTDEV_CLAUDE_DIR', lambda s: s.get('AGENTDEV_CLAUDE_DIR')),
    ),
    Variable(
        'CLAUDE_CONFIG_DIR',
        "Claude Code's own configuration directory.",
        Derived('$HOME/.claude', lambda s: f'{s.home}/.claude'),
    ),
    Variable(
        'XDG_CONFIG_HOME',
        'XDG configuration root.',
        Derived('$HOME/.config', lambda s: f'{s.home}/.config'),
    ),
    Variable(
        'XDG_DATA_HOME',
        'XDG data root.',
        Derived('$HOME/.local/share', lambda s: f'{s.home}/.local/share'),
    ),
    Variable(
        'XDG_STATE_HOME',
        'XDG state root.',
        Derived('$HOME/.local/state', lambda s: f'{s.home}/.local/state'),
    ),
    Variable(
        'XDG_RUNTIME_DIR',
        'Per-user runtime directory.',
        Derived('/run/user/$UID', lambda s: f'/run/user/{os.getuid()}'),
    ),
    Variable(
        'AGENTDEV_STATE_DIR',
        'Runtime state such as the clone marker.',
        Derived('$XDG_STATE_HOME/agentdev', lambda s: f'{s.get("XDG_STATE_HOME")}/agentdev'),
    ),
    Variable(
        'OPENCODE_CONFIG_DIR',
        'OpenCode configuration directory.',
        Derived('$XDG_CONFIG_HOME/opencode', lambda s: f'{s.get("XDG_CONFIG_HOME")}/opencode'),
    ),
    Variable(
        'AGENTDEV_SKIP_CLAUDE_PREAPPROVE',
        'Non-empty skips the Claude workspace pre-approval.',
    ),
    # Lifecycle and services.
    Variable('AGENTDEV_SKIP_XPRA', 'True leaves Xpra out.'),
    Variable('AGENTDEV_READY_TIMEOUT', 'Seconds `postStartCommand` waits for ready.', '900'),
    Variable('AGENTDEV_HEALTH_TIMEOUT', 'Seconds each health-report check may run.', '30'),
    # Firewall.
    Variable('ENABLE_FIREWALL', '`true` applies the egress firewall.', 'false'),
    Variable(
        'FIREWALL_ALLOWLIST',
        'Firewall allowlist; unset, a Dev Container reads its checkout copy when present.',
        '/etc/agentdev/firewall-allowlist.txt',
    ),
    Variable('AGENTDEV_XPRA_PORT', 'Xpra port.', '14500'),
    # Workspace and project.
    Variable('AGENTDEV_CATALOG_DIR', 'Catalog to register instead of the checkout.'),
    Variable('AGENTDEV_SKIP_PRE_COMMIT', 'Non-empty skips pre-commit hook registration.'),
    Variable(
        'AGENTDEV_VENV_ROOT',
        "Directory holding each checkout's uv environment, linked from its `.venv`.",
        '/uv/venvs',
    ),
    # Xpra.
    Variable('XPRA_HOST', 'Xpra bind address.', '127.0.0.1'),
    Variable('XPRA_VIDEO_ENCODERS', 'Xpra video encoders.', 'x264,vpx'),
    Variable(
        'XPRA_LOG_FILE',
        'Background Xpra log.',
        Derived('$PWD/.tmp/xpra.log', lambda s: f'{os.getcwd()}/.tmp/xpra.log'),
    ),
    Variable('XPRA_PASSWORD', 'Xpra password; none when empty.'),
    Variable('DISPLAY', 'X display Xpra serves.'),
)

BY_NAME: Mapping[str, Variable] = {variable.name: variable for variable in VARIABLES}


@dataclass
class Settings:
    """Environment values resolved against their defaults, with every error kept."""

    environ: Mapping[str, str] = field(default_factory=lambda: dict(os.environ))
    errors: list[str] = field(default_factory=list)

    @property
    def home(self) -> str:
        """Return the calling account's ``HOME``, as the scripts read it, else the runtime's."""
        return self.environ.get('HOME') or self.get('AGENTDEV_HOME')

    def raw(self, name: str) -> str:
        """Return the variable exactly as set, empty when unset."""
        self._known(name)
        return self.environ.get(name, '')

    def get(self, name: str) -> str:
        """Return the variable, or its default when unset or empty."""
        value = self.raw(name)
        if value:
            return value
        default = BY_NAME[name].default
        return default if isinstance(default, str) else default.compute(self)

    def path(self, name: str) -> Path:
        return Path(self.get(name))

    def boolean(self, name: str) -> bool:
        raw = self.get(name).strip().lower()
        if raw in TRUE_WORDS:
            return True
        if raw not in FALSE_WORDS:
            self.errors.append(
                f'{name} must be 1, true, yes, on, 0, false, no, off, or empty; '
                f'got {self.raw(name)!r}'
            )
        return False

    def get_default(self, name: str) -> str:
        """Return the default, ignoring the environment."""
        default = BY_NAME[name].default
        return default if isinstance(default, str) else default.compute(self)

    @staticmethod
    def _known(name: str) -> None:
        if name not in BY_NAME:
            raise KeyError(f'{name} is not a declared agentdev-runtime setting')


def _describe_default(default: Default) -> str:
    if isinstance(default, Derived):
        return default.text if ' ' in default.text else f'`{default.text}`'
    return f'`{default}`' if default else 'empty'


def markdown_table() -> str:
    """Render the settings as the Markdown table the package README carries."""
    rows = [
        '| Variable | Default | Meaning |',
        '| --- | --- | --- |',
    ]
    for variable in VARIABLES:
        rows.append(
            f'| `{variable.name}` | {_describe_default(variable.default)} '
            f'| {variable.description} |'
        )
    return '\n'.join(rows)
