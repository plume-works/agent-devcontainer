---
type: feature
description: OpenCode automatically registers a newly opened Git workspace with the shared codebase-memory daemon.
stage: implemented
generated:
  by: claude-code/opus-5.5
  at: 2026-10-19T02:00:00Z
sources:
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
- resource: .devcontainer/scripts/codebase-memory-mcp-start.sh
- resource: .devcontainer/scripts/codebase-memory-mcp-index.sh
---

# Automatic CBM indexing for OpenCode workspaces

## Purpose

Make the repository opened in OpenCode available to codebase-memory even when
the container was started for another repository.

## Behaviour

With agentdev's bridge and a local, enabled codebase-memory MCP configured,
opening a Git workspace checks the shared daemon for that exact repository root.
An absent repository is submitted for background indexing. Existing projects
remain available; a registered repository is not reindexed simply because
another conversation opens.

The bridge uses the active workspace, including the distinct root of a linked
Git worktree, rather than the catalog location or the container's original
workspace. Startup and catalog loading do not wait for indexing to finish. On
OpenCode v2 this happens for each directory OpenCode opens, and a failure is a
warning in `opencode.log`, as on v1.

## Edge cases

- A subdirectory or symlink resolves to the canonical worktree root.
- A non-Git directory is skipped.
- Missing, disabled, or remote CBM configuration is skipped.
- CBM command failures, invalid responses, or denied roots produce an OpenCode
  diagnostic without interrupting catalog loading or broadening CBM access.
- Concurrent requests for the same root join or deduplicate indexing; failed
  attempts may retry on the next workspace initialization.
- Existing container startup and attach indexing continue to work.

## Open questions

None. This feature covers OpenCode; other agent clients are separate work.
