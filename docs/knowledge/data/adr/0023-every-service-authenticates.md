---
type: adr
stage: accepted
description: OpenCode and Xpra in the standalone runtime each require their own password, because each peer on the shared proxy network can reach their ports.
---

# Each service authenticates on its own

Many containers use the proxy network, so each peer on it can connect to the
ports of the container. The proxy cannot be the only access boundary. OpenCode
requires `OPENCODE_SERVER_PASSWORD`. Xpra requires `XPRA_PASSWORD` through its
`env` module, which keeps the secret off the command line.

## Considered Options

- Require `ENABLE_FIREWALL` with trusted proxy CIDRs when Xpra runs. Rejected:
  desktop access then depends on the opt-in egress firewall.
- Tell operators that the proxy network must have no other members. Rejected:
  the default deployment then stays open.

## Consequences

- Dev Container and Coder starts bind Xpra to the loopback address, so they need
  no Xpra password. The check applies only to the standalone runtime.
