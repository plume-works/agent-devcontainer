---
type: adr
stage: accepted
description: OpenCode and Xpra in the standalone runtime each require their own password, because each peer on the shared proxy network can reach their ports.
---

# Each service authenticates on its own

The proxy network is shared, so any peer on it reaches the ports of the
container directly, and the proxy cannot be the only access boundary. OpenCode
requires `OPENCODE_SERVER_PASSWORD`. Xpra requires `XPRA_PASSWORD` through its
`env` module, which keeps the secret off the command line.

## Considered Options

- Require `ENABLE_FIREWALL` with trusted proxy CIDRs whenever Xpra runs.
  Rejected: it couples desktop access to the opt-in egress firewall.
- Document that the proxy network must have no other members. Rejected: it
  leaves the default deployment open.

## Consequences

- Dev Container and Coder starts bind Xpra to the loopback address, so they need
  no Xpra password. Only the standalone runtime requires `XPRA_PASSWORD`.
