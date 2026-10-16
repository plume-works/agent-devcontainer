---
type: feature
stage: implemented
description: Agents sign in inside the devcontainer instead of from seeded Coder-secret credentials, Remote Control autostarts only on a live claude.ai login, and Claude workspace pre-approval runs in every container with an opt-out.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-16T12:00:00Z
sources:
- resource: docs/knowledge/data/plans/20261009-remove-coder-agent-auth-seeding.md
- resource: .devcontainer/scripts/claude-remote-control-start.sh
- resource: .devcontainer/scripts/preapprove-claude-workspace.sh
---

# Agent sign-in without credential seeding

## Purpose

Seeding one Claude credential snapshot from a Coder secret into several
workspaces left all but the first with an expired login, because claude.ai
rotates the refresh token on refresh. Codex seeding shared the mechanism.

## Behaviour

**No seeding.** The `AGENTDEV_CLAUDE_JSON` and `AGENTDEV_CODEX_JSON` Coder
secrets and everything that consumed them are gone. A `/login` inside any
container persists on the shared `agentdev-agents-auth` volume.

**Remote Control needs a live login.** Autostart runs only when
`claude auth status` reports a claude.ai login, not merely a credentials file.

**Workspace pre-approval everywhere.** `preapprove-claude-workspace.sh` runs in
every container from `postCreateCommand`, unless
`AGENTDEV_SKIP_CLAUDE_PREAPPROVE` is set.

The contracts are [Claude Remote Control](../spec/claude-remote-control.md) and
[Devcontainer Git credentials](../spec/devcontainer-git-credentials.md).

## Edge cases

- **A rejected refresh** leaves a credentials file with emptied tokens;
  autostart does not start on it.
- **A setup-token login** cannot run Remote Control, so autostart skips it.
- **Headless CI** sets `AGENTDEV_SKIP_CLAUDE_PREAPPROVE` so project MCP servers
  are not enabled there.

## Open questions

None — the design is settled.

## References

- Plan: [Remove Coder agent-auth
  seeding](../plans/20261009-remove-coder-agent-auth-seeding.md)
