---
type: feature
stage: implemented
description: OpenCode loads the agentdev catalog from the same tree as Claude Code and Codex through a dependency-free bridge plugin, with namespaced slash commands and tool-limited subagents, installed by the image build, postCreate, and postAttach.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-19T02:00:00Z
sources:
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
- resource: .devcontainer/scripts/reinstall-agentdev-opencode.sh
- resource: ansible/roles/agentic_tools/tasks/install_catalog.yml
- resource: ansible/roles/agentic_tools/defaults/main.yml
---

# OpenCode as a catalog host

## Purpose

The agentdev catalog serves Claude Code and Codex from one tree,
`.agents/plugins/agentdev/`. OpenCode has neither a Claude plugin loader nor a
Codex manifest format, so it could not use the catalog at all. This makes
OpenCode a third host for the same tree, without copies and without depending on
Claude Code.

## Behaviour

**A bridge plugin ships inside the catalog.**
`.agents/plugins/agentdev/.opencode-plugin/` sits next to `.claude-plugin/` and
`.codex-plugin/`, resolves the catalog root from its own location, and has no
runtime dependencies, so it runs from the read-only staged catalog in the image.
The same bridge loads in OpenCode v1 and v2.

**OpenCode sees the catalog the way the other hosts do.** Every catalog skill is
listed by OpenCode's skill tool and is a `/agentdev:<name>` slash command that
appears in autocomplete. On v2, running one sends only the user's words, with
the skill attached as a skill chip rather than pasted into the chat. The skill
tool accepts the catalog's namespaced `agentdev:<name>` spelling. A
`disable-model-invocation` skill is denied to the model but still runs as a
command. Each catalog agent is a subagent denied the tools its `tools:` list
omits, even under the devcontainer's full-access policy; the tools it lists keep
the user's own approval settings. Commands and skills the user already
configured win, and an agent the user defines under a catalog agent's name
replaces it, limits included.

**The image and the devcontainer lifecycle install it.** The image ships a
pinned OpenCode v2 CLI, `@opencode/cli`. The image build registers the staged
bridge in the user's OpenCode config, `postCreateCommand` registers it again,
and `postAttachCommand` points the entry at the workspace checkout, through
`reinstall-agentdev-opencode.sh`. Each run leaves exactly one bridge entry.

## Edge cases

- **A container with no lifecycle hooks.** The build-time registration is what
  OpenCode loads, and it lists every catalog skill.
- **A consuming project attaches.** Its checkout ships no bridge, so the
  attach-time script registers nothing and the image-staged bridge stays.
- **An existing OpenCode config.** Other keys and plugins are preserved, and an
  earlier bridge entry from another root is replaced.
- **Provider logins.** OpenCode keeps them in its database on the per-worktree
  `agentdev-opencode` volume, so each worktree logs in once; see [Agent auth
  persistence](../architecture/agent-auth-persistence.md).

## Open questions

None — self-improve on OpenCode and credential sharing are out of scope for this
feature.

## References

- Spec: [OpenCode catalog bridge](../spec/opencode-catalog-bridge.md), [Catalog
  lifecycle](../spec/catalog-lifecycle.md)
- Architecture: [OpenCode catalog
  bridge](../architecture/opencode-catalog-bridge.md)
- Plans: [Load the agentdev catalog into OpenCode through a bridge
  plugin](../plans/20261001-opencode-catalog-bridge.md), [Make OpenCode v2 the
  devcontainer default](../plans/20261018-opencode-v2-default.md)
