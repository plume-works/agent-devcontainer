---
type: feature
stage: proposed
description: Claude Code cloud sessions run the project toolchain directly on the session host, so an idle reboot costs only the processes that stopped, while the host dockerd and the devcontainer stay for Docker image builds and tests.
sources:
- resource: .claude/startup.py
- resource: .claude/CLAUDE.cloud.md
- resource: .claude/settings.json
- resource: ansible/playbooks/setup-dev.yml
- resource: .pre-commit-config.yaml
---

# Cloud session host toolchain

## Purpose

A cloud session's host is reclaimed after a few idle minutes and cold-boots on
the next event ([Cloud session host
restarts](../architecture/cloud-session-host-restarts.md)). With the toolchain
only inside the devcontainer ([Cloud session
devcontainer](../../../../openspec/specs/cloud-session-devcontainer/spec.md#rationale)),
every boot must restore the host `dockerd`, the agent proxy relay, and the
container before any tool runs, and each step of that restore has been a source
of failures. Provisioning the toolchain on the host itself makes a reboot cost
only the processes that stopped.

## Behaviour

- **The toolchain lives on the host.** The environment setup script provisions
  the tools the project's work needs onto the session host: `uv` with the
  project's Python environment, `bun`, `iwe`, Ansible, and the system binaries
  the pre-commit hooks call. The host's disk survives a reboot, so they are
  provisioned once per host build, not on each boot.
- **Commit, push, and GitHub run on the host.** `git commit` runs the hooks on
  the host, and `git push` and `gh` reach GitHub through the session's agent
  proxy directly, with no relay and no container in the path.
- **Docker stays for Docker work.** The host `dockerd` and the devcontainer
  setup remain for `docker build`, image tests, and anything that needs the
  provisioned image, and come up when that work needs them rather than as a
  precondition of every turn.
- **Session instructions follow.** `.claude/CLAUDE.cloud.md` stops routing every
  tool through `devcontainer exec` and describes the host toolchain, with the
  devcontainer as the path for Docker work only.

## Edge cases

- **Version drift.** Host tools and the devcontainer image must resolve the same
  pinned versions, or a hook passes on the host and fails in CI's pre-commit run
  on the candidate image.
- **Docker work after a reboot.** A turn that needs Docker still meets a host
  whose `dockerd` and relay stopped; `.claude/startup.py resume` keeps that path
  working.
- **Setup time.** Provisioning on the host lengthens the environment setup
  script, which runs once per host build.
- **Tools with services.** Tools that need the devcontainer's supervised
  services (Xpra, the keyring) stay container-only.

## Open questions

- Whether the host is provisioned by running `ansible/playbooks/setup-dev.yml`
  against it, by a narrower role selection, or by a separate install list.
- Whether the `SessionStart` hook still brings the devcontainer up on every
  start, or only `dockerd`, with the container started on demand.
- Whether the proxy relay is still needed once nothing in the container pushes
  to GitHub.
