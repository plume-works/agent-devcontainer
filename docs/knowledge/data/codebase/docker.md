---
type: codebase
description: The four images built in sequence — ubuntu-ansible, the lifecycle-neutral agentdev-base, and its sibling runtimes agentdev-deploy and agentdev-devcontainer — and the scripts they bake.
source: docker
source_digest: sha256:79b0267b29d9d28fd2ba7fac1f7545cdffed3018d0b75388448292992e0ed691
verified:
  by: claude-code/opus-5.5
  at: 2026-10-29T21:16:01Z
stale_after: 2027-01-27
generated:
  by: claude-code/opus-5.5
  at: 2026-10-29T21:16:01Z
sources:
- id: code
  resource: docker
---

# Image build (Docker)

Four images, built in sequence: `docker/ansible/Dockerfile` turns `ubuntu:24.04`
into `ubuntu-ansible` (Ansible and its collections, locale);
`docker/base/agentdev-base.Dockerfile` provisions that base with the
[playbook](ansible.md), every capability on, into the lifecycle-neutral
`agentdev-base`; and two siblings derive from a supplied `agentdev-base` digest
— `docker/deploy/agentdev-deploy.Dockerfile`, the standalone single-project
runtime, and `docker/devcontainer/agentdev-devcontainer.Dockerfile`, the Dev
Container runtime. `docker/desktop/` holds the two scripts the base bakes.

## Public surface

- `docker/base/agentdev-base.Dockerfile` build args — `FROM_IMAGE:5`,
  `WORKSPACE_FOLDER:12`, `AGENTDEV_PLUGIN_VERSION:18`,
  `AGENTDEV_CATALOG_DIR:22`, `VALIDATE_AGENT_FILES_VERSION:29`,
  `PLAYWRIGHT_VERSION:33` (required; supplied by the image workflow)
- `docker/deploy/agentdev-deploy.Dockerfile` and
  `docker/devcontainer/agentdev-devcontainer.Dockerfile` build arg `FROM_IMAGE`,
  also recorded as the `org.opencontainers.image.base.name` label
- `docker/deploy/supervisord.conf` — the controller event listener and the
  twelve deploy programs; `docker/devcontainer/supervisord.conf` — the same
  listener and eight programs; each runs `runtime-supervisor.py exec <name>` and
  is baked to `/etc/agentdev/supervisord.conf`
- the `devcontainer.metadata` label on `agentdev-devcontainer` — the lifecycle
  commands, `waitFor`, privileged mode, the kept entrypoint, and the
  `/var/lib/docker` volume every descriptor selecting the image inherits
- `/etc/agentdev/hooks/{created,started,attached}.d/` — empty phase hook
  directories a derived image fills
- `docker/deploy/runtime.env.example` — every setting the root
  `compose.opencode.yml` interpolates, with the accepted boolean spellings, each
  limit's default, and the Claude Remote Control mode and spawn mode
- `docker/deploy/README.md` — the operator deployment guide for the root Compose
  files; not copied into the image
- `/entrypoint.sh`, `/start-xpra.sh`, the `gh` wrapper — the files a running
  container exposes; their contract is in [the image runtime
  interface](api-image-runtime.md)
- `docker/ansible/setup-ansible.sh` — pins Ansible `13.4.0` and installs the two
  collections

## How it works

The base Dockerfile bind-mounts the whole build context read-only at
`/provision`, `cd`s into it so `ansible.cfg` is found, and runs
`ansible-playbook ansible/playbooks/setup-dev.yml` with every `install_*` flag
and the catalog, validator, and Playwright pins as extra vars; the workflow
reads the Playwright pin from the role default before the build. None of the
provisioning sources land in a layer. It then exports `AGENTDEV_CATALOG_DIR` and
`PLAYWRIGHT_BROWSERS_PATH`, labels the image with all three versions, copies the
two `docker/desktop/` scripts, exposes `14500`, and sets the entrypoint, which
only `exec`s the default `bash` command. No runtime script is copied into it.

Both runtime images install apt `supervisor`, copy `.devcontainer/scripts/` to
`/opt/agentdev-runtime`, their own `supervisord.conf` and the firewall allowlist
to `/etc/agentdev/`, set their profile's `ENV`, and give
`runtime-supervisor.py run` as the entrypoint with a `runtime-health.sh ready`
healthcheck. Deploy also deletes the stock `ubuntu` account, relocates the
root-home `gh-stack` extension to `/usr/local/lib/agentdev/gh-stack`, sets the
`agent` identity, path, and uv `ENV`, exposes `4096` and `14500`, and allows a
10-minute start period. The Dev Container image instead creates the hook
directories, records a sorted `sha256sum` manifest of `/opt/agentdev-runtime` at
`/etc/agentdev/runtime.sha256`, runs as `root`, embeds the
`devcontainer.metadata` label, and allows 5 minutes. `.dockerignore` reopens
only `.devcontainer/scripts` and the allowlist for the two runtime builds.

`start-xpra.sh` serves the HTML5 client on container port `14500` unless
`--port` overrides it, clears a stale display lock, and supports `--background`,
`--stop`, and `--supervised`. A nonempty `XPRA_PASSWORD` adds
`--tcp-auth=env:name=XPRA_PASSWORD`, so every TCP/WebSocket session must
authenticate and the secret stays off the command line. `--supervised` fails
when `xpra` is missing or a session is already live, stops a previous Xpra's
leftover X server, and execs a foreground `xpra start`. The `gh` wrapper finds
the real `gh` by walking `PATH` and skipping every copy of itself, derives
`GH_TOKEN` from the host's git credential helper when no token is set, and
`exec`s, with a re-entrancy guard for the two copies that can share a `PATH`.

## Depends on

[ansible/](ansible.md) for everything installed; [the docker composite
actions](github/actions.md) for the CI build; the
[catalog](agents/plugins/agentdev.md) and
[validator](py_packages/validate_agent_files.md) sources, which the playbook
copies out of `/provision`; [the lifecycle scripts](devcontainer/scripts.md),
which both runtime images bake.

## Invariants & gotchas

- Every `FROM_IMAGE` default is tag-only by design; CI overrides each with the
  digest built in the same run. A digest here would make Renovate bump a file
  under `docker/**`, which matches the image path filter and rebuilds the image
  that produced the digest, forever.
- The three version args are verified pins: the playbook fails when the staged
  catalog, installed validator, or Playwright CLI reports a different version.
  The base Dockerfile also rejects an omitted Playwright build argument.
- The build context is the repository root, never a `docker/` subdirectory.
- `runtime-bootstrap.sh` fails startup when a file below `/opt/agentdev-runtime`
  differs from, or is added to or missing from, the image's manifest, so a
  derived image extends the runtime only through the hook directories and
  documented environment.

## Key references

Verified anchor points (line numbers as of 2026-10-29):

- `docker/base/agentdev-base.Dockerfile:45-68` — provisioning and required
  Playwright version
- `docker/base/agentdev-base.Dockerfile:75-82` — `ENV` and version labels
- `docker/base/agentdev-base.Dockerfile:87-97` — scripts, port, entrypoint
- `docker/deploy/agentdev-deploy.Dockerfile:11` — supervisor, account removal,
  `gh-stack` relocation; `:22-24` — baked runtime files; `:28` — runtime `ENV`;
  `:57-65` — ports, healthcheck, entrypoint
- `docker/devcontainer/agentdev-devcontainer.Dockerfile:9` — supervisor and hook
  directories; `:19-25` — baked runtime and its manifest; `:29` — profile `ENV`;
  `:41-50` — `devcontainer.metadata`; `:57-61` — healthcheck, entrypoint
- `docker/deploy/supervisord.conf:24` — the controller; `:37-225` — the twelve
  programs, `:211` — `remote-control`
- `docker/devcontainer/supervisord.conf:24` — the controller; `:37-161` — the
  eight programs, `:115` — `created`
- `.devcontainer/scripts/runtime-bootstrap.sh:176-186` — `verify_runtime_root`,
  the manifest check
- `docker/ansible/setup-ansible.sh:4` — `ANSIBLE_VERSION`
- `docker/desktop/start-xpra.sh:7` — default HTML5 container port
- `docker/desktop/start-xpra.sh:175-183` — `--port` override
- `docker/desktop/start-xpra.sh:285-287` — `XPRA_PASSWORD` session auth
- `docker/desktop/start-xpra.sh:74` — `reclaim_orphaned_display`; `:320` — the
  supervised `exec`
- `docker/bin/gh:58-62` — `GH_TOKEN` from `git credential fill`
- `docker/bin/gh:51` — re-entrancy `exec`
