---
type: adr
stage: accepted
description: A cloud session installs its toolchain on the session host and runs no Dev Container.
---

# A cloud session works on its host, not in a Dev Container

The session host, which is the machine that a cloud session runs on, stops after
some idle minutes and starts again with a new agent proxy port. A toolchain on
the host disk stays after this, but the session must restore a container that
runs for a long time before each turn. As a result, a cloud session runs no Dev
Container, by decision of the repository owner.

## Considered Options

- A Dev Container that runs for a long time on the session host. Rejected: a
  restart of the session host keeps the disk but stops each container, so each
  turn starts with a rebuild or a restart.

## Consequences

- The relay, a TCP forwarder from the Docker bridge address to the port of the
  agent proxy, gives the agent proxy, and with it the GitHub access of the
  session, to each container on the host. The maintainer accepted this for cloud
  sessions.
- The agent proxy terminates TLS again, so a container that makes TLS requests
  needs the CA bundle of the host.
