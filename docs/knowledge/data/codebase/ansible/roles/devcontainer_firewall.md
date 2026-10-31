---
type: codebase
description: Installs the iptables and ipset packages the runtime's egress firewall drives; nothing in the role applies a rule.
source: ansible/roles/devcontainer_firewall
source_digest: sha256:515a48efe072880cb57978b2bb39ae3e3468b3823f90259cae95452e5265d2c8
verified:
  by: claude-code/opus-5.5
  at: 2026-10-31T04:38:23Z
stale_after: 2027-01-29
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T04:38:23Z
sources:
- id: code
  resource: ansible/roles/devcontainer_firewall
---

# devcontainer_firewall role

One apt task: `iptables` and `ipset`. The policy itself is
`agentdev-runtime firewall apply` in the [agentdev_runtime
package](../../py_packages/agentdev_runtime.md), which the runtime bootstrap
runs as root when `ENABLE_FIREWALL=true`.

## Public surface

- The `iptables` and `ipset` binaries on the image.

## Depends on

Selected by `install_devcontainer_firewall`, which `agentdev-base` turns on and
`group_vars/all.yml` leaves off.

## Invariants & gotchas

- Installing the packages enables nothing; the runtime applies rules only when
  `ENABLE_FIREWALL=true`.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `ansible/roles/devcontainer_firewall/tasks/main.yml:3` — the apt install
- `ansible/playbooks/setup-dev.yml:41` — the role's `when:` gate
- `docker/base/agentdev-base.Dockerfile:58` —
  `install_devcontainer_firewall=true`
