# agentdev-runtime

The `agentdev-runtime` command line runs the `agentdev-devcontainer` and
`agentdev-deploy` images: PID 1 and its supervisor, the health probes, every
supervised service, and the Dev Container lifecycle commands. Both images
install it as a uv tool under `/opt/uv-tools` with the entry point on
`/usr/local/bin`; `agentdev-base` never carries it.

Run the tests from the repository root with
`uv run pytest py_packages/agentdev_runtime`.

## Settings

`agentdev_runtime.settings` parses every environment value the runtime reads,
with one default per variable. Where the two profiles disagree, the deploy
column names the deploy profile's default. `agentdev-runtime settings` prints
this table from the code.

| Variable                          | Default                                          | Deploy default           | Profiles             | Meaning                                                                    |
| --------------------------------- | ------------------------------------------------ | ------------------------ | -------------------- | -------------------------------------------------------------------------- |
| `AGENTDEV_RUNTIME_MODE`           | `devcontainer`                                   |                          | devcontainer, deploy | Service profile, `devcontainer` or `deploy`; PID 1 requires it explicitly. |
| `AGENTDEV_USER`                   | `root`                                           | `agent`                  | devcontainer, deploy | Runtime account name.                                                      |
| `AGENTDEV_UID`                    | `1000`                                           |                          | devcontainer, deploy | Runtime account UID the bootstrap creates or reuses.                       |
| `AGENTDEV_GID`                    | `1000`                                           |                          | devcontainer, deploy | Runtime account GID the bootstrap creates or reuses.                       |
| `AGENTDEV_HOME`                   | `/root` for root, else `/home/$AGENTDEV_USER`    |                          | devcontainer, deploy | Runtime account home.                                                      |
| `DEV_WORKSPACE_FOLDER`            | the working directory                            | `/workspaces/project`    | devcontainer, deploy | Project checkout.                                                          |
| `AGENTDEV_RUN_DIR`                | `/run/agentdev`                                  |                          | devcontainer, deploy | Controller state, retry request, and socket.                               |
| `AGENTDEV_LIFECYCLE_DIR`          | `/var/lib/agentdev/lifecycle`                    |                          | devcontainer, deploy | Per-container lifecycle markers.                                           |
| `AGENTDEV_HOOKS_ROOT`             | `/etc/agentdev/hooks`                            |                          | devcontainer, deploy | Derived-image lifecycle hook root.                                         |
| `AGENTDEV_SUPERVISOR_CONFIG`      | `/etc/agentdev/supervisord.conf`                 |                          | devcontainer, deploy | supervisord configuration PID 1 runs.                                      |
| `AGENTDEV_SUDOERS_FILE`           | `/etc/sudoers.d/agentdev-runtime`                |                          | devcontainer, deploy | Sudoers entry the bootstrap writes for the runtime account.                |
| `AGENTDEV_RUNTIME_ROOT`           | `/opt/agentdev-runtime`                          |                          | devcontainer, deploy | Image-owned runtime script tree.                                           |
| `AGENTDEV_UV_DIR`                 | `/uv`                                            |                          | devcontainer, deploy | uv cache, interpreter, and venv volume root.                               |
| `AGENTDEV_GH_STACK_DIR`           | `/usr/local/lib/agentdev/gh-stack`               |                          | devcontainer, deploy | Image copy of the gh-stack extension.                                      |
| `AGENTDEV_REQUIRE_MOUNTS`         | `1`                                              |                          | deploy               | `1` makes the bootstrap refuse unmounted instance storage.                 |
| `AGENTDEV_AGENTS_AUTH_DIR`        | `/root/.agents-auth`                             | `/var/lib/agentdev/auth` | devcontainer, deploy | Shared agent credential directory.                                         |
| `AGENTDEV_AUTH_LOCK_TIMEOUT`      | `60`                                             |                          | devcontainer, deploy | Seconds the bootstrap waits for the shared-auth lock.                      |
| `AGENTDEV_CONFIG_LOCK_TIMEOUT`    | `1800`                                           |                          | devcontainer, deploy | Seconds agent-state setup waits for the configuration lock.                |
| `AGENTDEV_CLAUDE_DIR`             | `$AGENTDEV_HOME/.claude`                         |                          | devcontainer, deploy | Claude configuration directory.                                            |
| `AGENTDEV_CLAUDE_JSON`            | `$AGENTDEV_HOME/.claude.json`                    |                          | devcontainer, deploy | Claude state file.                                                         |
| `AGENTDEV_CLAUDE_STATE_PATH`      | `$AGENTDEV_HOME/.claude.json`                    |                          | devcontainer, deploy | Claude state file the workspace pre-approval edits.                        |
| `CLAUDE_SECURESTORAGE_CONFIG_DIR` | `$AGENTDEV_CLAUDE_DIR`                           |                          | devcontainer, deploy | Directory holding Claude `.credentials.json`.                              |
| `CLAUDE_CONFIG_DIR`               | `$AGENTDEV_HOME/.claude`                         |                          | devcontainer, deploy | Claude Code's own configuration directory.                                 |
| `CODEX_HOME`                      | `$AGENTDEV_HOME/.codex`                          |                          | devcontainer, deploy | Codex home.                                                                |
| `XDG_CONFIG_HOME`                 | `$AGENTDEV_HOME/.config`                         |                          | devcontainer, deploy | XDG configuration root.                                                    |
| `XDG_DATA_HOME`                   | `$AGENTDEV_HOME/.local/share`                    |                          | devcontainer, deploy | XDG data root.                                                             |
| `XDG_STATE_HOME`                  | `$AGENTDEV_HOME/.local/state`                    |                          | devcontainer, deploy | XDG state root.                                                            |
| `XDG_RUNTIME_DIR`                 | `/run/user/$AGENTDEV_UID`                        |                          | devcontainer, deploy | Per-user runtime directory.                                                |
| `AGENTDEV_STATE_DIR`              | `$XDG_STATE_HOME/agentdev`                       |                          | devcontainer, deploy | Runtime state such as the clone marker.                                    |
| `OPENCODE_CONFIG_DIR`             | `$XDG_CONFIG_HOME/opencode`                      |                          | devcontainer, deploy | OpenCode configuration directory.                                          |
| `AGENTDEV_SKIP_CLAUDE_PREAPPROVE` | empty                                            |                          | devcontainer, deploy | Non-empty skips the Claude workspace pre-approval.                         |
| `AGENTDEV_RECOVERY_ATTEMPTS`      | `3`                                              |                          | devcontainer, deploy | Restarts per service before latching failed.                               |
| `AGENTDEV_RECOVERY_BACKOFF`       | `1`                                              |                          | devcontainer, deploy | Seconds before the first restart.                                          |
| `AGENTDEV_HEALTHY_RESET`          | `60`                                             |                          | devcontainer, deploy | Healthy seconds that refill the recovery budget.                           |
| `AGENTDEV_SERVICE_START_TIMEOUT`  | `60`                                             |                          | devcontainer, deploy | Seconds a service has to become ready.                                     |
| `AGENTDEV_BOOTSTRAP_TIMEOUT`      | `1800`                                           |                          | devcontainer, deploy | Seconds the root bootstrap may run.                                        |
| `AGENTDEV_PREPARE_TIMEOUT`        | `1800`                                           |                          | devcontainer, deploy | Seconds the deploy `prepare` phase may run.                                |
| `AGENTDEV_HEALTH_INTERVAL`        | `2`                                              |                          | devcontainer, deploy | Seconds between health probes.                                             |
| `AGENTDEV_PROBE_FAILURES`         | `2`                                              |                          | devcontainer, deploy | Consecutive failed probes that count as down.                              |
| `AGENTDEV_STOP_TIMEOUT`           | `30`                                             |                          | devcontainer, deploy | Seconds supervisord waits for a program's stop.                            |
| `AGENTDEV_HEALTH_COMMAND`         | `agentdev-runtime health`                        |                          | devcontainer, deploy | Probe command the controller runs per service.                             |
| `AGENTDEV_BOOTSTRAP_COMMAND`      | `agentdev-runtime bootstrap`                     |                          | devcontainer, deploy | Root bootstrap PID 1 runs before supervisord.                              |
| `AGENTDEV_STRICT_STARTUP`         | empty                                            |                          | devcontainer, deploy | True makes an optional-service failure fatal.                              |
| `AGENTDEV_SKIP_XPRA`              | empty                                            |                          | devcontainer, deploy | True leaves Xpra out.                                                      |
| `AGENTDEV_OPENCODE_WEB`           | empty                                            |                          | devcontainer         | True serves OpenCode Web in a Dev Container.                               |
| `AGENTDEV_CLAUDE_RC_MODE`         | empty                                            |                          | devcontainer, deploy | Remote Control mode, `session` or `server`; empty is off.                  |
| `AGENTDEV_CLAUDE_RC_SPAWN`        | empty                                            |                          | devcontainer, deploy | Server-mode spawn, `worktree` or `same-dir`.                               |
| `AGENTDEV_STARTUP_ID`             | empty                                            |                          | devcontainer, deploy | Set by PID 1 for each start; read by its children.                         |
| `AGENTDEV_RETRY_ID`               | empty                                            |                          | devcontainer, deploy | Set by PID 1 for each retry; read by its children.                         |
| `AGENTDEV_READY_TIMEOUT`          | `900`                                            |                          | devcontainer, deploy | Seconds `postStartCommand` waits for ready.                                |
| `AGENTDEV_HEALTH_TIMEOUT`         | `30`                                             |                          | devcontainer, deploy | Seconds each health-report check may run.                                  |
| `ENABLE_FIREWALL`                 | `false`                                          |                          | devcontainer, deploy | `true` applies the egress firewall.                                        |
| `FIREWALL_ALLOWLIST`              | `/etc/agentdev/firewall-allowlist.txt`           |                          | devcontainer, deploy | Firewall allowlist file.                                                   |
| `AGENTDEV_INIT_FIREWALL`          | `/usr/local/bin/init-firewall.sh`                |                          | devcontainer, deploy | Firewall program the supervised wrapper runs.                              |
| `AGENTDEV_TRUSTED_PROXY_CIDRS`    | empty                                            |                          | deploy               | CIDRs allowed to reach the web ports through the firewall.                 |
| `AGENTDEV_OPENCODE_PORT`          | `4096`                                           |                          | devcontainer, deploy | OpenCode Web port.                                                         |
| `AGENTDEV_XPRA_PORT`              | `14500`                                          |                          | devcontainer, deploy | Xpra port.                                                                 |
| `AGENTDEV_DOCKER_DATA_DIR`        | `/var/lib/docker`                                |                          | devcontainer, deploy | Nested engine data root.                                                   |
| `AGENTDEV_DOCKER_SOCKET`          | `/var/run/docker.sock`                           |                          | devcontainer, deploy | Nested engine socket.                                                      |
| `AGENTDEV_DOCKER_CONFIG`          | `/etc/docker/daemon.json`                        |                          | devcontainer, deploy | Nested engine configuration.                                               |
| `AGENTDEV_DOCKER_EXEC_ROOT`       | `/var/run/docker`                                |                          | devcontainer, deploy | Nested engine exec root.                                                   |
| `AGENTDEV_DOCKER_PIDFILE`         | `/var/run/docker.pid`                            |                          | devcontainer, deploy | Nested engine PID file.                                                    |
| `AGENTDEV_PROC_STATUS`            | `/proc/self/status`                              |                          | devcontainer, deploy | Process status file the privilege preflight reads.                         |
| `CBM_CACHE_DIR`                   | empty                                            |                          | devcontainer, deploy | CBM index cache; required by every CBM command.                            |
| `CBM_INSTALL_DIR`                 | `$AGENTDEV_HOME/.local/bin`                      |                          | devcontainer, deploy | Directory of the user-owned CBM binary.                                    |
| `CBM_LOG_LEVEL`                   | `debug`                                          |                          | devcontainer, deploy | CBM log level during install.                                              |
| `AGENTDEV_CBM_BIN`                | `codebase-memory-mcp`                            |                          | devcontainer, deploy | CBM executable.                                                            |
| `AGENTDEV_CBM_STATE_DIR`          | `${XDG_RUNTIME_DIR:-/tmp}/agentdev-cbm-<euid>`   |                          | devcontainer, deploy | CBM daemon generation and log directory.                                   |
| `AGENTDEV_CBM_START_TIMEOUT`      | `60`                                             |                          | devcontainer, deploy | Seconds the CBM daemon has to answer.                                      |
| `AGENTDEV_CBM_STOP_TIMEOUT`       | `30`                                             |                          | devcontainer, deploy | Seconds the CBM daemon has to stop.                                        |
| `AGENTDEV_CBM_POLL_INTERVAL`      | `2`                                              |                          | devcontainer, deploy | Seconds between CBM daemon polls.                                          |
| `AGENTDEV_CBM_UNRESPONSIVE_LIMIT` | `3`                                              |                          | devcontainer, deploy | Failed CBM polls that count as unresponsive.                               |
| `AGENTDEV_REPOSITORY_URL`         | empty                                            |                          | deploy               | Repository the deploy profile clones.                                      |
| `AGENTDEV_REPOSITORY_REF`         | empty                                            |                          | deploy               | Ref the deploy profile checks out.                                         |
| `AGENTDEV_CATALOG_DIR`            | empty                                            |                          | devcontainer, deploy | Catalog to register instead of the checkout.                               |
| `AGENTDEV_SKIP_PRE_COMMIT`        | empty                                            |                          | devcontainer, deploy | Non-empty skips pre-commit hook registration.                              |
| `AGENTDEV_KEYRING_ENV_FILE`       | `$DEV_WORKSPACE_FOLDER/.tmp/keyring-session.env` |                          | devcontainer, deploy | Keyring-session environment the credential helper reads.                   |
| `UV_PROJECT_ENVIRONMENT`          | empty                                            |                          | devcontainer, deploy | The project's uv environment.                                              |
| `DBUS_SESSION_BUS_ADDRESS`        | empty                                            |                          | devcontainer, deploy | Session bus address.                                                       |
| `OPENCODE_SERVER_USERNAME`        | `opencode`                                       |                          | devcontainer, deploy | OpenCode Web user.                                                         |
| `OPENCODE_SERVER_PASSWORD`        | empty                                            |                          | devcontainer, deploy | OpenCode Web password; generated when empty.                               |
| `VSCODE_PROXY_URI`                | empty                                            |                          | devcontainer, deploy | Coder proxy URL template for the OpenCode link.                            |
| `CODER_WORKSPACE_NAME`            | empty                                            |                          | devcontainer, deploy | Coder workspace name for the Remote Control session.                       |
| `XPRA_HOST`                       | `127.0.0.1`                                      |                          | devcontainer, deploy | Xpra bind address.                                                         |
| `XPRA_VIDEO_ENCODERS`             | `x264,vpx`                                       |                          | devcontainer, deploy | Xpra video encoders.                                                       |
| `XPRA_LOG_FILE`                   | `$PWD/.tmp/xpra.log`                             |                          | devcontainer, deploy | Background Xpra log.                                                       |
| `XPRA_PASSWORD`                   | empty                                            |                          | devcontainer, deploy | Xpra password; none when empty.                                            |
| `DISPLAY`                         | empty                                            |                          | devcontainer, deploy | X display Xpra serves.                                                     |
