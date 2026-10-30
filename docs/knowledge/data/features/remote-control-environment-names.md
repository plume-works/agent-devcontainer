---
type: feature
stage: accepted
description: The dev container's hostname names where it was launched from — a Coder workspace, VS Code on a machine, or the devcontainer CLI on a machine — so Claude Remote Control environments are told apart in the Claude apps.
generated:
  by: claude-code/opus-5
  at: 2026-10-29T12:00:00Z
sources:
- resource: .devcontainer/docker-compose.yml
- resource: .devcontainer/devcontainer-init.sh
- resource: https://code.claude.com/docs/en/remote-control
---

# Remote Control environment names

## Purpose

Claude Remote Control registers its environment under the container hostname,
and no Claude option overrides that name. A dev container without a set hostname
gets its Docker container ID, so every workspace appears in Claude Desktop as a
string like `08564f998d42` and several Coder workspaces cannot be told apart.

## Behaviour

**The launcher names the container.** The initialize command derives the
hostname before Compose creates the container:

- **Coder** — `coder-<workspace name>`.
- **VS Code** — `vscode-<host>-<checkout>`, where `<host>` is the launching
  machine's short hostname and `<checkout>` the checkout directory's name.
- **The devcontainer CLI** — `cli-<host>-<checkout>`.

**The name is a valid hostname.** It is lowercased, other characters become
hyphens, and it is at most 63 characters.

**Session names are unchanged.** Coder sessions keep the workspace name the
Remote Control start script already passes; only the environment name changes.

## Edge cases

- **Coder also sets VS Code variables.** The Coder name wins.
- **The same checkout opened twice on one machine by the same launcher.** Both
  containers get the same name.
- **Compose run directly, without the initialize command.** The container is
  named `agentdev`.
- **An existing container.** It keeps its old name until it is recreated.

## Open questions

- Whether `devcontainer up` run from VS Code's integrated terminal reads as VS
  Code or as the CLI.
