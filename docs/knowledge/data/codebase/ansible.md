---
type: codebase
description: The Ansible playbook and roles that provision the agent-desktop image from an Ubuntu base; capability roles are opt-in and the desktop Dockerfile turns them all on.
source:
- ansible
- ansible.cfg
source_digest: sha256:a732098f2be585972525dacdf5804f37acd19a49f06ef07f9f13125ef9c4e3ca
verified:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
stale_after: 2026-12-03
generated:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
sources:
- id: code
  resource: ansible
---

# Image provisioning (Ansible)

`ansible/playbooks/setup-dev.yml` provisions an Ubuntu 24.04 base into the
published `agent-desktop` image. Every capability role is a boolean in
`ansible/playbooks/group_vars/all.yml`, `false` by default, and
[the desktop Dockerfile](docker.md) passes them all as `true`. `ansible.cfg`
sits at the repository root so `ansible-playbook`, `ansible-lint`, and the
Dockerfile's `cd /provision` all resolve the inventory, roles path, and log path
from there.

## Contains

[agentic_tools](ansible/roles/agentic_tools.md)

[dev_tools](ansible/roles/dev_tools.md)

[perm_probe](ansible/roles/perm_probe.md)

[devcontainer_firewall](ansible/roles/devcontainer_firewall.md)

[xpra_setup](ansible/roles/xpra_setup.md)

[validate_agent_files](ansible/roles/validate_agent_files.md)

Roles that are one task file plus a README, *not mapped*: `basic_prereqs` (apt
essentials, GNOME Keyring, sshd, universe repo), `extra_facts` (`system_arch`,
`user_home`), `locale_setup`, `utc_timezone`, `fish_setup` (fisher, bass,
`conf.d/dev.fish`), `bash_setup`, `cmake_kitware`, `github_cli`, `bun_setup`,
`nodejs` (NodeSource 24), `uv_setup`, `install_docker`,
`install_docker_service`.

## Public surface

- `ansible/playbooks/setup-dev.yml` — the one playbook; `hosts: all` against the
  `localhost` inventory, `become: true`
- `install_xpra`, `install_docker`, `install_agentic_tools`,
  `install_validate_agent_files`, `install_devcontainer_firewall`,
  `workspace_folder` — `ansible/playbooks/group_vars/all.yml:5-24`
- Per-role `agentic_tools_*` and `validate_agent_files_*` variables, passed by
  the Dockerfile as `-e` extra vars
- Role tags matching role names, plus `always` on the guards

## How it works

The play runs the roles in a fixed order with three ordering constraints:
`bun_setup` precedes `nodejs` and `agentic_tools` because both install global
packages through `bun add --global`; `validate_agent_files` follows `uv_setup`
because the validator is installed as a uv tool; and `perm_probe` runs first
(`pre-check`) and last (`final`) with `perm_probe_fail_on_drift: true`, so a
role that hands `/usr/local` to a non-root owner fails the build instead of
shipping.

## Depends on

The `ubuntu-ansible` base image from [docker/](docker.md) supplies Ansible
13.4.0 and the `community.general` and `community.docker` collections
(`ansible/requirements.yml`). Locally, `uv run ansible-lint ansible` and
`uv run ansible-playbook --syntax-check` come from the `dev` dependency group.

## Invariants & gotchas

- Run every Ansible command from the repository root; `ansible.cfg` is only
  auto-loaded from the current directory.
- Capability roles default off. A leaner image is a different set of `-e` flags,
  not a different playbook.
- The `final` perm probe is a build guard, not diagnostics: an ownership drift
  baked into the published image is inherited by every warm build layered on it,
  which is why it fails the play.

## Key references

Verified anchor points (line numbers as of 2026-09-04):

- `ansible/playbooks/setup-dev.yml:18` — `perm_probe` pre-check guard
- `ansible/playbooks/setup-dev.yml:28` — `dev_tools`
- `ansible/playbooks/setup-dev.yml:36-40` — the opt-in capability roles and the
  final guard
- `ansible.cfg:5-8` — inventory, log path, roles path
- `ansible/playbooks/group_vars/all.yml:5-24` — the capability booleans
