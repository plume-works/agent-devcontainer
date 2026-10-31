"""Every environment value the runtime reads, parsed once, with one default per variable."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
import math
import os
from pathlib import Path

DEVCONTAINER = 'devcontainer'
DEPLOY = 'deploy'
PROFILES = (DEVCONTAINER, DEPLOY)
BOTH = PROFILES

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
    """One environment variable: its default, per profile where the profiles differ."""

    name: str
    description: str
    default: Default = ''
    deploy: Default | None = None
    profiles: tuple[str, ...] = BOTH

    def default_for(self, profile: str) -> Default:
        if profile == DEPLOY and self.deploy is not None:
            return self.deploy
        return self.default


def _home(s: Settings) -> str:
    user = s.get('AGENTDEV_USER')
    return '/root' if user == 'root' else f'/home/{user}'


def _workspace(s: Settings) -> str:
    return os.getcwd()


VARIABLES: tuple[Variable, ...] = (
    # Identity and profile.
    Variable(
        'AGENTDEV_RUNTIME_MODE',
        'Service profile, `devcontainer` or `deploy`; PID 1 requires it explicitly.',
        DEVCONTAINER,
    ),
    Variable('AGENTDEV_USER', 'Runtime account name.', 'root', deploy='agent'),
    Variable('AGENTDEV_UID', 'Runtime account UID the bootstrap creates or reuses.', '1000'),
    Variable('AGENTDEV_GID', 'Runtime account GID the bootstrap creates or reuses.', '1000'),
    Variable(
        'AGENTDEV_HOME',
        'Runtime account home.',
        Derived('`/root` for root, else `/home/$AGENTDEV_USER`', _home),
    ),
    Variable(
        'DEV_WORKSPACE_FOLDER',
        'Project checkout.',
        Derived('the working directory', _workspace),
        deploy='/workspaces/project',
    ),
    # Image-owned paths.
    Variable('AGENTDEV_RUN_DIR', 'Controller state, retry request, and socket.', '/run/agentdev'),
    Variable(
        'AGENTDEV_LIFECYCLE_DIR',
        'Per-container lifecycle markers.',
        '/var/lib/agentdev/lifecycle',
    ),
    Variable('AGENTDEV_HOOKS_ROOT', 'Derived-image lifecycle hook root.', '/etc/agentdev/hooks'),
    Variable(
        'AGENTDEV_SUPERVISOR_CONFIG',
        'supervisord configuration PID 1 runs.',
        '/etc/agentdev/supervisord.conf',
    ),
    Variable(
        'AGENTDEV_SUDOERS_FILE',
        'Sudoers entry the bootstrap writes for the runtime account.',
        '/etc/sudoers.d/agentdev-runtime',
    ),
    Variable('AGENTDEV_UV_DIR', 'uv cache, interpreter, and venv volume root.', '/uv'),
    Variable(
        'AGENTDEV_GH_STACK_DIR',
        'Image copy of the gh-stack extension.',
        '/usr/local/lib/agentdev/gh-stack',
    ),
    Variable(
        'AGENTDEV_REQUIRE_MOUNTS',
        '`1` makes the bootstrap refuse unmounted instance storage.',
        '1',
        profiles=(DEPLOY,),
    ),
    # Agent state.
    Variable(
        'AGENTDEV_AGENTS_AUTH_DIR',
        'Shared agent credential directory.',
        '/root/.agents-auth',
        deploy='/var/lib/agentdev/auth',
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
        Derived('/run/user/$AGENTDEV_UID', lambda s: f'/run/user/{s.get("AGENTDEV_UID")}'),
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
    # Supervisor budgets and switches.
    Variable('AGENTDEV_RECOVERY_ATTEMPTS', 'Restarts per service before latching failed.', '3'),
    Variable('AGENTDEV_RECOVERY_BACKOFF', 'Seconds before the first restart.', '1'),
    Variable('AGENTDEV_HEALTHY_RESET', 'Healthy seconds that refill the recovery budget.', '60'),
    Variable('AGENTDEV_SERVICE_START_TIMEOUT', 'Seconds a service has to become ready.', '60'),
    Variable('AGENTDEV_BOOTSTRAP_TIMEOUT', 'Seconds the root bootstrap may run.', '1800'),
    Variable('AGENTDEV_PREPARE_TIMEOUT', 'Seconds the deploy `prepare` phase may run.', '1800'),
    Variable('AGENTDEV_HEALTH_INTERVAL', 'Seconds between health probes.', '2'),
    Variable('AGENTDEV_PROBE_FAILURES', 'Consecutive failed probes that count as down.', '2'),
    Variable('AGENTDEV_STOP_TIMEOUT', "Seconds supervisord waits for a program's stop.", '30'),
    Variable(
        'AGENTDEV_HEALTH_COMMAND',
        'Probe command the controller runs per service.',
        'agentdev-runtime health',
    ),
    Variable(
        'AGENTDEV_BOOTSTRAP_COMMAND',
        'Root bootstrap PID 1 runs before supervisord.',
        'agentdev-runtime bootstrap',
    ),
    Variable('AGENTDEV_STRICT_STARTUP', 'True makes an optional-service failure fatal.'),
    Variable('AGENTDEV_SKIP_XPRA', 'True leaves Xpra out.'),
    Variable(
        'AGENTDEV_OPENCODE_WEB',
        'True serves OpenCode Web in a Dev Container.',
        profiles=(DEVCONTAINER,),
    ),
    Variable(
        'AGENTDEV_CLAUDE_RC_MODE', 'Remote Control mode, `session` or `server`; empty is off.'
    ),
    Variable('AGENTDEV_CLAUDE_RC_SPAWN', 'Server-mode spawn, `worktree` or `same-dir`.'),
    Variable('AGENTDEV_STARTUP_ID', 'Set by PID 1 for each start; read by its children.'),
    Variable('AGENTDEV_RETRY_ID', 'Set by PID 1 for each retry; read by its children.'),
    Variable('AGENTDEV_READY_TIMEOUT', 'Seconds `postStartCommand` waits for ready.', '900'),
    Variable('AGENTDEV_HEALTH_TIMEOUT', 'Seconds each health-report check may run.', '30'),
    # Firewall.
    Variable('ENABLE_FIREWALL', '`true` applies the egress firewall.', 'false'),
    Variable(
        'FIREWALL_ALLOWLIST',
        'Firewall allowlist; unset, a Dev Container reads its checkout copy when present.',
        '/etc/agentdev/firewall-allowlist.txt',
    ),
    Variable(
        'AGENTDEV_TRUSTED_PROXY_CIDRS',
        'CIDRs allowed to reach the web ports through the firewall.',
        profiles=(DEPLOY,),
    ),
    Variable('AGENTDEV_OPENCODE_PORT', 'OpenCode Web port.', '4096'),
    Variable('AGENTDEV_XPRA_PORT', 'Xpra port.', '14500'),
    # Docker.
    Variable('AGENTDEV_DOCKER_DATA_DIR', 'Nested engine data root.', '/var/lib/docker'),
    Variable('AGENTDEV_DOCKER_SOCKET', 'Nested engine socket.', '/var/run/docker.sock'),
    Variable('AGENTDEV_DOCKER_CONFIG', 'Nested engine configuration.', '/etc/docker/daemon.json'),
    Variable('AGENTDEV_DOCKER_EXEC_ROOT', 'Nested engine exec root.', '/var/run/docker'),
    Variable('AGENTDEV_DOCKER_PIDFILE', 'Nested engine PID file.', '/var/run/docker.pid'),
    Variable(
        'AGENTDEV_PROC_STATUS',
        'Process status file the privilege preflight reads.',
        '/proc/self/status',
    ),
    # CBM.
    Variable('CBM_CACHE_DIR', 'CBM index cache; required by every CBM command.'),
    Variable(
        'CBM_INSTALL_DIR',
        'Directory of the user-owned CBM binary.',
        Derived('$HOME/.local/bin', lambda s: f'{s.home}/.local/bin'),
    ),
    Variable('CBM_LOG_LEVEL', 'CBM log level during install.', 'debug'),
    Variable('AGENTDEV_CBM_BIN', 'CBM executable.', 'codebase-memory-mcp'),
    Variable(
        'AGENTDEV_CBM_STATE_DIR',
        'CBM daemon generation and log directory.',
        Derived(
            '${XDG_RUNTIME_DIR:-/tmp}/agentdev-cbm-<euid>',
            lambda s: f'{s.get("XDG_RUNTIME_DIR") or "/tmp"}/agentdev-cbm-{os.geteuid()}',
        ),
    ),
    Variable('AGENTDEV_CBM_START_TIMEOUT', 'Seconds the CBM daemon has to answer.', '60'),
    Variable('AGENTDEV_CBM_STOP_TIMEOUT', 'Seconds the CBM daemon has to stop.', '30'),
    Variable('AGENTDEV_CBM_POLL_INTERVAL', 'Seconds between CBM daemon polls.', '2'),
    Variable(
        'AGENTDEV_CBM_UNRESPONSIVE_LIMIT',
        'Failed CBM polls that count as unresponsive.',
        '3',
    ),
    # Workspace and project.
    Variable(
        'AGENTDEV_REPOSITORY_URL', 'Repository the deploy profile clones.', profiles=(DEPLOY,)
    ),
    Variable('AGENTDEV_REPOSITORY_REF', 'Ref the deploy profile checks out.', profiles=(DEPLOY,)),
    Variable('AGENTDEV_CATALOG_DIR', 'Catalog to register instead of the checkout.'),
    Variable('AGENTDEV_SKIP_PRE_COMMIT', 'Non-empty skips pre-commit hook registration.'),
    Variable(
        'AGENTDEV_KEYRING_ENV_FILE',
        'Keyring-session environment the credential helper reads.',
        Derived(
            '$DEV_WORKSPACE_FOLDER/.tmp/keyring-session.env',
            lambda s: f'{s.get("DEV_WORKSPACE_FOLDER")}/.tmp/keyring-session.env',
        ),
    ),
    Variable('UV_PROJECT_ENVIRONMENT', "The project's uv environment."),
    # Keyring.
    Variable('DBUS_SESSION_BUS_ADDRESS', 'Session bus address.'),
    # OpenCode and Coder.
    Variable('OPENCODE_SERVER_USERNAME', 'OpenCode Web user.', 'opencode'),
    Variable('OPENCODE_SERVER_PASSWORD', 'OpenCode Web password; generated when empty.'),
    Variable('VSCODE_PROXY_URI', 'Coder proxy URL template for the OpenCode link.'),
    Variable('CODER_WORKSPACE_NAME', 'Coder workspace name for the Remote Control session.'),
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
    """Environment values resolved against the profile's defaults, with every error kept."""

    environ: Mapping[str, str] = field(default_factory=lambda: dict(os.environ))
    errors: list[str] = field(default_factory=list)

    @property
    def profile(self) -> str:
        mode = self.environ.get('AGENTDEV_RUNTIME_MODE', '')
        return mode if mode in PROFILES else DEVCONTAINER

    @property
    def home(self) -> str:
        """Return the calling account's ``HOME``, as the scripts read it, else the runtime's."""
        return self.environ.get('HOME') or self.get('AGENTDEV_HOME')

    def raw(self, name: str) -> str:
        """Return the variable exactly as set, empty when unset."""
        self._known(name)
        return self.environ.get(name, '')

    def get(self, name: str) -> str:
        """Return the variable, or its profile default when unset or empty."""
        value = self.raw(name)
        if value:
            return value
        default = BY_NAME[name].default_for(self.profile)
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

    def positive(self, name: str) -> float:
        default = float(self.get_default(name))
        raw = self.raw(name)
        if not raw:
            return default
        try:
            value = float(raw)
        except ValueError:
            value = math.nan
        if not (math.isfinite(value) and value > 0):
            self.errors.append(f'{name} must be a positive number; got {raw!r}')
            return default
        return value

    def count(self, name: str) -> int:
        default = int(self.get_default(name))
        raw = self.raw(name)
        if not raw:
            return default
        if not raw.strip().isdigit() or int(raw) <= 0:
            self.errors.append(f'{name} must be a positive integer; got {raw!r}')
            return default
        return int(raw)

    def required(self, name: str, options: tuple[str, ...]) -> str:
        raw = self.raw(name)
        if raw not in options:
            self.errors.append(f'{name} must be {" or ".join(options)}; got {raw!r}')
            return ''
        return raw

    def choice(self, name: str, options: tuple[str, ...]) -> str:
        raw = self.raw(name)
        if raw and raw not in options:
            self.errors.append(f'{name} must be {", ".join(options)}, or empty; got {raw!r}')
            return ''
        return raw

    def get_default(self, name: str) -> str:
        """Return the profile default, ignoring the environment."""
        default = BY_NAME[name].default_for(self.profile)
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
        '| Variable | Default | Deploy default | Profiles | Meaning |',
        '| --- | --- | --- | --- | --- |',
    ]
    for variable in VARIABLES:
        deploy = '' if variable.deploy is None else _describe_default(variable.deploy)
        rows.append(
            f'| `{variable.name}` | {_describe_default(variable.default)} | {deploy} '
            f'| {", ".join(variable.profiles)} | {variable.description} |'
        )
    return '\n'.join(rows)
