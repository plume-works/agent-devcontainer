---
type: adr
stage: superseded
---

# The Coder agent start runs OpenCode and Remote Control in a Dev Container

The `devcontainer` runtime profile does not include the `opencode` service or
the `remote-control` service. In a Coder workspace, the agent start
`agentdev-runtime coder start` starts the two servers. The `deploy` runtime
profile continues to supervise them. This is the decision of the maintainer.

PID 1 starts before the Coder agent. Thus a server that PID 1 starts does not
get the Coder user secrets or the git credential helper. When PID 1 and the
agent start both start a server, a Coder workspace has two copies of it. Each
copy has a different environment, and the copy that starts first holds the port
or the tmux session.

## Consequences

- `AGENTDEV_OPENCODE_WEB` is removed. In a Dev Container that Coder does not
  start, nothing starts OpenCode Web or Remote Control. You can start each one
  manually with `agentdev-runtime opencode coder-start` and
  `agentdev-runtime remote-control start`.
- In a Coder workspace, nothing restarts a server that stops, and nothing starts
  Remote Control after a later claude.ai login. A restart of the agent starts
  both again.
