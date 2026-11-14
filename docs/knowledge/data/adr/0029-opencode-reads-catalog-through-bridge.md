---
type: adr
stage: accepted
description: OpenCode reads the agentdev catalog from the same tree as Claude Code, through a bridge plugin that translates skills, commands, and agents at start.
---

# OpenCode reads the catalog through a bridge plugin

OpenCode is the second harness of the catalog. It reads the same tree as Claude
Code, `.agents/plugins/agentdev/`, through the OpenCode bridge at
`.agents/plugins/agentdev/.opencode-plugin/index.ts`. The bridge translates
skills, commands, and agents when OpenCode starts.

## Considered Options

- The Claude compatibility layer of oh-my-opencode. Rejected: its license is the
  Sustainable Use License, which is not an open-source license. It sends
  telemetry by default. It finds plugins through the `installed_plugins.json` of
  Claude Code, so OpenCode then needs a Claude installation.
- Distribution through the OCX registry. Rejected: it copies files into
  `.opencode/` without conversion, so it gives no namespaced commands and no
  agent mapping.

## Consequences

- The `agent_catalog` Ansible role adds the absolute path of the staged bridge
  to the OpenCode configuration of the user. The bridge is not on npm.
- The bridge has no runtime dependencies. It uses only type imports and the
  built-in modules of Bun. Root owns the staged catalog and it is read-only, so
  no `node_modules` directory can go next to it.
- An explicit-only skill gets `permission.skill.<name> = "deny"` on v1 and
  `autoinvoke: false` on v2. The model then cannot load it, but its
  `agentdev:<name>` command still runs.
- The bridge does not change a key that the configuration of the user already
  sets. On v2, a skill or a command of the user with the same name has priority
  through the order of the host.
- A catalog agent becomes an OpenCode subagent. The bridge denies each OpenCode
  tool that its `tools:` list does not map to, and the mapped tools stay unset,
  so the approval settings of the user apply to them.
- OpenCode reads the bridge only when it starts. After a change to the bridge or
  to its configuration, the user stops OpenCode and starts it again.
