---
type: adr
stage: accepted
description: A cloud session installs its toolchain on the session host and runs no devcontainer.
---

# A cloud session works on its host, not in a devcontainer

The session host stops after some idle minutes and starts again with a new agent
proxy port. A toolchain on the host disk stays after this, but the session must
restore a container that runs for a long time before each turn. As a result, a
cloud session runs no devcontainer, by decision of the repository owner.

## Considered Options

- A devcontainer that runs for a long time on the session host. Rejected: a
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
