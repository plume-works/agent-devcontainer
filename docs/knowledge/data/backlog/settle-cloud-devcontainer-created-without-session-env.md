---
type: task
description: Find which step of a fresh Claude Code cloud session creates the devcontainer without .devcontainer/cloud-session.env.
stage: done
priority: medium
created: 2026-11-04
completed: 2026-11-04
generated:
  by: claude-code/opus-5.5
  at: 2026-11-04T03:49:43Z
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

## Result

The environment setup script creates the devcontainer without
`cloud-session.env`, because it runs without the session's loopback
`HTTPS_PROXY`:

- The setup script runs `.claude/startup.py setup` once, when the session's host
  is built: it installs `~/.claude/CLAUDE.md`, pre-pulls the pinned images,
  installs the devcontainer CLI, and creates the container.
- In `bring_devcontainer_up`, `prepare_proxy_access` either writes
  `cloud-session.env`, when `HTTPS_PROXY` names a loopback proxy, or removes it;
  any other outcome raises before `devcontainer up`. A container created there
  without the file therefore means the setup environment had no loopback
  `HTTPS_PROXY`.
- The `SessionStart` hook that follows does see the loopback proxy: it starts
  the relay to it and writes the file, after the container exists.

Recreating the container from `resume` is therefore needed on every fresh
session, not only after a worker restart. A recreate runs container creation and
the `postCreate`, `postStart` and `postAttach` commands, about 30 seconds each,
inside the `SessionStart` hook; pulling and building a changed image pin adds to
that.
