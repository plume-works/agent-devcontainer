# agentdev-runtime

The `agentdev-runtime` command line runs inside the `agentdev-devcontainer`
image: the root bootstrap that `agentdev-bootstrap.service` runs, the health
probes that read systemd's unit states, and the Dev Container lifecycle
commands. systemd supervises the services. The image installs it as a uv tool
under `/opt/uv-tools` with the entry point on `/usr/local/bin`.

Run the tests from the repository root with
`uv run pytest py_packages/agentdev_runtime`.

## Settings

`agentdev_runtime.settings` parses every environment value the runtime reads,
with one default per variable. `agentdev-runtime settings` prints this table
from the code.

| Variable                          | Default                                       | Meaning                                                                             |
| --------------------------------- | --------------------------------------------- | ----------------------------------------------------------------------------------- |
| `AGENTDEV_USER`                   | `root`                                        | Runtime account name.                                                               |
| `AGENTDEV_HOME`                   | `/root` for root, else `/home/$AGENTDEV_USER` | Runtime account home.                                                               |
| `DEV_WORKSPACE_FOLDER`            | the working directory                         | Project checkout.                                                                   |
| `AGENTDEV_LIFECYCLE_DIR`          | `/var/lib/agentdev/lifecycle`                 | Per-container lifecycle markers.                                                    |
| `AGENTDEV_HOOKS_ROOT`             | `/etc/agentdev/hooks`                         | Derived-image lifecycle hook root.                                                  |
| `AGENTDEV_EXTRA_CA_CERTS`         | `/etc/agentdev/extra-ca.crt`                  | PEM bundle the bootstrap adds to the system trust store; absent or empty adds none. |
| `AGENTDEV_AGENTS_AUTH_DIR`        | `/root/.agents-auth`                          | Shared agent credential directory.                                                  |
| `AGENTDEV_AUTH_LOCK_TIMEOUT`      | `60`                                          | Seconds the bootstrap waits for the shared-auth lock.                               |
| `AGENTDEV_CONFIG_LOCK_TIMEOUT`    | `1800`                                        | Seconds agent-state setup waits for the configuration lock.                         |
| `AGENTDEV_CLAUDE_DIR`             | `$HOME/.claude`                               | Claude configuration directory.                                                     |
| `AGENTDEV_CLAUDE_JSON`            | `$HOME/.claude.json`                          | Claude state file.                                                                  |
| `AGENTDEV_CLAUDE_STATE_PATH`      | `$HOME/.claude.json`                          | Claude state file the workspace pre-approval edits.                                 |
| `CLAUDE_SECURESTORAGE_CONFIG_DIR` | `$AGENTDEV_CLAUDE_DIR`                        | Directory holding Claude `.credentials.json`.                                       |
| `CLAUDE_CONFIG_DIR`               | `$HOME/.claude`                               | Claude Code's own configuration directory.                                          |
| `XDG_CONFIG_HOME`                 | `$HOME/.config`                               | XDG configuration root.                                                             |
| `XDG_DATA_HOME`                   | `$HOME/.local/share`                          | XDG data root.                                                                      |
| `XDG_STATE_HOME`                  | `$HOME/.local/state`                          | XDG state root.                                                                     |
| `XDG_RUNTIME_DIR`                 | `/run/user/$UID`                              | Per-user runtime directory.                                                         |
| `AGENTDEV_STATE_DIR`              | `$XDG_STATE_HOME/agentdev`                    | Runtime state such as the clone marker.                                             |
| `OPENCODE_CONFIG_DIR`             | `$XDG_CONFIG_HOME/opencode`                   | OpenCode configuration directory.                                                   |
| `AGENTDEV_SKIP_CLAUDE_PREAPPROVE` | empty                                         | Non-empty skips the Claude workspace pre-approval.                                  |
| `AGENTDEV_SKIP_XPRA`              | empty                                         | True leaves Xpra out.                                                               |
| `AGENTDEV_READY_TIMEOUT`          | `900`                                         | Seconds `postStartCommand` waits for ready.                                         |
| `AGENTDEV_HEALTH_TIMEOUT`         | `30`                                          | Seconds each health-report check may run.                                           |
| `ENABLE_FIREWALL`                 | `false`                                       | `true` applies the egress firewall.                                                 |
| `FIREWALL_ALLOWLIST`              | `/etc/agentdev/firewall-allowlist.txt`        | Firewall allowlist; unset, a Dev Container reads its checkout copy when present.    |
| `AGENTDEV_XPRA_PORT`              | `14500`                                       | Xpra port.                                                                          |
| `AGENTDEV_CATALOG_DIR`            | empty                                         | Catalog to register instead of the checkout.                                        |
| `AGENTDEV_SKIP_PRE_COMMIT`        | empty                                         | Non-empty skips pre-commit hook registration.                                       |
| `AGENTDEV_VENV_ROOT`              | `/uv/venvs`                                   | Directory holding each checkout's uv environment, linked from its `.venv`.          |
| `XPRA_HOST`                       | `127.0.0.1`                                   | Xpra bind address.                                                                  |
| `XPRA_VIDEO_ENCODERS`             | `x264,vpx`                                    | Xpra video encoders.                                                                |
| `XPRA_LOG_FILE`                   | `$PWD/.tmp/xpra.log`                          | Background Xpra log.                                                                |
| `XPRA_PASSWORD`                   | empty                                         | Xpra password; none when empty.                                                     |
| `DISPLAY`                         | empty                                         | X display Xpra serves.                                                              |
