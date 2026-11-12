---
type: architecture
description: A Claude Code cloud session works on the session host itself — .claude/startup.py provisions the project toolchain there with the image's own Ansible roles — and runs no devcontainer; a host dockerd and a relay to the agent proxy serve short-lived containers.
sources:
- resource: .claude/startup.py
- resource: .claude/CLAUDE.cloud.md
- resource: .claude/agent-proxy-relay.py
- resource: .claude/settings.json
- resource: ansible/playbooks/setup-dev.yml
- resource: docker/ansible/setup-ansible.sh
- resource: .pre-commit-config.yaml
- resource: https://code.claude.com/docs/en/claude-code-on-the-web
---

# Cloud session host toolchain

## Setup

A Claude Code cloud session runs `.claude/startup.py` as its environment setup
script, once, when the session's host is built. It:

1. registers the checkout as the `agent-devcontainer` plugin marketplace and
   installs `agentdev`;
2. copies `.claude/CLAUDE.cloud.md` to `~/.claude/CLAUDE.md`, which tells the
   session that tools, commits, pushes and `gh` run on the host;
3. merges `ZIZMOR_OFFLINE=true` into the `env` of the user-level
   `~/.claude/settings.json`, so every command the session runs skips zizmor's
   online audits, which the session's placeholder `GH_TOKEN` fails ([Bug: zizmor
   online audits fail in the cloud
   devcontainer](../../../bugs/zizmor-online-audits-fail-in-cloud-devcontainer.md));
4. installs Ansible with `docker/ansible/setup-ansible.sh` and runs
   `ansible/playbooks/setup-dev.yml` with the `dev_tools`, `bun_setup` and
   `uv_setup` tags, which install the pinned binaries every `language: system`
   pre-commit hook calls, `bun`, `iwe`, and `uv`, with the playbook's modules on
   `/usr/bin/python3.12` and every command given blocking standard streams;
5. runs `uv sync` and installs the git hooks with
   `pre-commit install --install-hooks` for the `pre-commit`, `pre-push`,
   `pre-merge-commit` and `post-checkout` hook types.

Any failing step fails the script, and the session starts without the steps
after it.

## Resume

The session's host starts with no process running, and a worker restart stops
the host `dockerd`, the relay, and every container, and can move the agent proxy
to another port. A `SessionStart` hook in `.claude/settings.json` therefore runs
`.claude/startup.py resume` on every session start. Resume mode acts only on a
cloud-session host (`CLAUDE_CODE_REMOTE=true` and no `AGENTDEV_RUNTIME_MODE`,
which the runtime images set), keeps whatever still runs, and restores the rest:

- starts `dockerd` with `--bip 10.213.0.1/24` when it does not answer, first
  removing a `/var/run/docker.pid` that names no running `dockerd` and a
  `/var/run/docker/containerd/containerd.pid` that names no running
  `containerd`: `/var/run` is on the persistent disk, `dockerd` refuses to start
  while the pid in its own file is alive, and it takes a live pid in
  containerd's file for its containerd;
- keeps `.claude/agent-proxy-relay.py`, a plain TCP relay from `10.213.0.1:3128`
  to the proxy's current `127.0.0.1:<port>`, while `/proc/<pid>/cmdline` still
  names it with that port, and otherwise restarts it;
- sets the `proxies.default` entry of `~/.docker/config.json` to the relay, with
  the session's `NO_PROXY`, so the Docker client passes the proxy to every
  container it runs or builds. Without a loopback agent proxy it stops the relay
  and removes that entry.

## Decision

Cloud sessions run no devcontainer (human:author). The session host is reclaimed
after a few idle minutes and cold-boots on the next event with a new agent proxy
port ([Cloud session host
restarts](../../../findings/cloud-session-host-restarts.md)); a toolchain on the
host's disk survives that, while a long-running container had to be restored
before every turn. Short-lived containers keep working: the host `dockerd` and
the relay come back on every session start, and a container reaches GitHub and
package registries through the agent proxy, which listens only on the host's
`127.0.0.1`. `git push` and `gh` on the host use the proxy directly.

## Constraints

- Host tools and the published images come from the same `dev_tools`,
  `bun_setup` and `uv_setup` roles and the same `uv.lock`, so a hook resolves
  the same version on the host as in CI's pre-commit job; `bun_setup` supplies
  the `bunx` the `prettier` and `renovate-config-validator` hooks call.
- A container lives only until the next worker restart, so nothing in a cloud
  session depends on a long-running one.
- The bridge subnet is fixed off `172.17.0.0/16`, where a nested engine inside a
  container creates its own `docker0`, and the relay's fixed address keeps a
  container's proxy valid when the agent proxy's port moves.
- The relay exposes the agent proxy, and with it the session's GitHub access, to
  every container on the host. The maintainer accepted that for cloud sessions.
- The agent proxy re-terminates TLS, so a container that makes TLS requests
  needs the host's CA bundle mounted.
- The session host's `python3` is 3.13, while apt's Python bindings, which
  Ansible's `apt` module imports, are built only for the system Python 3.12, so
  the playbook's modules run on `/usr/bin/python3.12`.
- The setup runner hands the script non-blocking standard streams, which Ansible
  refuses, so the script sets them back to blocking before each command.
- The `link-venv` hook needs `agentdev-runtime`, which only the images ship, so
  on the host it skips and `.venv` is the project environment `uv sync` made.
- The session's proxy answers GitHub requests outside the session's repositories
  with a 400 or 403, from the host and from a container alike, so only a
  repository-scoped path shows whether a container reaches GitHub.
- GitHub GraphQL is refused by the session's proxy policy, so `gh` commands
  built on it fail; `gh auth status` validates the token through GraphQL and
  reports it as invalid while REST calls with it succeed.
