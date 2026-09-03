---
type: codebase
description: The two Dockerfiles that produce ubuntu-ansible and agent-desktop, plus the entrypoint, the Xpra start script, and the gh auth wrapper baked into the image.
source: docker
commit: eb60f60450c6009b076bc51993b49a924653eaa4
verified:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:04:51Z
stale_after: 2026-12-02
generated:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:04:51Z
sources:
- id: code
  resource: docker
  title: the code this map describes, read at commit eb60f60
---

# Image build (Docker)

Two images, built in sequence: `docker/ansible/Dockerfile` turns `ubuntu:24.04`
into `ubuntu-ansible` (Ansible and its collections, locale), and
`docker/desktop/agent-desktop.Dockerfile` provisions that base with the
[playbook](ansible.md), every capability on, and adds the runtime scripts.

## Public surface

- `docker/desktop/agent-desktop.Dockerfile` build args — `FROM_IMAGE:5`,
  `WORKSPACE_FOLDER:12`, `AGENTDEV_PLUGIN_VERSION:18`,
  `AGENTDEV_CATALOG_DIR:22`, `VALIDATE_AGENT_FILES_VERSION:29`
- `/entrypoint.sh`, `/start-xpra.sh`, the `gh` wrapper — the files a running
  container exposes; their contract is in
  [the image runtime interface](api-image-runtime.md)
- `docker/ansible/setup-ansible.sh` — pins Ansible `13.4.0` and installs the two
  collections

## How it works

The desktop Dockerfile bind-mounts the whole build context read-only at
`/provision`, `cd`s into it so `ansible.cfg` is found, and runs
`ansible-playbook ansible/playbooks/setup-dev.yml` with every `install_*` flag
and the catalog and validator pins as extra vars; none of the provisioning
sources land in a layer. It then exports `AGENTDEV_CATALOG_DIR`, labels the
image with both versions, copies the two scripts, exposes `14500`, and sets the
entrypoint, which only `exec`s the command.

`start-xpra.sh` derives the HTML5 port from `DEVCONTAINER_ID`
(`14500 + cksum % 100`) unless `--port` is explicit, clears a stale display
lock, and supports `--background` and `--stop`. The `gh` wrapper finds the real
`gh` by walking `PATH` and skipping every copy of itself, derives `GH_TOKEN`
from the host's git credential helper when no token is set, and `exec`s, with a
re-entrancy guard for the two copies that can share a `PATH`.

## Depends on

[ansible/](ansible.md) for everything installed;
[the docker composite actions](github/actions.md) for the CI build; the
[catalog](agents/plugins/agentdev.md) and
[validator](py_packages/validate_agent_files.md) sources, which the playbook
copies out of `/provision`.

## Invariants & gotchas

- `FROM_IMAGE` is tag-only by design; CI overrides it with the digest built in
  the same run. A digest here would make Renovate bump a file under `docker/**`,
  which matches the image path filter and rebuilds the image that produced the
  digest, forever.
- The two version args are verified pins: the playbook fails when the staged
  catalog or the installed validator reports a different version.
- The build context is the repository root, never `docker/desktop/`.

## Key references

Verified anchor points (line numbers as of 2026-09-03):

- `docker/desktop/agent-desktop.Dockerfile:41` — the provisioning `RUN`
- `docker/desktop/agent-desktop.Dockerfile:68-71` — `ENV` and version labels
- `docker/desktop/agent-desktop.Dockerfile:76-86` — scripts, port, entrypoint
- `docker/ansible/setup-ansible.sh:4` — `ANSIBLE_VERSION`
- `docker/desktop/start-xpra.sh:188-190` — per-devcontainer port derivation
- `docker/bin/gh:58-59` — `GH_TOKEN` from `git credential fill`
- `docker/bin/gh:51` — re-entrancy `exec`
