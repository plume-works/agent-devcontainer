---
type: bug
stage: pending
severity: medium
description: With ip6tables absent, the enabled egress firewall warns, leaves IPv6 unrestricted, and still passes its self-verification.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/firewall.py
- resource: docs/knowledge/data/spec/firewall.md
---

# Bug: the enabled firewall leaves IPv6 open when ip6tables is missing

## Symptom

[Firewall](../spec/firewall.md) requires the enabled firewall to block IPv6
entirely and to fail loudly when it is misconfigured. On a system without
`ip6tables`, `agentdev-runtime firewall apply` prints
`WARNING: ip6tables not available; IPv6 traffic is not restricted`, applies the
IPv4 policy, passes its self-verification, and exits 0. IPv6 egress then
bypasses the allowlist.

## Reproduction

1. Call `agentdev_runtime.firewall.block_ipv6` with a `firewall.System` whose
   `has` returns `False`.
2. It prints the warning, runs no command, and returns without raising
   `FirewallError`.

## Root cause

`py_packages/agentdev_runtime/agentdev_runtime/firewall.py::block_ipv6` returns
after the warning when `ip6tables` is not on `PATH`, and
`py_packages/agentdev_runtime/agentdev_runtime/firewall.py::apply_policy` does
not check the outcome.
`py_packages/agentdev_runtime/agentdev_runtime/firewall.py::verify` probes
`https://example.com` and `https://api.github.com/zen` through
`System.reachable`, which never forces an address family, so it cannot detect
open IPv6 on a host whose blocked probe fails over IPv4.

## Potential solution

Raise `FirewallError` from
`py_packages/agentdev_runtime/agentdev_runtime/firewall.py::block_ipv6` when
`ip6tables` is missing, so
`py_packages/agentdev_runtime/agentdev_runtime/firewall.py::apply` exits 1.

## Key references

- `py_packages/agentdev_runtime/agentdev_runtime/firewall.py::block_ipv6`
- `py_packages/agentdev_runtime/agentdev_runtime/firewall.py::verify`
- `docs/knowledge/data/spec/firewall.md#requirement-enabled-firewall-default-drops-ipv4-and-blocks-ipv6-entirely`
