---
type: bug
description: When ENABLE_FIREWALL is true and ip6tables is not available, the firewall writes a warning and applies no IPv6 rule, so IPv6 egress goes past the allowlist.
stage: pending
severity: high
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/firewall.py
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
- resource: docs/spec-audit/requirements.jsonl
---

# Bug: the enabled firewall leaves IPv6 open when `ip6tables` is missing

## Symptom

With `ENABLE_FIREWALL=true`, the firewall must block IPv6 fully. When the
container has no `ip6tables`, `agentdev-runtime firewall apply` writes "WARNING:
ip6tables not available; IPv6 traffic is not restricted" and continues. The
self-verification passes, because it does only IPv4 probes. A process can then
send IPv6 traffic to a host that is not on the allowlist.

## Reproduction

1. Start a container with `ENABLE_FIREWALL=true` in which `ip6tables` is not on
   `PATH`, and that has an IPv6 route.
2. The start log shows the warning, and the firewall verification passes.
3. A request over IPv6 to a host that is not on the allowlist gets an answer.

## Root cause

`py_packages/agentdev_runtime/agentdev_runtime/firewall.py::block_ipv6` returns
after the warning when `system.has('ip6tables')` is false. It does not fail the
start.

## Potential solution

Make `firewall apply` fail when IPv6 cannot be blocked and the container has an
IPv6 route.
