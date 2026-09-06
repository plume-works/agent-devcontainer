---
type: spec
description: Xpra uses a fixed container port while VS Code handles local port conflicts.
generated:
  by: codex/gpt-6
  at: 2026-09-06T04:26:49Z
sources:
- resource: docker/desktop/start-xpra.sh
- resource: .devcontainer/devcontainer.json
- resource: README.md
---

# Xpra port forwarding

## Requirement: Xpra has a fixed default container port

The startup script SHALL use TCP port 14500 by default, independently of
`DEVCONTAINER_ID`, and SHALL honor an explicit `--port` argument.

### Scenario: default startup

- **WHEN** Xpra starts without `--port`, with `DEVCONTAINER_ID` either unset or
  set
- **THEN** it listens on container port 14500.

### Scenario: explicit override

- **WHEN** Xpra starts with `--port 14600` and `DEVCONTAINER_ID` is set
- **THEN** it listens on container port 14600.

## Requirement: devcontainer forwarding permits local remapping

The default devcontainer configuration SHALL explicitly forward container port
14500, label it Xpra HTML5, use silent forwarding, and permit a different local
port when the preferred port is unavailable. Browser access instructions SHALL
direct users to the actual forwarded address in VS Code's Ports panel.

### Scenario: concurrent devcontainers

- **WHEN** two isolated devcontainers run Xpra on port 14500 and both are opened
  in VS Code on the same client machine
- **THEN** both desktops are accessible through their respective forwarded local
  addresses, without requiring distinct container ports.
