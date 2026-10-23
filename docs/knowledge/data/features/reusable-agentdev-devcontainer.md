---
type: feature
stage: accepted
description: A published agentdev-devcontainer image owns the reusable Dev Container lifecycle and supervised services so repositories can use agentdev without copying their implementation.
generated:
  by: codex/gpt-5
  at: 2026-10-23T02:35:00Z
sources:
- resource: docs/user-stories/agent-containers.md
- resource: docker/desktop/agent-desktop.Dockerfile
- resource: docker/opencode/agent-opencode.Dockerfile
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/scripts/runtime-supervisor.py
- resource: .devcontainer/scripts/postCreateCommand.sh
- resource: .devcontainer/scripts/postStartCommand.sh
- resource: .devcontainer/scripts/postAttachCommand.sh
---

# Reusable agentdev Dev Container

## Purpose

Publish a reusable `agentdev-devcontainer` image that supplies agentdev's Dev
Container lifecycle, persistent services, tools, catalog, and default policy.
Repositories can use or derive from that image without copying the lifecycle
implementation into every checkout.

## Behaviour

- Publish an image family rooted at lifecycle-neutral `agentdev-base`, renamed
  from `agent-desktop`. Publish `agentdev-deploy`, renamed from
  `agent-opencode`, and the new `agentdev-devcontainer` as sibling derivatives.
- Bundle the Dev Container lifecycle implementation and stable lifecycle entry
  points in `agentdev-devcontainer`; repository configuration selects mounts,
  environment, editor customization, and optional repository-owned hooks rather
  than carrying copies of agentdev scripts.
- Run persistent Dev Container services under an image entrypoint that reuses
  the deploy runtime's supervised service primitives with a Dev
  Container-specific profile. Keep create-, start-, and attach-scoped work in
  thin image-provided lifecycle commands whose timing cannot be represented by
  PID 1.
- Preserve the current agentdev-development workflow: this repository opens in
  its own Dev Container and its checkout catalog overrides the staged catalog on
  attachment.
- Let a consuming repository reference the published image directly or derive a
  custom image from it while retaining the agentdev lifecycle. Environment
  variables and ordered hook directories provide explicit customization points.
- Keep full template adoption through `template-consume` supported. Full and
  minimal adoption use the same published runtime; extracting the shared IWE
  bootstrap is separate work.
- Build, test, publish, pin, and use the Dev Container image in repository CI so
  automated reviews exercise the same runtime family as interactive work.

## Edge cases

- A repository with no local agentdev catalog continues using the immutable
  catalog staged in the image; this repository's complete checkout catalog wins
  without rebuilding the image.
- Restarting, rebuilding, and reattaching retain their distinct lifecycle
  semantics. The entrypoint does not silently replace create-once or
  attach-scoped operations.
- Derived images and full-adoption repositories can add hooks without replacing
  managed entry points or modifying files below the image-owned runtime root.
- A service failure is reported through readiness and bounded recovery; the
  editor must not attach to a container whose required runtime failed.
- Per-worktree caches and path-bearing agent state remain isolated while the
  intentionally shared credential state remains shared.

## Open questions

None — the image boundary, inheritance model, lifecycle split, and continued
support for full template adoption are settled.
