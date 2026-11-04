---
type: task
description: Find which step of a fresh Claude Code cloud session creates the devcontainer without .devcontainer/cloud-session.env.
stage: pending
priority: medium
created: 2026-11-04
generated:
  by: claude-code/opus-5.5
  at: 2026-11-04T03:22:57Z
sources:
- resource: .claude/startup.py
- resource: docs/knowledge/data/bugs/cloud-devcontainer-runs-without-session-env.md
---

# Settle how the cloud devcontainer is created without its session env

[Bug: cloud devcontainer runs without the session env, and resume does not
recover it](../bugs/cloud-devcontainer-runs-without-session-env.md) leaves open
which step creates the devcontainer before `.devcontainer/cloud-session.env`
exists. The open hypothesis is that the environment setup script runs
`devcontainer up` without the session's loopback `HTTPS_PROXY`.

Start a fresh cloud session on a branch carrying `.claude/startup.py`. Record
the environment setup command, whether `HTTPS_PROXY` is set in the setup
script's environment, the setup script's stderr, and the container's creation
time against the `SessionStart` hook's run. The answer decides whether `setup`
must refuse to bring the container up without the proxy, or whether recreating
the container from `resume` alone is enough.
