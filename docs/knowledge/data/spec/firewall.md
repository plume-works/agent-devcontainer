---
type: spec
description: The opt-in egress firewall's default-DROP policy and its self-verification check.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/firewall.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py
- resource: README.md
---

# Firewall

## Rationale

### The firewall is applied before the engine starts

The bootstrap applies the firewall as root before supervisord starts `dockerd`,
because applying the rules flushes the tables: run first, the flush leaves the
rules the engine installs at its own start in place, and running as root at
bootstrap needs no sudoers entry.

Rejected:

- **Applying the firewall from a supervised program after `dockerd`** — the
  flush would remove the engine's rules.
