---
type: adr
stage: accepted
description: On OpenCode v2, the bridge applies the declared tools of a catalog agent in the context and evaluate hooks, and only while the agent still has the catalog prompt.
---

# On OpenCode v2, hooks apply the tool limits of a catalog agent

Claude Code applies the declared tools of a catalog agent under full access, and
the OpenCode bridge gives OpenCode the same limits. v2 adds the global
`permission` rules at the end of each agent after all plugins change the agent,
and the last rule that matches applies. For this reason, the bridge removes each
denied tool in `session.hook("context")` and denies its actions in
`permission.hook("evaluate")`.

## Considered Options

- Deny rules on the v2 agent. Rejected: v2 adds the global rules after them, so
  full access removes the limits.
- Remove the tool limits on all harnesses. Rejected: Claude Code applies them
  under full access.
- Read the configuration files of the user to find a replaced agent. Rejected:
  plugins cannot query the v2 configuration search, so the bridge must copy it.

## Consequences

- The hooks apply the limits only while the `system` prompt of the agent is the
  catalog body. v2 merges agents with the same ID and shows no user
  configuration to plugins.
- As a result, an agent that the user defines with the ID of a catalog agent
  replaces it, and only the permissions of the user apply. A field that the
  agent of the user does not set, such as `description` or `mode`, keeps the
  catalog value.
- The bridge denies each action that the `tools:` list does not map to, and also
  `question`, which no Claude tool maps to. `TodoWrite` maps to no v2 action.
- The `evaluate` hook only sets `deny`. It does not change the approval of a
  tool that the agent can use.
- A `tools:` list limits the tools but does not approve them, so each mapped
  tool keeps the approval settings of the user.
- `browser` stays at the v2 default deny. The bridge does not change `execute`,
  which applies only to code-mode tools.
