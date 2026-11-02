---
type: spec
description: The opt-in egress firewall's default-DROP policy and its self-verification check.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T20:55:00Z
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/firewall.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py
- resource: README.md
---

# Firewall

## Requirement: the firewall is inert unless explicitly enabled

`agentdev-runtime firewall apply` SHALL apply egress rules only when
`ENABLE_FIREWALL` is `true`. The runtime's bootstrap SHALL run it as root before
supervisord starts, in both profiles, so no sudoers entry is needed, and with
any other value it SHALL report that the firewall stays inert and exit 0.

### Scenario: a container starts with no `ENABLE_FIREWALL` set

- **WHEN** the container starts
- **THEN** no egress restriction is applied.

## Requirement: enabled firewall default-DROPs IPv4 and blocks IPv6 entirely

When enabled, `agentdev-runtime firewall apply` SHALL set IPv4
`INPUT`/`FORWARD`/`OUTPUT` policies to `DROP` and block IPv6 entirely, while
preserving Docker's embedded DNS NAT rules and allowing only hosts on the
allowlist. When `FIREWALL_ALLOWLIST` is set, both profiles SHALL read the file
it names. Otherwise the devcontainer profile SHALL read
`<workspace>/.devcontainer/firewall-allowlist.txt` when it exists, so per-branch
edits take effect on the next start without an image rebuild, and
`/etc/agentdev/firewall-allowlist.txt` otherwise; the deploy profile SHALL read
the image copy.

### Scenario: a host not on the allowlist is requested

- **WHEN** code in the container tries to reach a non-allowlisted host
- **THEN** the connection is dropped.

### Scenario: the checkout edits its allowlist

- **WHEN** a devcontainer restarts after `.devcontainer/firewall-allowlist.txt`
  changed in the checkout
- **THEN** the new allowlist is in force without an image rebuild.

### Scenario: `FIREWALL_ALLOWLIST` is set in a devcontainer

- **WHEN** a devcontainer starts with `FIREWALL_ALLOWLIST` naming a file and a
  checkout allowlist present
- **THEN** the firewall applies the file `FIREWALL_ALLOWLIST` names.

## Requirement: the firewall self-verifies at start and fails loudly

`agentdev-runtime firewall apply` SHALL check, immediately after applying rules,
that a known-blocked host (`example.com`) fails and that
`https://api.github.com/zen` succeeds, exiting non-zero if either check goes the
wrong way, so a misconfigured firewall never silently passes as enabled while
actually open or actually blocking required traffic.

### Scenario: the allowlist accidentally omits `api.github.com`

- **WHEN** the self-verification runs
- **THEN** the `api.github.com/zen` reachability check fails and the command
  exits non-zero, surfacing the misconfiguration at container start.

### Scenario: the DROP policy fails to apply

- **WHEN** `example.com` is still reachable after the rules are applied
- **THEN** the verification step exits non-zero.
