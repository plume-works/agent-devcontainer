# `.claude/` — this repository's own Claude Code configuration

The agent catalog does not live here; it ships as the `agentdev` plugin under
[`.agents/plugins/agentdev/`](../.agents/plugins/agentdev/README.md). What remains in this directory is the
configuration this repository keeps for itself.

| Path            | Purpose                                                               |
| --------------- | --------------------------------------------------------------------- |
| `settings.json` | Permissions, additional directories, and enabled third-party plugins. |
| `startup.sh`    | Cloud session startup: registers the marketplace, installs `agentdev`, starts Docker, pre-pulls the pinned image. |

`startup.sh` resolves the repository root from its own location, so it runs from any directory. It
fails fast if the Docker daemon does not answer within 30 seconds; the daemon log is
`/var/log/dockerd.log`. The image it pulls is the digest in `devcontainer-compose-pins.yml`, so the
script stays in step with Renovate's pin bumps without edits.

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
