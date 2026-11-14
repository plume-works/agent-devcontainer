---
type: spec
description: Xpra uses a fixed container port while VS Code handles local port conflicts.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/xpra.py
- resource: .devcontainer/devcontainer.json
- resource: README.md
- resource: https://github.com/devcontainers/spec/blob/main/docs/specs/devcontainerjson-reference.md#port-attributes
---

# Xpra port forwarding

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

## Rationale

### One fixed container port, forwarded explicitly

Separate devcontainers have separate network namespaces, so each can listen on
the same container port, and a local-port conflict is VS Code's to resolve
because the Dev Container specification defaults `requireLocalPort` to false.
The port is listed in `forwardPorts` so Xpra's availability does not depend on
VS Code detecting the process. A second Xpra server in the same namespace takes
an explicit `--port`.

Rejected:

- **A port derived from a hash of `DEVCONTAINER_ID`.** Isolated containers do
  not need distinct ports, and a hash over 100 values cannot guarantee
  uniqueness anyway.
- **Relying on VS Code's process auto-detection.** Xpra would be reachable only
  when detection notices it.
- **Publishing the port on the Docker host.** VS Code forwarding reaches it
  without a host port, and a fixed host port would collide between
  devcontainers.
