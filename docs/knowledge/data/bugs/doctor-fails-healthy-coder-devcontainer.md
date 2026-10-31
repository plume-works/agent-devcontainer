---
type: bug
description: In a Compose Dev Container under Coder without the opt-in mcp profile, agentdev-runtime doctor fails the mcp-gateway and git user checks although the workspace is healthy.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T17:30:54Z
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/doctor.py
- resource: .devcontainer/devcontainer-init.sh
- resource: .devcontainer/docker-compose.yml
---

# Bug: doctor fails a healthy Coder Dev Container

## Symptom

In this repository's Compose Dev Container under Coder, with credentials,
`agentdev-runtime doctor` ends `Overall: FAIL` with exactly three failures while
every other check passes: `mcp-gateway DNS` (`getent` exits 2),
`mcp-gateway :8811` (`curl` cannot resolve `mcp-gateway`), and `git user` (name
or email missing).

## Reproduction

1. Start the Dev Container on a host with no `~/.docker/mcp` directory, so
   `devcontainer-init.sh` writes no `COMPOSE_PROFILES=mcp` and Compose never
   starts the `mcp`-profile sidecar.
2. Use a Coder workspace whose git identity comes from `GIT_AUTHOR_NAME`,
   `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME`, and `GIT_COMMITTER_EMAIL`, with no
   `user.name` or `user.email` in git config. Commits succeed.
3. Run `agentdev-runtime doctor`.

## Root cause

- In the devcontainer profile, `doctor` checks the `mcp-gateway` sidecar
  unconditionally, though Compose starts it only under the opt-in `mcp` profile,
  and the container receives no signal saying whether that profile is enabled.
- The `git user` check reads only `git config user.name` and `user.email`,
  ignoring the environment identity git itself honors.

Both checks were carried over unchanged from the retired
`environment-health.sh`.

## Fix

Task 21 of [Replace the runtime shell scripts with one agentdev-runtime
CLI](../plans/20261029-off-bash-migration.md). Compose passes `COMPOSE_PROFILES`
into the `devcontainer` service, and `doctor` checks `mcp-gateway` only when it
names `mcp`, reporting it SKIP otherwise (commit 27c1ab21). `git user` passes
when `git var GIT_AUTHOR_IDENT` and `GIT_COMMITTER_IDENT` both resolve (commit
666da330).

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `py_packages/agentdev_runtime/agentdev_runtime/doctor.py:142` — `gateway`: the
  `mcp-gateway` checks, skipped unless `COMPOSE_PROFILES` names `mcp` (`:145`)
- `py_packages/agentdev_runtime/agentdev_runtime/doctor.py:233` — `git user`
  resolves identity through `git var`; `:240` — its FAIL
- `.devcontainer/docker-compose.yml:70` — `COMPOSE_PROFILES` passed into the
  `devcontainer` service
- `.devcontainer/devcontainer-init.sh:57` — `COMPOSE_PROFILES=mcp` (`:61`)
  written only when `~/.docker/mcp` exists
- `.devcontainer/docker-compose.yml:7` — the sidecar's `profiles: ['mcp']`
