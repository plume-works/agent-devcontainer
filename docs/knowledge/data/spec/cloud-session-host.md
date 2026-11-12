---
type: spec
description: How a Claude Code cloud session works on its host with no devcontainer — .claude/startup.py setup provisions the agentdev plugin, the cloud instructions, the project toolchain from the image's own Ansible roles, and the git hooks, and startup.py resume restores the host dockerd and the relay that gives containers the agent proxy.
sources:
- resource: .claude/startup.py
- resource: .claude/agent-proxy-relay.py
- resource: .claude/CLAUDE.cloud.md
- resource: .claude/settings.json
- resource: ansible/playbooks/setup-dev.yml
- resource: docker/ansible/setup-ansible.sh
- resource: .pre-commit-config.yaml
- resource: scripts/tests/test_cloud_startup.py
---

# Cloud session host

## Purpose

A Claude Code cloud session works on the session host itself and runs no
devcontainer. `.claude/startup.py setup`, the environment setup script,
provisions the host once; `.claude/startup.py resume`, a `SessionStart` hook,
restores on every session start what a host restart stopped, so short-lived
containers keep reaching the network through the session's agent proxy.

## Requirements

### Requirement: setup provisions the session host

`.claude/startup.py setup` SHALL, in order: register the checkout as the
`agent-devcontainer` plugin marketplace and install `agentdev`; copy
`.claude/CLAUDE.cloud.md` to `~/.claude/CLAUDE.md`; merge `ZIZMOR_OFFLINE=true`
into the `env` of `~/.claude/settings.json`, keeping its other entries; install
Ansible with `docker/ansible/setup-ansible.sh` and run
`ansible/playbooks/setup-dev.yml` with the `dev_tools`, `bun_setup`, and
`uv_setup` tags and `/usr/bin/python3.12` as the modules' interpreter; then run
`uv sync` and `pre-commit install --install-hooks` for the `pre-commit`,
`pre-push`, `pre-merge-commit`, and `post-checkout` hook types. It SHALL set the
standard streams to blocking before each command. A failing step SHALL end the
script with a nonzero status and run no later step.

#### Scenario: setup completes

- **WHEN** the cloud environment runs `.claude/startup.py` on a fresh host
- **THEN** `agentdev` is installed, every `language: system` pre-commit hook's
  binary, `bun`, `iwe`, and `uv` are on `PATH` from the same roles the published
  images use, and the git hooks run `pre-commit` from the project environment

#### Scenario: a step fails

- **WHEN** the Ansible playbook exits nonzero
- **THEN** the script prints the error, exits 1, and does not run `uv sync`

#### Scenario: a command reads zizmor's settings

- **WHEN** any command the session runs invokes `zizmor`
- **THEN** it inherits `ZIZMOR_OFFLINE=true` from the user-level Claude Code
  settings and skips the online audits

### Requirement: resume restores the host's Docker and relay on a cloud host only

`.claude/settings.json` SHALL run `.claude/startup.py resume` as a
`SessionStart` hook. Resume SHALL act only when `CLAUDE_CODE_REMOTE` is `true`
and `AGENTDEV_RUNTIME_MODE` is unset, and SHALL keep what still runs. When
`docker info` fails it SHALL remove a `/var/run/docker.pid` or
`/var/run/docker/containerd/containerd.pid` that names no running process of
that program, then start `dockerd --bip 10.213.0.1/24` in its own session and
fail when the daemon does not answer within 30 seconds.

#### Scenario: a worker restart stopped the daemon

- **WHEN** a session starts after a host restart left `/var/run/docker.pid`
  holding a pid another process now uses
- **THEN** resume removes the pid file, starts `dockerd`, and returns once
  `docker info` succeeds

#### Scenario: resume inside a runtime image

- **WHEN** the hook runs where `AGENTDEV_RUNTIME_MODE` is set
- **THEN** resume does nothing

#### Scenario: run again with everything up

- **WHEN** resume runs while `dockerd` and the relay for the current proxy port
  are running
- **THEN** it starts nothing

### Requirement: containers reach the agent proxy through a fixed relay

When `HTTPS_PROXY` names a loopback proxy `http://127.0.0.1:<port>`, resume
SHALL keep `.claude/agent-proxy-relay.py`, a TCP relay from `10.213.0.1:3128` to
`127.0.0.1:<port>`, running: it SHALL keep the recorded relay while
`/proc/<pid>/cmdline` names the relay with that port, and otherwise stop it and
start a new one. It SHALL set the `proxies.default` entry of
`~/.docker/config.json` to the relay for HTTP and HTTPS, with the session's
`NO_PROXY`, keeping the file's other settings. Without a loopback proxy it SHALL
stop the relay, remove that entry, and warn.

#### Scenario: the agent proxy moved port

- **WHEN** a session starts with `HTTPS_PROXY` on a port other than the one the
  running relay forwards to
- **THEN** resume replaces the relay with one forwarding to the new port, and a
  container's proxy address `10.213.0.1:3128` stays the same

#### Scenario: a container is run

- **WHEN** the session runs `docker run` or `docker build` with no proxy flags
- **THEN** the Docker client passes the relay as the container's proxy

## Rationale

### The session works on the host, not in a devcontainer

Cloud sessions run no devcontainer, by the repository owner's decision. The
session host is reclaimed after a few idle minutes and cold-boots with a new
agent proxy port; a toolchain on the host's disk survives that, while a
long-running container would have to be restored before every turn. Host tools
come from the same `dev_tools`, `bun_setup`, and `uv_setup` roles and the same
`uv.lock` as the published images, so a hook resolves the same version on the
host as in CI. The relay exposes the agent proxy, and with it the session's
GitHub access, to every container on the host; the maintainer accepted that for
cloud sessions. The bridge subnet sits off `172.17.0.0/16`, where a nested
engine inside a container creates its own `docker0`.

Rejected:

- **A long-running devcontainer on the session host.** A worker restart stops
  every container, so it would be rebuilt or restarted before every turn.
