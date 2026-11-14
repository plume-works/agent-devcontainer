---
type: adr
stage: accepted
description: Claude Code and OpenCode are the only harnesses, but `validate_agent_files` keeps its `codex` ecosystem for other repositories.
---

# Claude Code and OpenCode are the only harnesses

The maintainer chose Claude Code and OpenCode as the only harnesses. The images
do not install Codex, and the runtime writes no Codex configuration.
`validate_agent_files` has its own releases and validates the catalogs of other
repositories, so it keeps its `codex` ecosystem. Only the CI of this repository
uses `--require-marketplace claude`.

## Considered Options

- A `.codex-plugin/plugin.json` package that users install themselves and that
  no test checks. Rejected: Codex loads catalog agents only through TOML agents
  that an installer writes. Without that installer, no agent that the skills
  dispatch can load, so the package does not work.

## Consequences

- No test checks that Codex is absent. This ADR records that the absence is a
  decision.
- The `chatgpt-codex-connector[bot]` reviewer on GitHub is not a harness. A test
  that identifies this bot is not Codex support.
