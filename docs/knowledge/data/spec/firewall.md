---
type: spec
description: The opt-in egress firewall's default-DROP policy and its self-verification check.
generated:
  by: claude-sonnet-5
  at: 2026-08-12T00:00:00Z
sources:
- ansible/roles/devcontainer_firewall/files/init-firewall.sh
- README.md
---

# Firewall

## Requirement: the firewall is inert unless explicitly enabled

`init-firewall.sh` SHALL take no effect unless `ENABLE_FIREWALL=true` is set in
`containerEnv`; the script and its NOPASSWD sudoers entry are installed in the
image regardless, but do nothing by default.

### Scenario: a devcontainer starts with no `ENABLE_FIREWALL` set

- **WHEN** the container starts
- **THEN** no egress restriction is applied.

## Requirement: enabled firewall default-DROPs IPv4 and blocks IPv6 entirely

When enabled, `init-firewall.sh` SHALL set IPv4 `INPUT`/`FORWARD`/`OUTPUT`
policies to `DROP` and block IPv6 entirely, while preserving Docker's embedded
DNS NAT rules and allowing only hosts on `.devcontainer/firewall-allowlist.txt`
(read at container start, so per-branch edits take effect on next start with no
image rebuild).

### Scenario: a host not on the allowlist is requested

- **WHEN** code in the container tries to reach a non-allowlisted host
- **THEN** the connection is dropped.

## Requirement: the firewall self-verifies at start and fails loudly

`init-firewall.sh` SHALL check, immediately after applying rules, that a
known-blocked host (`example.com`) fails and that `https://api.github.com/zen`
succeeds — exiting non-zero if either check goes the wrong way, so a
misconfigured firewall never silently passes as "enabled" while actually open or
actually blocking required traffic.

### Scenario: the allowlist accidentally omits `api.github.com`

- **WHEN** `init-firewall.sh` runs its self-verification
- **THEN** the `api.github.com/zen` reachability check fails and the script
  exits non-zero, surfacing the misconfiguration at container start rather than
  as a later, harder-to-diagnose failure.

### Scenario: the DROP policy fails to apply

- **WHEN** `example.com` is still reachable after the rules are applied
- **THEN** the verification step exits non-zero.
