---
type: feature
stage: implemented
description: Claude Code cloud sessions run the project toolchain directly on the session host and run no Docker daemon and no devcontainer, so an idle reboot costs only the processes that stopped.
sources:
- resource: .claude/startup.py
- resource: .claude/CLAUDE.cloud.md
- resource: ansible/playbooks/setup-dev.yml
- resource: .pre-commit-config.yaml
---

# Cloud session host toolchain

## Purpose

A cloud session's host is reclaimed after a few idle minutes and cold-boots on
the next event ([Cloud session host
restarts](../architecture/cloud-session-host-restarts.md)). A toolchain on the
host's disk survives that reboot, so a boot costs only the processes that
stopped. The design is [Cloud session host
toolchain](../architecture/cloud-session-host-toolchain.md).

## Behaviour

- **The toolchain lives on the host.** The environment setup script provisions
  the tools the project's work needs onto the session host: `uv` with the
  project's Python environment, `bun`, `iwe`, and the pinned binaries the
  pre-commit hooks call. They are provisioned once per host build, not on each
  boot.
- **Commit, push, and GitHub run on the host.** `git commit` runs the hooks on
  the host, and `git push` and `gh` reach GitHub through the session's agent
  proxy directly.
- **No Docker.** Cloud sessions run no Docker daemon and no devcontainer; image
  builds and image tests run in CI.
- **Session instructions follow.** `.claude/CLAUDE.cloud.md` describes the host
  toolchain.

## Edge cases

- **Version drift.** Host tools come from the same Ansible roles and `uv.lock`
  as the images, so a hook resolves the same version on the host as in CI.
- **Setup time.** Provisioning lengthens the environment setup script, which
  runs once per host build.
- **Tools with services.** Tools that need the devcontainer's supervised
  services (Xpra, the keyring) are unavailable in cloud sessions.

## Open questions

None — the design is settled.
