---
type: architecture
description: Claude Code and OpenCode are the two agent harnesses the images, runtime, catalog, CI, and e2e suites support; Codex is not supported, while validate_agent_files keeps its Codex ecosystem for other repositories.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T20:33:45Z
sources:
- resource: docs/knowledge/data/features/claude-and-opencode-only-harnesses.md
- resource: py_packages/agentdev_runtime/agentdev_runtime/catalog.py
- resource: py_packages/validate_agent_files/validate_agent_files/paths.py
---

# Supported harnesses

## Decision

The maintainer chose Claude Code and OpenCode as the only agent harnesses this
repository supports ([Claude Code and OpenCode are the only supported
harnesses](../features/claude-and-opencode-only-harnesses.md)). Codex is not
supported anywhere:

- the images do not install the Codex CLI, and the runtime writes no Codex
  configuration, hooks, credential links, or `CODEX_HOME`;
- the `agentdev` catalog ships a Claude Code plugin
  (`.claude-plugin/marketplace.json`) and an OpenCode bridge plugin
  (`.agents/plugins/agentdev/.opencode-plugin/`), and nothing for Codex;
- a catalog checkout is complete with those two, so `catalog install` and the
  attach override register Claude Code and OpenCode only;
- CI validates the catalog with `--require-marketplace claude`, and the e2e
  suites run Claude Code and OpenCode.

A user may still install Codex inside a container; nothing configures it or
registers the catalog for it.

## What is not Codex support

- `validate_agent_files` keeps its general `codex` ecosystem. The package is
  released independently and validates other repositories' catalogs (product
  constraint), so only this repository's own CI call drops `codex`.
- The `chatgpt-codex-connector[bot]` GitHub actor is a third-party reviewer on
  GitHub, not a harness running here; the workflows and tests that recognize it
  stay.

## Rejected alternatives

- **Keep `.codex-plugin/plugin.json` as an untested, install-yourself package.**
  Codex loads catalog agents only through the generated TOML agents the agent
  installer wrote; without that installer none of the agents the skills dispatch
  would load, so the package would ship broken.
