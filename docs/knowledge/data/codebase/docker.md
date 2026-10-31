---
type: codebase
description: The four images built in sequence — ubuntu-ansible, the lifecycle-neutral agentdev-base, and its sibling runtimes agentdev-deploy and agentdev-devcontainer — and the scripts they bake.
source: docker
source_digest: sha256:4d643c701a9f10408b028dac3ae63f76a5da77ea3d58949ec0b9e857749d4a5f
verified:
  by: claude-code/opus-5.5
  at: 2026-10-31T04:38:23Z
stale_after: 2027-01-29
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T04:38:23Z
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
Container runtime. `docker/desktop/entrypoint.sh` is the base image's
entrypoint.

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
  listener and eight programs; each runs
  `agentdev-runtime supervisor exec <name> agentdev-runtime …` and is baked to
  `/etc/agentdev/supervisord.conf`
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
- `/entrypoint.sh`, `agentdev-runtime` on the runtime images, the `gh` wrapper —
  the files a running container exposes; their contract is in [the image runtime
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
`PLAYWRIGHT_BROWSERS_PATH`, labels the image with all three versions, copies
`docker/desktop/entrypoint.sh`, exposes `14500`, and sets that entrypoint, which
only `exec`s the default `bash` command. No runtime code is installed in it.

Both runtime images install the [agentdev_runtime
package](py_packages/agentdev_runtime.md) with `uv tool install` from a writable
bind mount of `py_packages/agentdev_runtime`, into `/opt/uv-tools` with the
entry point on `/usr/local/bin`; copy their own `supervisord.conf` and the
firewall allowlist to `/etc/agentdev/`; set their profile's `ENV`; and give
`agentdev-runtime supervisor run` as the entrypoint with an
`agentdev-runtime health ready` healthcheck. Deploy also deletes the stock
`ubuntu` account, relocates the root-home `gh-stack` extension to
`/usr/local/lib/agentdev/gh-stack`, sets the `agent` identity, path, and uv
`ENV`, exposes `4096` and `14500`, and allows a 10-minute start period. The Dev
Container image instead creates the hook directories, runs as `root`, embeds the
`devcontainer.metadata` label, and allows 5 minutes. `.dockerignore` reopens
only the allowlist under `.devcontainer/` for the two runtime builds.

The `gh` wrapper finds the real `gh` by walking `PATH` and skipping every copy
of itself, derives `GH_TOKEN` from the host's git credential helper when no
token is set, and `exec`s, with a re-entrancy guard for the two copies that can
share a `PATH`.

## Depends on

[ansible/](ansible.md) for everything installed; [the docker composite
actions](github/actions.md) for the CI build; the
[catalog](agents/plugins/agentdev.md) and
[validator](py_packages/validate_agent_files.md) sources, which the playbook
copies out of `/provision`; the [agentdev_runtime
package](py_packages/agentdev_runtime.md), which both runtime images install.

## Invariants & gotchas

- Every `FROM_IMAGE` default is tag-only by design; CI overrides each with the
  digest built in the same run. A digest here would make Renovate bump a file
  under `docker/**`, which matches the image path filter and rebuilds the image
  that produced the digest, forever.
- The three version args are verified pins: the playbook fails when the staged
  catalog, installed validator, or Playwright CLI reports a different version.
  The base Dockerfile also rejects an omitted Playwright build argument.
- The build context is the repository root, never a `docker/` subdirectory.
- `agentdev-runtime bootstrap` fails startup when an installed package file
  differs from its `RECORD`, or one is added or missing, so a derived image
  extends the runtime only through the hook directories and documented
  environment.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `docker/base/agentdev-base.Dockerfile:45-68` — provisioning and required
  Playwright version
- `docker/base/agentdev-base.Dockerfile:75-82` — `ENV` and version labels
- `docker/base/agentdev-base.Dockerfile:87-93` — port, entrypoint script,
  entrypoint
- `docker/deploy/agentdev-deploy.Dockerfile:11` — account removal, `gh-stack`
  relocation; `:19` — the `agentdev_runtime` uv tool install; `:24-25` — baked
  configuration; `:29` — runtime `ENV`; `:58-65` — ports, healthcheck,
  entrypoint
- `docker/devcontainer/agentdev-devcontainer.Dockerfile:9` — hook directories;
  `:14` — the uv tool install; `:21-22` — baked configuration; `:26` — profile
  `ENV`; `:38-47` — `devcontainer.metadata`; `:54-57` — healthcheck, entrypoint
- `docker/deploy/supervisord.conf:24` — the controller; `:37-225` — the twelve
  programs, `:211` — `remote-control`
- `docker/devcontainer/supervisord.conf:24` — the controller; `:37-161` — the
  eight programs, `:115` — `created`
- `docker/ansible/setup-ansible.sh:4` — `ANSIBLE_VERSION`
- `docker/bin/gh:58-62` — `GH_TOKEN` from `git credential fill`
- `docker/bin/gh:51` — re-entrancy `exec`
