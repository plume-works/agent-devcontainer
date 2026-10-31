---
type: task
created: 2026-10-01
stage: done
completed: 2026-10-01
priority: medium
description: Remove the agentdev plugin's SessionStart hook, which never brought up a working devcontainer, and release the catalog as 4.0.0.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T16:40:07Z
sources:
- resource: .agents/plugins/agentdev/hooks/hooks.json
- resource: .agents/plugins/agentdev/hooks/session-start.sh
- resource: .agents/plugins/agentdev/README.md
- resource: .claude-plugin/marketplace.json
---

# Remove the agentdev SessionStart hook

The agentdev plugin wires one `SessionStart` hook: `session-start.sh` exits
unless `CLAUDE_CODE_REMOTE=true`, then installs bun and `@devcontainers/cli` and
runs `devcontainer up`. It is a no-op locally and has never produced a working
devcontainer in Claude Code web sessions. The decision (human:author) is to
remove it with no replacement: a web session without the toolchain follows the
`AGENTS.md` escalation path — `/agentdev:microvm-sandbox`, then
`/agentdev:remote-codespace-session`.

Removing plugin surface is a breaking change, so the catalog version goes from
`3.4.0` to `4.0.0`.

## Scope

- Delete `.agents/plugins/agentdev/hooks/` (`hooks.json`, `session-start.sh`);
  the plugin then declares no hooks.
- Remove the `### Hooks` section from `.agents/plugins/agentdev/README.md`.
- Bump the aligned version pins to `4.0.0`: both plugin manifests
  (`.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`),
  `.claude-plugin/marketplace.json`, and
  `docker/desktop/agent-desktop.Dockerfile`; check every other file carrying
  `3.4.0` (`README.md`, `docker/ansible/setup-ansible.sh`).

Unaffected: the Codex manifest declares no hooks, and the self-improve plugin
keeps its own `SessionStart` hook. No test or CI workflow references the
agentdev hook.

## Done when

- No file under `.agents/plugins/agentdev/` references `SessionStart` or
  `hooks/`.
- No agentdev `3.4.0` pin remains.
- Catalog validation passes.
