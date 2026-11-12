---
type: bug
stage: pending
severity: medium
description: The firewall accepts wildcard allowlist entries as valid and then skips each one, so the hosts they name stay blocked.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/firewall.py
- resource: .devcontainer/firewall-allowlist.txt
---

# Bug: wildcard firewall allowlist entries never take effect

## Symptom

`.devcontainer/firewall-allowlist.txt` lists `*.gallery.vsassets.io` and
`*.gallerycdn.vsassets.io`. With the firewall enabled, the start log shows
`WARNING: Failed to resolve *.gallery.vsassets.io (skipping)` for each, and no
host under either domain is reachable. The allowlist validates cleanly, so
nothing reports the entries as unusable.

## Reproduction

1. Call `agentdev_runtime.firewall.add_entry` with a `firewall.System` whose
   `say` and `run` record their arguments, and the entry
   `*.gallery.vsassets.io`.
2. It says `Resolving *.gallery.vsassets.io...`, then
   `WARNING: Failed to resolve *.gallery.vsassets.io (skipping)`, and runs no
   `ipset add`.
3. `socket.getaddrinfo('x.gallery.vsassets.io', None, socket.AF_INET)` on the
   same machine returns addresses, so the failure is the literal `*` label.

## Root cause

`DOMAIN_RE` in `py_packages/agentdev_runtime/agentdev_runtime/firewall.py`
admits an optional leading `*.`, so
`py_packages/agentdev_runtime/agentdev_runtime/firewall.py::validate_allowlist`
accepts a wildcard entry.
`py_packages/agentdev_runtime/agentdev_runtime/firewall.py::add_entry` passes
the entry unchanged to `System.resolve`, which asks `socket.getaddrinfo` for a
host literally named `*.<domain>`. That name does not resolve, and an unresolved
entry is skipped with a warning. The policy is an `ipset` of IPv4 addresses
resolved once at apply time, which has no way to express every host under a
domain.

## Potential solution

Reject a wildcard entry in
`py_packages/agentdev_runtime/agentdev_runtime/firewall.py::validate_allowlist`,
and replace the two entries in `.devcontainer/firewall-allowlist.txt` with the
host names the extension gallery uses.

## Key references

- `py_packages/agentdev_runtime/agentdev_runtime/firewall.py::validate_allowlist`
- `py_packages/agentdev_runtime/agentdev_runtime/firewall.py::add_entry`
- `.devcontainer/firewall-allowlist.txt` › `*.gallery.vsassets.io`
