---
type: feature
stage: implemented
description: Claude Code and OpenCode are the only agent harnesses the images, runtime, agentdev catalog, CI, and e2e suites support; Codex is removed entirely.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T03:30:00Z
sources:
- resource: ansible/roles/agentic_tools/defaults/main.yml
- resource: py_packages/agentdev_runtime/agentdev_runtime/catalog.py
- resource: .agents/plugins/agentdev/.codex-plugin/plugin.json
- resource: .agents/plugins/agentdev/bin/install-codex-agents.py
- resource: scripts/e2e/iwe-workflows/harness_codex.py
---

# Claude Code and OpenCode are the only supported harnesses

## Purpose

The devcontainer, the `agentdev-base`, `agentdev-devcontainer`, and
`agentdev-deploy` images, the `agentdev` catalog, CI, and the e2e suites support
exactly two agent harnesses: Claude Code and OpenCode. Codex is not supported.

## Behaviour

- The images do not install the Codex CLI.
- The runtime does not configure Codex: there is no full-access `config.toml`
  policy, no CBM Codex hooks repair, no shared Codex `auth.json` link, and no
  `CODEX_HOME`.
- The catalog ships no Codex package: no `.codex-plugin/plugin.json`, no
  `.agents/plugins/marketplace.json`, no per-skill `agents/openai.yaml`, and no
  Codex agent installer.
- The repository has no `.codex/` directory and the devcontainer declares no
  `agentdev-codex` volume.
- The e2e suites run Claude Code and OpenCode only, and CI requires only the
  Claude marketplace.
- The general-purpose `validate_agent_files` package keeps its Codex ecosystem
  support, because it validates other repositories' catalogs.

A partial Codex package — the plugin manifest kept as an untested,
install-yourself option — was rejected: without the agent installer Codex loads
none of the catalog agents its skills dispatch, so the package would ship
broken.

## Edge cases

- An existing devcontainer keeps its `agentdev-codex` volume, and the shared
  agents-auth volume keeps `codex/auth.json`. Nothing removes them; a user
  deletes them by hand.
- A user may still install Codex themselves inside a container; nothing in the
  runtime configures or registers the catalog for it.
- This supersedes [Codex full-access config](codex-full-access-config.md).

## Open questions

None — the maintainer settled scope, the validator boundary, and the upgrade
note.
