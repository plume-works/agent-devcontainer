---
type: feature
stage: implemented
description: Xpra listens on container port 14500, which the devcontainer forwards explicitly, and VS Code chooses the local port, so each devcontainer's remote desktop opens from the Ports panel.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-16T12:00:00Z
sources:
- resource: docs/knowledge/data/plans/20260905-xpra-vscode-port-forwarding.md
- resource: .devcontainer/devcontainer.json
---

# Xpra port forwarding

## Purpose

Separate devcontainers have separate network namespaces, so each can serve Xpra
on the same container port; a port derived from the container ID added nothing
and could still collide.

## Behaviour

**One container port.** Xpra listens on `14500` by default, and `forwardPorts`
declares it explicitly, so forwarding does not depend on process auto-detection.
`--port` still overrides the container port.

**VS Code picks the local port.** Developers open the Xpra HTML5 entry from the
Ports panel.

The contract is [Xpra port forwarding](../spec/xpra-port-forwarding.md).

## Edge cases

- **The preferred local port is taken.** VS Code forwards to another local port.
- **A container reopened on an older image digest** keeps the old start script;
  the forwarding change needs the image that carries the new one.

## Open questions

None — the design is settled.

## References

- Plan: [Xpra VS Code port
  forwarding](../plans/20260905-xpra-vscode-port-forwarding.md)
