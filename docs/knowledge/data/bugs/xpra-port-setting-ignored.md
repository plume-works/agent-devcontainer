---
type: bug
stage: pending
severity: low
description: AGENTDEV_XPRA_PORT moves the Xpra health probe and the firewall's proxy-ingress rule but not the port Xpra listens on.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/settings.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/xpra.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/health.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/firewall.py
- resource: docs/knowledge/data/spec/xpra-port-forwarding.md
---

# Bug: AGENTDEV_XPRA_PORT does not change the port Xpra listens on

## Symptom

`py_packages/agentdev_runtime/agentdev_runtime/settings.py` declares
`AGENTDEV_XPRA_PORT` as "Xpra port." with default `14500`. With it set to
another port, Xpra still listens on 14500, the Xpra health probe requests the
other port and fails, and in the deploy profile the firewall admits the trusted
proxy to the other port instead of 14500. [Xpra port
forwarding](../spec/xpra-port-forwarding.md) fixes the port at 14500 with
`--port` as the only override and does not mention the variable.

## Reproduction

1. With `AGENTDEV_XPRA_PORT=15000` in the environment,
   `agentdev_runtime.xpra.parse([]).port` is `14500` while
   `agentdev_runtime.settings.Settings().get('AGENTDEV_XPRA_PORT')` is `15000`.
2. `docker/deploy/supervisord.conf` and `docker/devcontainer/supervisord.conf`
   start `agentdev-runtime xpra --supervised` with no `--port`.

## Root cause

`py_packages/agentdev_runtime/agentdev_runtime/xpra.py::parse` takes its port
from `--port` with the constant `DEFAULT_PORT` in
`py_packages/agentdev_runtime/agentdev_runtime/xpra.py` as default and never
reads the setting. The Xpra branch of the service probe in
`py_packages/agentdev_runtime/agentdev_runtime/health.py` and
`py_packages/agentdev_runtime/agentdev_runtime/firewall.py::apply` both read
`AGENTDEV_XPRA_PORT`. The variable has consumers and no producer.

## Potential solution

Remove `AGENTDEV_XPRA_PORT` and have
`py_packages/agentdev_runtime/agentdev_runtime/health.py` and
`py_packages/agentdev_runtime/agentdev_runtime/firewall.py::apply` use the port
constant from `py_packages/agentdev_runtime/agentdev_runtime/xpra.py`, which
keeps the port fixed as the spec states.

## Key references

- `py_packages/agentdev_runtime/agentdev_runtime/xpra.py::parse`
- `py_packages/agentdev_runtime/agentdev_runtime/settings.py` ›
  `Variable('AGENTDEV_XPRA_PORT', 'Xpra port.', '14500')`
- `py_packages/agentdev_runtime/agentdev_runtime/firewall.py::apply`
- `docker/deploy/supervisord.conf` › `[program:xpra]`
