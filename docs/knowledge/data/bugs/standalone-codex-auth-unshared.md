---
type: bug
description: In a standalone agent-opencode deployment, a project held a regular ~/.codex/auth.json instead of the symlink into the shared auth volume, so a second project with the same identity was not logged in to Codex until link-codex-auth.sh ran; which Codex action replaced the symlink is not yet settled.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T20:56:59Z
sources:
- resource: .devcontainer/scripts/link-codex-auth.sh
- resource: .devcontainer/scripts/setup-agent-state.sh
- resource: .devcontainer/scripts/runtime-workspace.sh
stage: cancelled
---

# Bug: Codex login stops being shared between standalone projects

## Symptom

During the deployment acceptance of [Ship a standalone OpenCode
container](../plans/20261017-standalone-opencode-container.md), a second project
with the same `AGENTDEV_UID`, `AGENTDEV_GID`, and `AGENTDEV_AUTH_VOLUME` was not
logged in to Codex. In the first project, `~/.codex/auth.json` was an
`agent`-owned regular file, and the shared target
`/var/lib/agentdev/auth/codex/auth.json` did not exist. Running
`link-codex-auth.sh` as `agent` moved the file to the shared target and restored
the symlink. A third project then shared the login, and the first stayed logged
in. Claude Code's login was shared throughout.

## Reproduction

Not yet reproduced on purpose. The observed sequence was:

1. Start a standalone project. Preparation runs `setup-agent-state.sh create`,
   which links `~/.codex/auth.json` to the shared target.
2. Log in to Codex as `agent` with `codex login`, more than once across runs.
3. Start a second project with the same identity and auth volume: Codex is not
   logged in, and the first project's `auth.json` is a regular file.

## Root cause

Not settled. Two hypotheses fit the observation:

- **A logout before a login.** `codex logout` unlinks `auth.json` rather than
  clearing it, and the next `codex login` writes a regular file. The linker
  repairs that only on the next container start. `link-codex-auth.sh` already
  documents this window.
- **Login replaces the symlink.** The installed Codex, 0.164.0, may now write
  `auth.json` by renaming a temporary file over it. That would break the link on
  every login, not only after a logout. The linker's note that login writes
  through the symlink was verified against an earlier Codex.

One check separates them: in a running project with the symlink in place, run
`codex login` as `agent`, then test `[[ -L ~/.codex/auth.json ]]`.

## Fix

Not fixed: cancelled. Codex support was removed ([Supported
harnesses](../architecture/supported-harnesses.md)), so the runtime no longer
shares a Codex login and the link this bug concerns no longer exists.

## Key references

Verified anchor points (line numbers as of 2026-10-25):

- `.devcontainer/scripts/link-codex-auth.sh:30` — a regular local file is moved
  over the shared target; `:35` — the symlink
- `.devcontainer/scripts/setup-agent-state.sh:78` — `link_auth` in `create`;
  `:101` — the `links` command
- `.devcontainer/scripts/runtime-workspace.sh:110` — standalone preparation runs
  `create` on every start
