---
type: adr
stage: accepted
description: The Dev Container and the standalone runtime set the subagent depth limit of Claude Code and OpenCode to 5, and the compose files hold the Claude Code value.
---

# Both harnesses permit a subagent depth of 5 in the containers

Catalog agents start other catalog agents, so each harness must permit a
subagent that starts a subagent. The Dev Container and the standalone runtime
set the depth limit of Claude Code and of OpenCode to 5. A native host such as
macOS keeps the default limit of Claude Code.

## Considered Options

- The default limits of the harnesses. Rejected: at its default depth of 1,
  OpenCode refuses each nested `task` call. Without the variable, a server-side
  flag sets the limit of Claude Code, and the container does not.
- `env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` in the `settings.json` of Claude
  Code, from `agentdev-runtime state agent-policy`. Rejected: the maintainer
  wants the value in the container definition.
- A `~/.claude/settings.json` that the Ansible `agentic_tools` role writes into
  the image. Rejected: when the home volume holds this file, the volume hides
  the file of the image.

## Consequences

- A Claude Code agent can dispatch only when its `tools:` list includes `Agent`,
  or when it has no `tools:` list. For this reason, `iwe-shipper` lists `Agent`,
  and it dispatches `iwe-verifier` through `/agentdev:iwe-verify`. This dispatch
  is nested.
- The agents that the Implement loop dispatches start no other agent, so the
  loop does not need the depth setting.
- `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` is in the `environment:` of
  `.devcontainer/docker-compose.yml` and `compose.opencode.yml`, and a value on
  the host replaces it.
- `py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py` writes
  `experimental.subagent_depth`. OpenCode can rename or remove an `experimental`
  key, and the maintainer accepts this risk.
