---
type: adr
stage: accepted
description: A cloud session installs its toolchain on the session host and runs no Dev Container.
---

# A cloud session works on its host, not in a Dev Container

The session host stops after some idle minutes and starts again with a new agent
proxy port. A toolchain on the host disk stays after this, but the session must
restore a container that runs for a long time before each turn. As a result, a
cloud session runs no Dev Container, by decision of the repository owner.

## Considered Options

- A Dev Container that runs for a long time on the session host. Rejected: a
  worker restart stops each container, so each turn starts with a rebuild or a
  restart.

## Consequences

- `.claude/startup.py` installs the host tools from the Ansible roles
  `dev_tools`, `bun_setup`, and `uv_setup` and syncs from `uv.lock`, as the
  published images do. As a result, a hook resolves the same version on the host
  as in CI.
- The relay gives the agent proxy, and with it the GitHub access of the session,
  to each container on the host. The maintainer accepted this for cloud
  sessions.
- The host `dockerd` uses a bridge subnet outside `172.17.0.0/16`
  (`.claude/startup.py::start_docker`), because a nested engine in a container
  makes its own `docker0` in that subnet.
- A `SessionStart` hook in `.claude/settings.json` runs
  `.claude/startup.py resume` at each session start. It acts only on a cloud
  session host (`.claude/startup.py::is_cloud_host`), keeps each process that
  still runs, and starts `dockerd` and the relay again.
- The disk keeps `/var/run`. For this reason, the resume removes a `dockerd` or
  `containerd` pid file that names no running process, because `dockerd` does
  not start while the pid in its file is alive.
- The relay listens on a fixed address on the bridge, and the Docker client
  configuration tells each container to use it. As a result, a container keeps a
  valid proxy when the agent proxy port changes.
- A container lives only until the next worker restart, so no part of a cloud
  session needs a container that runs for a long time.
- The agent proxy terminates TLS again, so a container that makes TLS requests
  needs the CA bundle of the host.
- The Ansible modules run on `/usr/bin/python3.12`, because the apt Python
  bindings that the `apt` module needs exist only for the system Python.
- The `link-venv` hook needs `agentdev-runtime`, which only the images have. On
  the host it does nothing, and `.venv` is the environment that `uv sync` made.
