---
type: bug
description: In a Claude Code cloud session the devcontainer can run without the proxy and token from .devcontainer/cloud-session.env, and .claude/startup.py resume does not recover it, so gh and git push fail inside the container.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-04T03:33:47Z
sources:
- resource: .claude/startup.py
- resource: .claude/settings.json
- resource: .devcontainer/docker-compose.yml
- resource: scripts/tests/test_cloud_startup.py
- resource: https://github.com/plume-works/agent-devcontainer/pull/686
stage: done
severity: high
---

# Bug: cloud devcontainer runs without the session env, and resume does not recover it

## Symptom

Inside the devcontainer of a Claude Code cloud session, `gh` reports that it is
not authenticated and `git push` has no credentials. The container's environment
has no `GH_TOKEN` and no `HTTPS_PROXY`, although
`.devcontainer/cloud-session.env` on the host holds both. Running
`.claude/startup.py resume`, the documented recovery, leaves the container as it
is.

## Reproduction

1. On a cloud-session host, bring the devcontainer up while
   `.devcontainer/cloud-session.env` is absent.
2. Run `.claude/startup.py resume` with the session's loopback `HTTPS_PROXY`. It
   writes `.devcontainer/cloud-session.env` and starts the relay.
3. Run `devcontainer exec --workspace-folder . bash -lc 'gh api user'`: it still
   fails, and `docker inspect` shows no `GH_TOKEN` in the container's
   environment.

Removing the container and running `resume` again creates it with the file and
restores `gh` and `git push`.

## Root cause

- **Why it persists — settled.** A container's environment is fixed when it is
  created. When the container is running, `resume` only refreshes the relay and
  rewrites `cloud-session.env`; it never compares the container's environment
  with that file or recreates the container.
- **How the container came to lack the file — not settled.** The container was
  created before the session's `SessionStart` hook ran, at a point when
  `cloud-session.env` did not exist.
  - Eliminated: the `SessionStart` hook running without a loopback `HTTPS_PROXY`
    and deleting the file. The hook's recorded output shows it starting the
    relay to the loopback proxy, and the container predates the hook's run.
  - Open: the environment setup script ran `devcontainer up`, directly or
    through `.claude/startup.py setup`, without a loopback `HTTPS_PROXY`, so
    `prepare_proxy_access` removed the file before `devcontainer up`.
  - [Settle how the cloud devcontainer is created without its session
    env](../backlog/settle-cloud-devcontainer-created-without-session-env.md)
    settles it.

## Fix

`setup` and `resume` compare each existing devcontainer's environment with
`cloud-session.env`. When a line of the file is missing from it or carries a
different value, they run `devcontainer up --remove-existing-container`, so the
container is recreated with the file; otherwise `resume` keeps a running
container. Without the file there is nothing to compare and the container is
kept. `scripts/tests/test_cloud_startup.py` covers a missing key, a different
value, a matching container, no container, and no file.
