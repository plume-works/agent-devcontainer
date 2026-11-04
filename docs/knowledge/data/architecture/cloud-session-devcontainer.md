---
type: architecture
description: In a Claude Code cloud session .claude/startup.py brings the devcontainer up on the session host and lets it reach the session's loopback agent proxy through a relay on the host Docker bridge, moved off 172.17.0.0/16, so gh and git authenticate inside the container.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-04T03:50:45Z
sources:
- resource: .claude/startup.py
- resource: .claude/agent-proxy-relay.py
- resource: .claude/CLAUDE.cloud.md
- resource: .claude/settings.json
- resource: devcontainer-compose-pins.yml
- resource: .devcontainer/docker-compose.yml
- resource: https://code.claude.com/docs/en/claude-code-on-the-web
---

# Cloud session devcontainer

## Startup sequence

A Claude Code cloud session runs `.claude/startup.py` as its environment setup
script. The repository checkout stays on the session's host; the toolchain lives
in the devcontainer, which the script brings up before the session starts work:

1. registers the checkout as the `agent-devcontainer` plugin marketplace and
   installs `agentdev`;
2. copies `.claude/CLAUDE.cloud.md` to `~/.claude/CLAUDE.md`, which tells the
   session that the devcontainer is already up and that tools run through
   `/agentdev:devcontainer-sandbox`;
3. starts the host `dockerd`;
4. pre-pulls the images pinned in `devcontainer-compose-pins.yml`;
5. installs a pinned `@devcontainers/cli` with `bun` unless that version is
   already on `PATH`, prepares the proxy access and git identity described
   below, and runs `devcontainer up` on the checkout.

Any failing step fails the script, and the session starts without the steps
after it.

The setup script runs once, when the session's host is built, and without the
session's loopback agent proxy, so the container it creates has no proxy access.
A worker restart inside a session stops the host `dockerd`, the relay and with
them the container, and can move the agent proxy to another port. A
`SessionStart` hook in `.claude/settings.json` therefore runs
`.claude/startup.py resume` on every session start. Resume mode acts only on a
cloud-session host (`CLAUDE_CODE_REMOTE=true` and no `AGENTDEV_RUNTIME_MODE`,
which the devcontainer sets), keeps whatever still runs, and restores the rest:

- starts `dockerd` when it does not answer;
- keeps the relay while `/proc/<pid>/cmdline` still names it with the proxy's
  current port, and otherwise restarts it there;
- rewrites `.devcontainer/cloud-session.env`, and recreates the container with
  `devcontainer up --remove-existing-container` when its environment misses a
  line of that file or carries a different value;
- otherwise brings a stopped or missing container up.

## Decision

A Claude Code cloud session authenticates GitHub only through its agent proxy,
which listens on the host's `127.0.0.1`. The session's `GH_TOKEN` is a
placeholder that the proxy replaces with the real credential, and the proxy
injects git's HTTP authentication. Direct egress from a container reaches
GitHub, but the placeholder token gets a 401 there.

`.claude/startup.py`, which runs only in cloud sessions, therefore:

- starts the host `dockerd` with `--bip 10.213.0.1/24`;
- runs `.claude/agent-proxy-relay.py`, a plain TCP relay from port 3128 on the
  host bridge gateway to the proxy's current `127.0.0.1:<port>`;
- writes `.devcontainer/cloud-session.env` (git-ignored) with `HTTPS_PROXY` and
  `https_proxy` set to `http://host.docker.internal:3128`, `NO_PROXY` and
  `no_proxy` from the session's own list, and the session's `GH_TOKEN`;
- exports `GIT_AUTHOR_*` / `GIT_COMMITTER_*` from the host's git identity, which
  `.devcontainer/docker-compose.yml` already passes through.

The Compose service reads that file as an optional `env_file`. Where it is
absent, as on every other host, the service sets none of those keys, so a proxy
the host configures in its Docker client config still reaches the container.

## Constraints

- The bridge subnet moves because the devcontainer's nested `dockerd` creates
  its own `docker0` at `172.17.0.1`. With the host bridge there too,
  `host.docker.internal` (`host-gateway`) resolves to the container itself.
- The relay exposes the proxy, and with it the session's GitHub access, to every
  container on the host bridge. The maintainer accepted that for cloud sessions.
- The container's environment is fixed when it is created, and the devcontainer
  CLI restarts an existing container instead of recreating it. The relay's fixed
  port keeps that environment valid when the proxy's port moves; a container
  created without `cloud-session.env`, as every setup script creates it, is
  recreated by the first `resume`. That recreate runs inside the `SessionStart`
  hook: container creation plus the `postCreate`, `postStart` and `postAttach`
  commands, about 30 seconds each, and an image pull and build when the pin
  changed.
- GitHub GraphQL is refused by the session's proxy policy, so `gh` commands
  built on it fail inside the container exactly as on the host. `gh auth status`
  validates the token through GraphQL, so it reports the token as invalid while
  REST calls with it succeed.
- The proxy serves repository paths on `github.com` but answers the bare root
  `https://github.com/` with 400, and git needs no credential helper because the
  proxy injects its authentication.

## Rejected alternatives

- **Host networking for the devcontainer.** It reaches the loopback proxy with
  nothing exposed, but the nested `dockerd` then shares the host's network
  namespace and rewrites the host engine's iptables chains, removing the
  forwarding rules for the host's Compose bridge.
- **Passing `HTTPS_PROXY` through unchanged.** A host's loopback proxy is
  unreachable from a bridge-networked container, so forwarding it would cut that
  container's egress on any host that sets one.
- **Interpolated `environment` keys.** A key such as
  `HTTPS_PROXY: ${DEVCONTAINER_HTTPS_PROXY:-}` is set to an empty string when
  the variable is unset, and a key the service sets overrides the proxy from the
  Docker client config, so non-cloud hosts would lose their proxy.
