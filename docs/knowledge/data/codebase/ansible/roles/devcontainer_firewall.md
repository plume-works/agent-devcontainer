---
type: codebase
description: Installs the egress firewall script and its sudoers entry into the image; the script stays inert until a container start enables it.
source: ansible/roles/devcontainer_firewall
source_digest: sha256:af9517b455b1732d95b1e6202b3fcd64ce9351309f61eca03addb61f50328820
verified:
  by: claude-code/opus-5
  at: 2026-09-22T00:00:00Z
stale_after: 2026-12-21
generated:
  by: claude-code/opus-5
  at: 2026-09-22T00:00:00Z
sources:
- id: code
  resource: ansible/roles/devcontainer_firewall
---

# devcontainer_firewall role

Places `init-firewall.sh` at `/usr/local/bin` with a NOPASSWD sudoers entry and
installs the iptables/ipset tooling it needs. Nothing here runs at build time or
on a plain container start.

## Public surface

- `/usr/local/bin/init-firewall.sh` — the script the runtime gate invokes
- `FIREWALL_ALLOWLIST` (env) — overrides the allowlist path; default
  `$DEV_WORKSPACE_FOLDER/.devcontainer/firewall-allowlist.txt`
- The allowlist format: `github-meta`, one domain per line, `#` comments

## How it works

`init-firewall.sh` records Docker's embedded DNS rules, flushes iptables and
ipsets, resolves each allowlist line (`github-meta` expands to the ranges from
`api.github.com/meta`, other lines to their DNS answers) into an ipset, sets
`INPUT`/`FORWARD`/`OUTPUT` to `DROP` for IPv4, blocks IPv6 entirely, and
self-verifies at the end.

## Depends on

The allowlist lives in the workspace
([.devcontainer/firewall-allowlist.txt](../../devcontainer.md)) so it is
branch-editable without a rebuild; the gate that decides whether to run at all
is [firewall.sh](../../devcontainer/scripts.md) reading `ENABLE_FIREWALL`.

## Invariants & gotchas

- Installed but inert: `install_devcontainer_firewall` only places files;
  `ENABLE_FIREWALL=true` applies them — the constraint recorded in
  `data/product.md`.
- The script is adapted from the Claude Code reference devcontainer firewall;
  the allowlist indirection is the local addition.
- The iptables/ipset packages install at pinned versions from
  `vars/apt_pins_<suite>_<arch>.yml`, like every other apt install in the play.

## Key references

Verified anchor points (line numbers as of 2026-09-22):

- `ansible/roles/devcontainer_firewall/tasks/main.yml:6-11` — the pinned apt
  install
- `ansible/roles/devcontainer_firewall/tasks/main.yml:13` — install the script
- `ansible/roles/devcontainer_firewall/tasks/main.yml:21` — sudoers entry
- `ansible/roles/devcontainer_firewall/files/init-firewall.sh:14` — allowlist
  path resolution
- `ansible/roles/devcontainer_firewall/files/init-firewall.sh:76` —
  `github-meta` expansion
- `ansible/roles/devcontainer_firewall/files/init-firewall.sh:123-126` — default
  DROP
- `ansible/roles/devcontainer_firewall/files/init-firewall.sh:143` — IPv6 block
