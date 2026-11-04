---
type: architecture
description: In a Claude Code cloud session the devcontainer reaches the session's loopback agent proxy through a relay on the host Docker bridge, which .claude/startup.sh moves off 172.17.0.0/16, so gh and git authenticate inside the container.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-04T00:30:00Z
sources:
- resource: .claude/startup.sh
- resource: .claude/agent-proxy-relay.py
- resource: .devcontainer/docker-compose.yml
- resource: /root/.ccr/README.md
---

# Cloud session devcontainer

## Decision

A Claude Code cloud session authenticates GitHub only through its agent proxy,
which listens on the host's `127.0.0.1`. The session's `GH_TOKEN` is a
placeholder that the proxy replaces with the real credential, and the proxy
injects git's HTTP authentication. Direct egress from a container reaches
GitHub, but the placeholder token gets a 401 there.

`.claude/startup.sh`, which runs only in cloud sessions, therefore:

- starts the host `dockerd` with `--bip 10.213.0.1/24`;
- runs `.claude/agent-proxy-relay.py`, a plain TCP relay from the host bridge
  gateway, on the proxy's port, to `127.0.0.1:<port>`;
- exports `DEVCONTAINER_HTTPS_PROXY=http://host.docker.internal:<port>`,
  `DEVCONTAINER_NO_PROXY` and `DEVCONTAINER_GH_TOKEN` from the session's own
  values, and `GIT_AUTHOR_*` / `GIT_COMMITTER_*` from the host's git identity.

`.devcontainer/docker-compose.yml` maps the `DEVCONTAINER_*` variables onto
`HTTPS_PROXY`, `https_proxy`, `NO_PROXY`, `no_proxy` and `GH_TOKEN`, and already
passes the git identity variables through. With the variables unset, as on any
other host, each mapped variable is empty and the container behaves as before.

## Constraints

- The bridge subnet moves because the devcontainer's nested `dockerd` creates
  its own `docker0` at `172.17.0.1`. With the host bridge there too,
  `host.docker.internal` (`host-gateway`) resolves to the container itself.
- The relay exposes the proxy, and with it the session's GitHub access, to every
  container on the host bridge. The maintainer accepted that for cloud sessions.
- The proxy address is fixed when the container is created. A new session
  re-runs `.claude/startup.sh` and recreates the container.
- GitHub GraphQL is refused by the session's proxy policy, so `gh` commands
  built on it fail inside the container exactly as on the host. `gh auth status`
  reports the placeholder token as invalid on both.

## Rejected alternatives

- **Host networking for the devcontainer.** It reaches the loopback proxy with
  nothing exposed, but the nested `dockerd` then shares the host's network
  namespace and rewrites the host engine's iptables chains, removing the
  forwarding rules for the host's Compose bridge.
- **Passing `HTTPS_PROXY` through unchanged.** A host's loopback proxy is
  unreachable from a bridge-networked container, so forwarding it would cut that
  container's egress on any host that sets one. Dedicated `DEVCONTAINER_*` names
  keep the forwarding opt-in.
