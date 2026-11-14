# `.claude/` — this repository's own Claude Code configuration

The agent catalog does not live here; it ships as the `agentdev` plugin under
[`.agents/plugins/agentdev/`](../.agents/plugins/agentdev/README.md). What remains in this directory is the
configuration this repository keeps for itself.

| Path            | Purpose                                                                                                             |
| --------------- | ------------------------------------------------------------------------------------------------------------------- |
| `settings.json` | Permissions, additional directories, enabled third-party plugins, and the `SessionStart` hook.                      |
| `startup.py`    | Cloud session setup and resume: see [ADR-0071](../docs/knowledge/data/adr/0071-cloud-sessions-work-on-the-host.md). |

`startup.py` is standard-library Python, because the session host has no project environment
until it runs. It resolves the repository root from its own location, so it runs from any
directory. The cloud environment runs `startup.py` as its setup script; the `SessionStart` hook in
`settings.json` runs `startup.py resume`. Its logs are `/var/log/dockerd.log` and
`/var/log/agent-proxy-relay.log`.

`settings.json` must be strict JSON: no comments and no trailing commas. Claude
Code rejects the file outright if it does not parse, which silently drops every
permission and plugin setting with it.

The devcontainer lifecycle installs the image-staged `agentdev` plugin after persistent
volumes mount, then re-registers this checkout's marketplace during post-start so catalog
development uses the workspace copy. `settings.json` does not need to declare that local
installation.

`*.local.json` is gitignored, so `settings.local.json` can hold machine-specific
permissions without touching the shared configuration.

For editing and validating the catalog itself, see
[The agent catalog](../README.md#the-agent-catalog).
