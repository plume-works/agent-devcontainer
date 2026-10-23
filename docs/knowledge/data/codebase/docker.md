---
type: codebase
description: The Dockerfiles that produce ubuntu-ansible, agent-desktop, and agent-opencode, plus the entrypoint, the Xpra start script, the gh auth wrapper, and the standalone runtime's supervisord config and settings example.
source: docker
source_digest: sha256:12d316619ec1752302c102dbc5aeb62bc172b697d6744e45839628be5c946960
verified:
  by: claude-code/opus-5.5
  at: 2026-10-23T14:00:00Z
stale_after: 2027-01-21
generated:
  by: claude-code/opus-5.5
  at: 2026-10-23T14:00:00Z
sources:
- id: code
  resource: docker
---

# Image build (Docker)

Three images, built in sequence: `docker/ansible/Dockerfile` turns
`ubuntu:24.04` into `ubuntu-ansible` (Ansible and its collections, locale),
`docker/desktop/agent-desktop.Dockerfile` provisions that base with the
[playbook](ansible.md), every capability on, and adds the runtime scripts, and
`docker/opencode/agent-opencode.Dockerfile` layers the standalone OpenCode
runtime on a supplied `agent-desktop` digest.

## Public surface

- `docker/desktop/agent-desktop.Dockerfile` build args — `FROM_IMAGE:5`,
  `WORKSPACE_FOLDER:12`, `AGENTDEV_PLUGIN_VERSION:18`,
  `AGENTDEV_CATALOG_DIR:22`, `VALIDATE_AGENT_FILES_VERSION:29`,
  `PLAYWRIGHT_VERSION:33` (required; supplied by the image workflow)
- `docker/opencode/agent-opencode.Dockerfile` build arg `FROM_IMAGE:3`, also
  recorded as the `org.opencontainers.image.base.name` label
- `docker/opencode/supervisord.conf` — the controller event listener and the
  eight programs it starts; baked to `/etc/agentdev/supervisord.conf`
- `docker/opencode/runtime.env.example` — every setting the root
  `compose.opencode.yml` interpolates
- `docker/opencode/README.md` — the operator deployment guide for the root
  Compose files; not copied into the image
- `/entrypoint.sh`, `/start-xpra.sh`, the `gh` wrapper — the files a running
  container exposes; their contract is in [the image runtime
  interface](api-image-runtime.md)
- `docker/ansible/setup-ansible.sh` — pins Ansible `13.4.0` and installs the two
  collections

## How it works

The desktop Dockerfile bind-mounts the whole build context read-only at
`/provision`, `cd`s into it so `ansible.cfg` is found, and runs
`ansible-playbook ansible/playbooks/setup-dev.yml` with every `install_*` flag
and the catalog, validator, and Playwright pins as extra vars; the workflow
reads the Playwright pin from the role default before the build. None of the
provisioning sources land in a layer. The Dockerfile then exports
`AGENTDEV_CATALOG_DIR` and `PLAYWRIGHT_BROWSERS_PATH`, labels the image with all
three versions, copies the two scripts, exposes `14500`, and sets the
entrypoint, which only `exec`s the command.

The OpenCode Dockerfile installs apt `supervisor`, deletes the stock `ubuntu`
account, and copies the root-home `gh-stack` extension to
`/usr/local/lib/agentdev/gh-stack`. It copies `.devcontainer/scripts/` to
`/opt/agentdev-runtime`, `start-xpra.sh`, `supervisord.conf`, and the firewall
allowlist to `/etc/agentdev/`. It then sets the runtime identity, path, and
service `ENV`, exposes `4096` and `14500`, and gives `runtime-supervisor.py run`
as the entrypoint with a `runtime-health.sh ready` healthcheck. `.dockerignore`
reopens only `.devcontainer/scripts` and the allowlist for it.

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
which the OpenCode image bakes.

## Invariants & gotchas

- Both `FROM_IMAGE` defaults are tag-only by design; CI overrides each with the
  digest built in the same run. A digest here would make Renovate bump a file
  under `docker/**`, which matches the image path filter and rebuilds the image
  that produced the digest, forever.
- The three version args are verified pins: the playbook fails when the staged
  catalog, installed validator, or Playwright CLI reports a different version.
  The Dockerfile also rejects an omitted Playwright build argument.
- The build context is the repository root, never `docker/desktop/` or
  `docker/opencode/`.
- The OpenCode image copies `start-xpra.sh` itself because the desktop digest it
  builds on can predate `--supervised`.

## Key references

Verified anchor points (line numbers as of 2026-10-19):

- `docker/desktop/agent-desktop.Dockerfile:45-68` — provisioning and required
  Playwright version
- `docker/desktop/agent-desktop.Dockerfile:75-80` — `ENV` and version labels
- `docker/desktop/agent-desktop.Dockerfile:84-94` — scripts, port, entrypoint
- `docker/opencode/agent-opencode.Dockerfile:11` — supervisor, account removal,
  `gh-stack` relocation; `:22-26` — baked runtime files; `:30` — runtime `ENV`;
  `:59-65` — ports, healthcheck, entrypoint
- `docker/opencode/supervisord.conf:23` — the controller; `:36-146` — the eight
  programs
- `docker/ansible/setup-ansible.sh:4` — `ANSIBLE_VERSION`
- `docker/desktop/start-xpra.sh:7` — default HTML5 container port
- `docker/desktop/start-xpra.sh:175-183` — `--port` override
- `docker/desktop/start-xpra.sh:285-287` — `XPRA_PASSWORD` session auth
- `docker/desktop/start-xpra.sh:74` — `reclaim_orphaned_display`; `:320` — the
  supervised `exec`
- `docker/bin/gh:58-62` — `GH_TOKEN` from `git credential fill`
- `docker/bin/gh:51` — re-entrancy `exec`
