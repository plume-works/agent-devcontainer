---
type: bug
stage: pending
severity: low
description: The firewall spec misstates which ENABLE_FIREWALL values enable the firewall, which destinations the policy admits, and how a blocked connection fails.
sources:
- resource: docs/knowledge/data/spec/firewall.md
- resource: py_packages/agentdev_runtime/agentdev_runtime/firewall.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/supervisor.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/settings.py
---

# Bug: the firewall spec misstates the enabled policy

## Symptom

[Firewall](../spec/firewall.md) differs from the code in four places:

- It enables the firewall only for `ENABLE_FIREWALL=true` and calls every other
  value inert with exit 0. At container start `1`, `yes`, and `on` enable it
  too, and an unrecognised value is a configuration error.
- It admits only hosts on the allowlist. The policy also accepts all traffic to
  and from the default gateway, which is the Docker host.
- Its scenario says a connection to a host off the allowlist is dropped. The
  connection is rejected with `icmp-admin-prohibited` and fails at once.
- It is silent on the deploy profile, where the firewall refuses to start
  without `AGENTDEV_TRUSTED_PROXY_CIDRS`, admits those sources to the OpenCode
  and Xpra ports, and applies the allowlist again to nested containers.
  [Standalone OpenCode runtime](../spec/standalone-opencode-runtime.md) covers
  this in one clause with no scenario.

## Reproduction

1. Read `py_packages/agentdev_runtime/agentdev_runtime/supervisor.py::run`: it
   sets `ENABLE_FIREWALL` to `true` whenever
   `py_packages/agentdev_runtime/agentdev_runtime/settings.py::Settings.boolean`
   accepts the value, before the bootstrap calls
   `py_packages/agentdev_runtime/agentdev_runtime/firewall.py::apply`.
2. Read
   `py_packages/agentdev_runtime/agentdev_runtime/firewall.py::apply_policy`: it
   appends `ACCEPT` rules for the gateway address on `INPUT` and `OUTPUT`, and
   ends `OUTPUT` with `REJECT --reject-with icmp-admin-prohibited`.
3. Read `py_packages/agentdev_runtime/agentdev_runtime/firewall.py::apply`: in
   the deploy profile it calls
   `py_packages/agentdev_runtime/agentdev_runtime/firewall.py::proxy_cidrs`,
   `py_packages/agentdev_runtime/agentdev_runtime/firewall.py::allow_proxy_ingress`,
   and, in both profiles,
   `py_packages/agentdev_runtime/agentdev_runtime/firewall.py::filter_nested_egress`.

## Root cause

The spec describes `agentdev-runtime firewall apply` as a standalone command
with one profile. The supervisor's normalisation of boolean settings, the
trusted-proxy ingress, and the nested-container filter were added to the code
without a matching requirement in the spec.

## Key references

- `py_packages/agentdev_runtime/agentdev_runtime/supervisor.py::run` ›
  `os.environ['ENABLE_FIREWALL']`
- `py_packages/agentdev_runtime/agentdev_runtime/firewall.py::apply_policy`
- `py_packages/agentdev_runtime/agentdev_runtime/firewall.py::apply`
- `docs/knowledge/data/spec/firewall.md#requirement-the-firewall-is-inert-unless-explicitly-enabled`
