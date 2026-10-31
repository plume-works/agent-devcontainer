---
type: architecture
description: agentdev-devcontainer owns the Dev Container lifecycle and its supervised services, so a repository references or derives from the image instead of copying lifecycle scripts; consumers extend it only through hook directories and documented environment.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T04:32:14Z
sources:
- resource: docker/base/agentdev-base.Dockerfile
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/devcontainer/supervisord.conf
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: py_packages/agentdev_runtime/agentdev_runtime/supervisor.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/hooks.py
- resource: .devcontainer/devcontainer.json
- resource: scripts/tests/test_agentdev_devcontainer_image.py
- resource: scripts/tests/test_template_consume_migration.py
---

# Dev Container runtime

## Image family

`ubuntu-ansible` is the Ansible-ready base. `agentdev-base` adds the tools, the
staged catalog at `/opt/agentdev`, and the validators, and starts no service:
its entrypoint is a plain shell. Two sibling runtimes derive from the exact
`agentdev-base` digest built in the same CI run:

- `agentdev-deploy` runs one project with no Dev Containers client (see
  [Standalone OpenCode runtime](standalone-opencode-runtime.md)).
- `agentdev-devcontainer` is the Dev Container runtime this document describes.

Both install the `agentdev_runtime` package as a uv tool, the image-owned
runtime that `/usr/local/bin/agentdev-runtime` runs, and run
`agentdev-runtime supervisor run` as PID 1.

The old `agent-desktop` and `agent-opencode` names are not published as aliases.
`agent-desktop` would have to name the lifecycle-neutral base, which cannot run
the new descriptor, so a consumer needs the same migration either way and an
alias only adds a second name to maintain. Full-adoption consumers move through
`/agentdev:template-consume` update mode instead.

## Profiles

`AGENTDEV_RUNTIME_MODE` selects one supervisor profile per image; both share the
service adapters, dependency ordering, health probes, bounded recovery, and
shutdown. The devcontainer profile makes `dbus`, `keyring`, `dockerd`, `cbm`,
and `xpra` core. `opencode` and `remote-control` are opt-in clients that wait
for the `created` one-shot, which only waits for the create phase to finish.

A latched failure ends a Dev Container, where a deploy container stays up for an
explicit retry: an editor has no retry command, and a container that keeps
running with withdrawn readiness looks attached and healthy.

## Lifecycle ownership

PID 1 owns the persistent services. Work whose timing PID 1 cannot observe stays
in three thin image commands, declared in the image's `devcontainer.metadata`
label so every descriptor that selects the image inherits them:

| Phase               | Command                               | Runs                                                                                           |
| ------------------- | ------------------------------------- | ---------------------------------------------------------------------------------------------- |
| `postCreateCommand` | `agentdev-runtime lifecycle created`  | Once per container: client state, project dependencies and hooks, the staged catalog.          |
| `postStartCommand`  | `agentdev-runtime lifecycle ready`    | Every start: waits for the core services, repairs per-start state. It is the `waitFor` target. |
| `postAttachCommand` | `agentdev-runtime lifecycle attached` | Every attach: CBM index request, project environment, a complete checkout catalog.             |

The editor therefore never attaches to a container whose required services
failed. The label also sets `overrideCommand: false`, so the client keeps the
entrypoint, and mounts a per-container volume at `/var/lib/docker`, which the
nested engine needs because it refuses the container's own overlay. A descriptor
that declares the same commands runs each twice.

## Customization interface

A consumer extends the runtime in two ways only:

- **Hooks.** Executable files in
  `/etc/agentdev/hooks/{created,started,attached}.d/` run in C-locale name order
  at the end of their phase; a failing hook fails the phase. Hooks come from the
  image: a hook directory inside the workspace is refused, so a mounted
  repository cannot inject one by name.
- **Environment.** The image's documented defaults (`AGENTDEV_USER`, `DISPLAY`,
  `DOCKER_HOST`, the `AGENTDEV_*` budgets and timeouts, and the rest of its
  `ENV`) can be overridden in the descriptor or a derived image.

The bootstrap checks `/opt/agentdev-runtime/` against the build-time manifest
`/etc/agentdev/runtime.sha256` at every start and refuses a changed, added, or
removed file. A derived image that rewrites a managed script would otherwise
keep running a lifecycle no one tested.

## Adoption modes

- **Direct.** A descriptor references the image by tag and digest and keeps
  mounts, workspace selection, editor customization, and its own descriptor
  commands. It copies no lifecycle script.
- **Derived.** A custom image starts `FROM agentdev-devcontainer` (or from
  `agentdev-base` when it supplies no Dev Container runtime), adds tooling and
  hooks, and keeps the managed startup.
- **Full adoption.** `/agentdev:template-consume` copies the template's
  descriptor, Compose file, and workflows; it remains supported and uses the
  same published runtime.

This repository is a direct consumer whose checkout ships a complete catalog, so
the attach phase installs the checkout catalog over the staged one.

## Nested Docker

The supervised `dockerd` replaces the Docker-in-Docker Feature in the canonical
descriptor, so exactly one component starts and recovers the engine. See [Nested
Docker provisioning](nested-docker-provisioning.md).
