---
type: bug
description: After a worker restart in a Claude Code cloud session, the devcontainer is stopped and, once up again, points at an agent proxy port that no longer exists, so gh and git push fail inside it.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-04T04:00:00Z
sources:
- resource: .claude/startup.sh
- resource: .claude/settings.json
- resource: .claude/agent-proxy-relay.py
- resource: .devcontainer/docker-compose.yml
stage: done
severity: medium
---

# Bug: cloud devcontainer loses the agent proxy after a worker restart

## Symptom

After the session's worker process restarts, `docker` on the session host
reports `Cannot connect to the Docker daemon`, and the devcontainer is stopped.
Once the container is up again, `git push` inside it fails with
`Failed to connect to host.docker.internal port <old port>`, and `gh` fails with
`connection refused`.

## Reproduction

1. In a Claude Code cloud session, let `.claude/startup.sh` bring the
   devcontainer up, so its `HTTPS_PROXY` names the relay on the agent proxy's
   port at that time.
2. Restart the session's worker process. The host `dockerd` and the relay stop,
   and `HTTPS_PROXY` on the host now names a different port.
3. Restart `dockerd` and run `devcontainer up`, then run
   `git push --dry-run origin HEAD` in the container.

## Root cause

- `.claude/startup.sh` runs only as the environment setup script when the
  session's host is built. Nothing runs it after a worker restart, which stops
  the host `dockerd`, the relay, and the container.
- The relay listened on the agent proxy's own port, and that port went into the
  container's environment through `.devcontainer/cloud-session.env`. The
  container's environment is fixed when it is created, and `devcontainer up`
  restarts an existing container rather than recreating it, so the container
  kept the old port after the proxy moved.

## Fix

- The relay listens on the fixed port 3128 and forwards to the proxy's current
  port, so the container's `HTTPS_PROXY` stays valid when the proxy moves.
- `.claude/startup.sh resume` restores what a worker restart stops: it starts
  `dockerd` when it is down, restarts the relay unless a relay to the current
  port is alive, and brings the container up when it is not running. A relay
  counts as alive only while `/proc/<pid>/cmdline` still names it with that
  port.
- A `SessionStart` hook in `.claude/settings.json` runs it. Resume mode does
  nothing unless `CLAUDE_CODE_REMOTE=true` and `AGENTDEV_RUNTIME_MODE` is unset,
  so the devcontainer's own sessions and non-cloud hosts are untouched.

Design: [Cloud session
devcontainer](../architecture/cloud-session-devcontainer.md).
