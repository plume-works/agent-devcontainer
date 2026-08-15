---
name: microvm-sandbox
description: Run build, test, or lint commands through this repository's devcontainer when the host lacks the project toolchain. Use for devcontainer up or exec, Docker-backed sandbox testing, and local toolchain escalation.
---

# microVM Sandbox

Use this skill when the host cannot run the project's toolchain directly — `uv`
is missing, `bun` is missing, or a command needs the provisioned image — **and** a
Docker daemon is available. If Docker is unavailable, use
[remote-codespace-session](../remote-codespace-session/SKILL.md) instead.

Start the development container from the repository root when it is not already
running:

```bash
devcontainer up --workspace-folder . \
  --mount "type=bind,source=/var/run/docker.sock,target=/var/run/docker.sock"
```

Run the original command inside it:

```bash
devcontainer exec --workspace-folder . bash -lc 'uv run pytest <path>'
```

```bash
devcontainer exec --workspace-folder . bash -lc 'bun test <path>'
```

Keep the same selectors and paths the command would have used locally — the
container mounts the workspace, so relative paths resolve identically. If a
dependency was added, run `uv sync` (or `bun install`) inside the container
first; `.devcontainer/scripts/uv-sync.sh` does this, syncing into the cached
environment volume.

The container is not disposable: it keeps its state between `exec` calls. Stop it
with `docker compose -f .devcontainer/docker-compose.yml -f compose.pins.yml down`
from the repository root when finished, or leave it running for the rest of the
session. Both files are needed: `compose.pins.yml` carries the image digest pin
that `devcontainer up` layers on through `devcontainer.json`.
