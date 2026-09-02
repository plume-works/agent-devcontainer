---
type: feature
stage: implemented
description: The agent-desktop image installs the staged agentdev catalog at build time while devcontainers continue reinstalling into mounted plugin volumes.
generated:
  by: codex/gpt-5
  at: 2026-09-02T06:07:09Z
sources:
- resource: docs/knowledge/data/plans/20260817-catalog-install-in-image.md
- resource: docs/knowledge/data/spec/catalog-lifecycle.md
- resource: ansible/roles/agentic_tools/tasks/install_catalog.yml
- resource: docker/desktop/agent-desktop.Dockerfile
- resource: .devcontainer/scripts/postCreateCommand.sh
---

# Build-time agentdev catalog install

## Purpose

Raw-image consumers should receive the `agentdev` catalog the image already
stages, even when they run the image outside a devcontainer and no lifecycle
hooks execute.

## Behaviour

**The image installs the staged catalog during provisioning.** `agentic_tools`
registers the staged marketplace root and installs `agentdev` for both Claude
and Codex when `agentic_tools_install_catalog` and `agentic_tools_stage_catalog`
are enabled.

**The devcontainer lifecycle remains authoritative for mounted volumes.**
`postCreateCommand.sh` still installs the staged catalog into the mounted
`~/.claude` and `~/.codex` volumes, because those volumes shadow the plugin
state written during the image build.

**Claude config is handed to the volume before CBM installation.** When the
image ships a real `/root/.claude.json`, `postCreateCommand.sh` discards that
file, seeds `/root/.claude/claude.json` only for a fresh volume, and symlinks
`/root/.claude.json` to the volume before `codebase-memory-mcp-install.sh` runs.
Existing volume content is preserved, and image config content is not merged
into the volume.

## References

- Plan:
  [Install the agentdev catalog into the image](../plans/20260817-catalog-install-in-image.md)
- Spec: [Catalog lifecycle](../spec/catalog-lifecycle.md)
- Related decision:
  [CI agent plugin availability](../architecture/ci-agent-plugin-availability.md)
