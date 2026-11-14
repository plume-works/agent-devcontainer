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
