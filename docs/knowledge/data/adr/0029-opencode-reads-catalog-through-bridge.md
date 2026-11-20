---
type: adr
stage: accepted
description: OpenCode reads the agentdev catalog from the same tree as Claude Code, through the OpenCode bridge, which translates skills, commands, and agents at start.
---

# OpenCode reads the catalog through the OpenCode bridge

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
  `.opencode/` without conversion, so it gives no namespaced commands
  (`agentdev:<skill-name>`) and no agent mapping.

## Consequences

- The bridge has no runtime dependencies. It uses only type imports and Bun or
  Node built-in modules, because it loads from the root-owned, read-only catalog
  staged in the image, where no `node_modules` directory can be installed beside
  it.
