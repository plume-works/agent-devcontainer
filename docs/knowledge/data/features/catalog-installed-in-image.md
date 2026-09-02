---
type: feature
stage: implemented
description: The agent-desktop image installs the agentdev catalog into each agent's plugin state at build time, so a consumer running the raw image with no devcontainer lifecycle hooks still resolves agentdev:* skills; postCreate installs again because mounted volumes shadow the build-time install.
generated:
  by: claude-code/opus-5
  at: 2026-09-02T00:00:00Z
sources:
- resource: ansible/roles/agentic_tools/tasks/install_catalog.yml
- resource: docker/desktop/agent-desktop.Dockerfile
- resource: .devcontainer/scripts/postCreateCommand.sh
---

# Install the agentdev catalog into the image

## Purpose

The `agent-desktop` image staged the `agentdev` catalog at `/opt/agentdev` but
never installed it — the marketplace was unregistered and the plugin cache
empty. Installation belonged to the devcontainer lifecycle scripts, which a
consumer that starts the image *without* those hooks (a plain `docker run`, a
Codespace, a CI job) never runs. Such a consumer got a catalog present on disk
and unusable, and the failure was quiet: an agent asked for a skill that does
not resolve improvises instead of failing. This closes that gap for raw-image
consumers.

## Behaviour

**The catalog is installed during the image build.** `agentic_tools` gains an
install step after staging, gated by `agentic_tools_install_catalog` (the
Dockerfile passes it `true`). It reads the marketplace names from the staged
Claude and Codex manifests rather than hardcoding them, then registers the
staged root as a marketplace and installs the plugin for Claude at user scope
and for Codex. The build stays offline and needs no auth — the marketplace is
added from the local staged path. A container run from the image with no volumes
and no lifecycle hooks resolves `agentdev:*` skills.

**postCreate still installs, because volumes shadow the build.** A devcontainer
mounts persistent `~/.claude` / `~/.codex` volumes over where both agents record
installed plugins, so the build-time install is invisible there;
`postCreateCommand.sh` installs again on every create, so the workspace's
catalog is never silently stale.

**The `~/.claude.json` handoff runs before cbm-install.** The build-time Claude
install seeds a real `/root/.claude.json` into the image.
`codebase-memory-mcp-install.sh` folds its MCP entry back into the volume only
when `/root/.claude.json` is already a symlink, so `postCreateCommand.sh`
establishes the volume→`/root/.claude.json` symlink up front — discarding the
image's real file, seeding `/root/.claude/claude.json` with `{}` only when the
volume has none. An existing volume's `claude.json` content is preserved across
a rebuild; a fresh volume is seeded clean with no image content.

## Scope

Changing how the lifecycle scripts install the catalog is out of scope — they
keep installing unconditionally; this adds a second, earlier install for
consumers that never run them. The one lifecycle change is the `~/.claude.json`
handoff reorder, a consequence of the image now shipping that file. Making
`~/.claude.json` volume-backed stays out (Docker volumes are directory-backed;
the symlink workaround stays). This is deliberately independent of the AI
responder workflows, which use the branch checkout and do not depend on it.

Rejected: having each raw-image consumer install the catalog itself (duplicates
lifecycle-script logic and leaves the image carrying a catalog that looks
installed but is not); an unconditional `rm` of the image's `/root/.claude.json`
before cbm-install (clobbers an existing volume by severing cbm-install's only
path back to the volume's content).

## References

- Spec: [Catalog lifecycle](../spec/catalog-lifecycle.md)
- Architecture:
  [CI agent plugin availability](../architecture/ci-agent-plugin-availability.md)
- Plan:
  [Install the agentdev catalog into the image](../plans/20260817-catalog-install-in-image.md)
