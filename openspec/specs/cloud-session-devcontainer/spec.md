# Cloud session devcontainer Specification

## Purpose

Defines how a Claude Code cloud session runs its tools in this repository's
devcontainer: `.claude/startup.py` prepares the image when the session's host is
built, brings the container up on every session start, and lets it reach the
session's loopback agent proxy so `gh` and git authenticate inside it.

## Requirements

### Requirement: environment setup prepares the image without a container

Run as the cloud session's setup script, `.claude/startup.py` SHALL register the
checkout as the `agent-devcontainer` plugin marketplace and install `agentdev`,
copy `.claude/CLAUDE.cloud.md` to `~/.claude/CLAUDE.md`, start the host
`dockerd`, install the pinned `@devcontainers/cli` with `bun` unless that
version is on `PATH`, and run `devcontainer build` with
`BUILDX_BAKE_ENTITLEMENTS_FS=0`. It SHALL create no container, and any failing
step SHALL fail the script.

#### Scenario: a cloud session's host is built

- **WHEN** the setup script runs on a new session host
- **THEN** the pinned devcontainer image is built and no container exists

### Requirement: every session start restores the container

A `SessionStart` hook in `.claude/settings.json` SHALL run
`.claude/startup.py resume` synchronously. Resume SHALL act only where
`CLAUDE_CODE_REMOTE=true` and `AGENTDEV_RUNTIME_MODE` is unset. It SHALL start
`dockerd` when it does not answer, first removing a `docker.pid` or containerd
pid file that names no running process; keep the relay while it serves the
proxy's current port and otherwise restart it; rewrite
`.devcontainer/cloud-session.env`; recreate the container with
`--remove-existing-container` when its environment misses or differs from that
file; and otherwise bring a stopped or missing container up.

#### Scenario: a worker restart moved the proxy port

- **WHEN** a session starts after a worker restart stopped `dockerd` and moved
  the agent proxy to another port
- **THEN** resume starts `dockerd`, restarts the relay on the new port, and the
  container is up before the session's first turn

#### Scenario: resume runs inside the devcontainer

- **WHEN** the hook runs where `AGENTDEV_RUNTIME_MODE` is set
- **THEN** resume does nothing

### Requirement: the container reaches the agent proxy through a relay

In a cloud session the host `dockerd` SHALL use the bridge `10.213.0.1/24`.
`.claude/agent-proxy-relay.py` SHALL relay port 3128 on the bridge gateway to the
proxy's `127.0.0.1:<port>`. `.devcontainer/cloud-session.env` SHALL set
`HTTPS_PROXY` and `https_proxy` to `http://host.docker.internal:3128`, `NO_PROXY`
and `no_proxy` from the session's list, the session's `GH_TOKEN`, and
`ZIZMOR_OFFLINE=true`, and the Compose service SHALL read it as an optional
`env_file`. The host's git identity SHALL reach the container as `GIT_AUTHOR_*`
and `GIT_COMMITTER_*`.

#### Scenario: gh runs inside the container in a cloud session

- **WHEN** a REST `gh` call runs inside the container
- **THEN** it reaches GitHub through the relay and the proxy authenticates it

#### Scenario: another host has no cloud-session.env

- **WHEN** the devcontainer starts on a host without `cloud-session.env` whose
  Docker client config sets a proxy
- **THEN** the service sets no proxy key and the client config's proxy reaches
  the container

## Rationale

### A relay on a moved bridge

A cloud session authenticates GitHub only through its agent proxy on the host's
`127.0.0.1`: `GH_TOKEN` is a placeholder the proxy replaces, and the proxy injects
git's HTTP authentication, so direct egress reaches GitHub but gets a 401. The
bridge moves off `172.17.0.0/16` because the nested `dockerd` creates its own
`docker0` at `172.17.0.1`, where `host.docker.internal` would resolve to the
container itself. The relay's fixed port keeps a container's environment, fixed
at creation, valid when the proxy's port moves. The relay exposes the session's
GitHub access to every container on the host bridge, which the maintainer
accepted. `ZIZMOR_OFFLINE` is set because the proxy honours the token only for
repositories in the session's scope. `BUILDX_BAKE_ENTITLEMENTS_FS=0` is needed
because, with no Dev Container Feature, the CLI's generated Dockerfile lies
outside every build context. Creating the container delays a session's start by
about 40 seconds. The session's proxy refuses GitHub GraphQL, so `gh` commands
built on it, `gh auth status` among them, fail inside the container as on the
host.

Rejected:

- **Host networking for the devcontainer.** The nested `dockerd` would rewrite
  the host engine's iptables chains.
- **Pass `HTTPS_PROXY` through unchanged.** A host's loopback proxy is
  unreachable from a bridge-networked container.
- **Interpolated `environment` keys.** An unset variable becomes an empty key,
  which overrides the Docker client config's proxy on every other host.
