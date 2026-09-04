---
type: architecture
description: The Docker MCP gateway runs as a profile-gated Compose sidecar reached over SSE on the private network, rather than as a stdio bridge, and host secrets arrive by mounting the host's secrets-engine socket instead of copying secrets into the container.
generated:
  by: claude-code/opus-5
  at: 2026-09-04T00:00:00Z
sources:
- resource: .devcontainer/docker-compose.yml
- resource: .devcontainer/devcontainer-init.sh
- resource: .mcp.json
- resource: https://github.com/Dr-QP/Dr.QP/pull/403
- resource: https://github.com/Dr-QP/Dr.QP/pull/404
- resource: https://github.com/Dr-QP/Dr.QP/pull/338
---

# MCP gateway transport

## Decision

The Docker MCP gateway runs as a **Compose sidecar**, not as a process the MCP
client spawns. Clients reach it over SSE at `http://mcp-gateway:8811/sse`, by
Compose service name on the private network.

The service is gated behind the `mcp` Compose profile, which
`devcontainer-init.sh` activates only when `~/.docker/mcp` exists on the host.
Host secrets reach the gateway by **bind-mounting the host's
`docker-secrets-engine` socket**; nothing exports, re-encrypts, or imports
secrets into the container.

## Why a sidecar over SSE rather than a stdio bridge

A client that spawns `docker mcp gateway run` itself owns the gateway's startup,
and that startup races Docker Desktop's per-container DNS proxy attaching. As a
service, the gateway's entrypoint polls DNS before exec'ing, so it cannot lose
that race.

`--allow-unauthenticated` is safe **because** of the transport choice: the
gateway is published only on the private Compose network under its service name
and is not exposed publicly. The flag would not be defensible on a bridge that
listened more broadly.

## Why the socket is mounted rather than the secrets copied

Docker Desktop resolves MCP secrets through host-native integrations that do not
exist inside a Linux container. Reproducing them in-container means a CLI plugin
built from source, a Secret Service backend, and scripts that export secrets
from the host, pass them in, and import them.

Mounting the host socket read-only replaces all of it. Secrets stay on the host
and are resolved across the socket, so no copy of a secret is ever written
inside the container.

## The stub-socket requirement

Compose bind-mounts a **directory** when the source path does not exist. For a
socket mount that is silently wrong, so `devcontainer-init.sh` pre-creates a
stub file at the fallback path. The mount then attaches a file whether or not
the real socket is present, and a host without Docker Desktop starts cleanly
instead of failing on a type mismatch.

## Consequences

- A host without `~/.docker/mcp` starts only the devcontainer service, with no
  gateway and no error.
- Adding an MCP client means pointing it at the service name, not at a command.
- The gateway's availability is a property of the host, so a workflow that needs
  MCP tools cannot assume the sidecar is running.
