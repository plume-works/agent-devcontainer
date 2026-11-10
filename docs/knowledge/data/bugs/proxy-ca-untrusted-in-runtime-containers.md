---
type: bug
stage: done
severity: high
description: Behind a TLS-intercepting egress proxy, every TLS client inside the runtime containers rejected the proxy's certificates, so nested image pulls, uv sync, and package downloads failed.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/trust.py
- resource: .devcontainer/devcontainer-init.sh
- resource: docker/base/agentdev-base.Dockerfile
---

# Bug: runtime containers reject a TLS-intercepting proxy's certificates

## Symptom

On a host whose egress re-terminates TLS, such as a Claude Code cloud session:

- In `agentdev-devcontainer`, a nested pull fails:
  `tls: failed to verify certificate: x509: certificate signed by unknown authority`.
- In `agentdev-deploy`, the `project` step latches the runtime degraded:
  `uv sync` fails with `invalid peer certificate: UnknownIssuer`.

## Reproduction

1. On a host behind such a proxy, start either runtime image privileged.
2. Inside it, run `docker run --rm alpine:3.20 true` or `uv sync`; both fail as
   above.

## Root cause

The host trusts the proxy's CA, but nothing passed it to the container, whose
system store holds only the public roots. uv also ignores the system store
unless told otherwise.

## Fix

The root bootstrap installs the bundle at `AGENTDEV_EXTRA_CA_CERTS` into the
system store, `agentdev-base` points `SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, and
`NODE_EXTRA_CA_CERTS` at that store, and `devcontainer-init.sh` hands the host's
bundle to the Dev Container. Design: [Extra CA
trust](../../../../openspec/specs/agentdev-runtime-images/spec.md#rationale).
