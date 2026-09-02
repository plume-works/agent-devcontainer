---
type: architecture
description: The three-part module layout (image build, devcontainer scaffolding, agent catalog) and how they compose at runtime.
generated:
  by: codex
  at: 2026-08-15T03:30:00Z
---

# Module layout

## The three responsibilities

The repository carries three distinct build/publish surfaces from one checkout,
documented as the authoritative inventory in
[Template boundary](template-boundary.md):

1. **Image build** (`ansible/` + `docker/`) — provisions and publishes
   `ghcr.io/plume-works/agent-desktop` and its `ubuntu-ansible` base,
   multi-arch, pinned by tag and digest.
2. **Agent catalog** (`.agents/plugins/agentdev/`) — the canonical Claude Code /
   Codex plugin: agents, skills, hooks, `bin/` scripts, and the plugin's own
   test suite (`.agents/plugins/agentdev/tests/`). Everything else that
   references the catalog (`.claude-plugin/`,
   `.agents/plugins/marketplace.json`, the `reinstall-agentdev-*.sh` scripts) is
   derived from this tree, never edited directly.
3. **Devcontainer scaffolding** (`.devcontainer/`) — the template surface a
   consuming project copies in: lifecycle scripts, MCP configuration, firewall
   allowlist, digest pin (`devcontainer-compose-pins.yml`).

A fourth, independently-released unit lives alongside these:
`py_packages/validate_agent_files/` — a Python package (own `pyproject.toml`,
isolated test suite) that validates agent/skill definitions. It must build and
test with zero knowledge of this repository, since it ships on its own.

## Runtime composition

How the three main surfaces come together for a consumer, per the README's
"Runtime flow" (verbatim structure, condensed):

``` text
ansible/ + docker/ + catalog publisher source
        -> ghcr.io/plume-works/agent-desktop  (digest-pinned in devcontainer-compose-pins.yml)
        -> .devcontainer/devcontainer.json + docker-compose.yml
        -> postCreateCommand (once): install staged agentdev catalog into
           persistent Claude/Codex state volumes
        -> postStartCommand (each start): CBM daemon, pre-commit, keyring,
           firewall, Xpra, workspace catalog override if present
```

The image stages the catalog read-only at `/opt/agentdev`
(`AGENTDEV_CATALOG_DIR`); it does not stage the devcontainer scaffolding itself
— that's copied manually per
[Template consumption](../spec/template-consumption.md).

## Key design decisions

- **Catalog install happens in a lifecycle hook, not the image build.** The
  `agentdev-claude` / `agentdev-codex` volumes mount over `~/.claude` /
  `~/.codex` — exactly where each agent records installed plugins — so a
  build-time install would be shadowed by the volume mount on every container
  after the first. Installing in `postCreateCommand` instead means the install
  runs once per devcontainer instance (volumes are scoped per instance), while
  credentials alone are shared across worktrees via the separate
  `agentdev-agents-auth` volume.
- **This repository's own `postAttachCommand` re-registers the workspace
  marketplace on every editor attach**, overriding the image's staged copy —
  because this repo *develops* the catalog it ships, unlike a normal consumer
  which only installs the image's copy. Other projects' reinstall scripts find
  no marketplace manifest here and exit quietly.
- **Images are pinned by tag and digest everywhere, never a bare moving tag**,
  so a rebuild upstream never silently changes what a consumer runs; Renovate
  advances the pin deliberately.
- **`.agents/plugins/agentdev/` is the single source of truth for the catalog.**
  Codex consumes it directly (no `.codex/agents` trampoline, no symlink);
  scripts under `bin/` resolve the target repository from the working directory
  rather than assuming they run inside this checkout, since the same scripts run
  inside a consumer's plugin cache.
- **`validate_agent_files`'s test suite is deliberately kept separate** from the
  plugin's own test suite (`.agents/plugins/agentdev/tests/`) so the package
  continues to pass with no repository-specific fixtures, since it is released
  independently of this repo.

## Unknowns

- Internal structure of `ansible/roles/` and how the provisioning roles compose
  (role dependency graph, which roles are load-bearing vs. optional) — not
  mapped yet; see the provisioning knobs table in the README for the toggles,
  but not the role internals.
- The Xpra/VirtualGL desktop subsystem's internal wiring beyond port derivation
  (`14500 + cksum(DEVCONTAINER_ID) % 100`) is not detailed here.
