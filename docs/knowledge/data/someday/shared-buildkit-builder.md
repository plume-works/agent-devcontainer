---
type: someday
description: Run one BuildKit daemon in a dedicated Coder workspace and make it the default builder for docker build inside every Dev Container, so workspaces share one build cache, falling back to the local builder when it is unreachable.
---

# Share one BuildKit builder across Coder workspaces

Each Coder workspace's Dev Container engine keeps its own BuildKit cache, so
workspaces that build the same images store and rebuild the same layers. [Cap
Docker storage with automatic garbage
collection](../archive/2.0.0/plans/20261013-docker-storage-gc.md) bounds each
cache; one shared builder would hold one cache for all of them.

## The idea

- One `buildkitd` runs in a dedicated, always-on Coder workspace, with its state
  on a persistent volume and its cache capped (30 GB was the working
  assumption).
- Each Dev Container's agent start, `agentdev-runtime coder start`, registers it
  as a `remote`-driver buildx builder named `shared` with `default-load=true`,
  so a plain `docker build` still loads its result into the local engine. The
  registration would be an `agentdev-runtime docker builder` subcommand whose
  failure is a warning, never a stop.
- `shared` is the default builder when it answers at agent start; otherwise the
  local `default` builder is selected. A builder lost mid-session fails the
  build, and `docker build --builder default` builds locally.
- Only `docker build` inside Dev Containers changes: the devcontainer CLI builds
  the Dev Container image on the workspace engine, which keeps its own builder.

## Decisions already made

The maintainer decided that the daemon runs in a dedicated Coder workspace, not
as a host service next to Sysbox, and that it is the default builder, not
opt-in. A host service would outlive any workspace, but needs host access to
deploy and change.

## Open questions

- How a Dev Container reaches the builder workspace: for example
  `coder port-forward` to a loopback port, which needs a Coder user session, or
  a published port reached over the host network.
- How the endpoint is authenticated. `buildkitd` over TCP accepts any client
  unless mTLS is configured, so an endpoint reachable from outside Coder
  workspaces needs mTLS.
- Where the builder workspace's template lives: a second template in
  `plume-works/coder-ide-baseline`, or `coder-ide-baseline` with a parameter.
- How much it would save once per-workspace garbage collection already bounds
  each cache.

## Out of scope

- Sharing images or registry pulls between workspaces.
- Builder isolation between Coder users; the deployment has one user.
- Codespaces and local Dev Containers, which have no Coder agent start.
