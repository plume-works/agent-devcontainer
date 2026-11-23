---
type: adr
stage: accepted
supersedes:
- adr/0022-deploy-image-reuses-runtime-helpers
- adr/0023-every-service-authenticates
- adr/0025-fixed-session-bus-address-in-image-env
- adr/0026-latch-waits-for-retry-or-ends-devcontainer
- adr/0028-opencode-first-optional-work-after
- adr/0030-packages-avoid-launchpad
- adr/0033-runtime-is-one-python-package
- adr/0034-supervisord-in-process-as-pid1
- adr/0038-apt-packages-float-within-base-release
- adr/0044-image-and-create-phase-both-install-catalog
- adr/0072-coder-secrets-only-in-the-agent-start
- adr/0073-docker-gc-removes-only-disposable-volumes
- adr/0075-one-empty-home-volume
- adr/0079-runtime-supervises-the-nested-engine
- adr/0092-remote-control-server-on-by-default
- adr/0095-coder-agent-start-runs-opencode-and-remote-control
---

# agentdev-devcontainer is one Dockerfile on plume-works/devcontainer-base, with systemd as PID 1

The maintainer decided that this repository publishes one image,
`agentdev-devcontainer`, built by the plain Dockerfile
`docker/devcontainer/agentdev-devcontainer.Dockerfile` from
`ghcr.io/plume-works/devcontainer-base`, pinned by tag and digest. That base
image supplies Ubuntu 26.04 with apt pinned to a dated archive snapshot, the
`dev` account at UID 1000 with passwordless sudo, the shared toolchain, Claude
Code, OpenCode, and systemd as PID 1 running the Docker engine and its daily
prune. Ansible provisioning, supervisord, and the `agentdev-base`,
`ubuntu-ansible`, and `agentdev-deploy` images are gone. The image adds only
what the base lacks: Xpra, the pinned release tools of
`docker/devcontainer/pinned-tools.yml`, Playwright, the staged catalog, the
egress firewall, and the `agentdev-runtime` lifecycle. Its systemd units in
`docker/devcontainer/systemd/` replace the supervised programs:
`agentdev-bootstrap.service` runs the root bootstrap before the engine and
`systemd-logind`, and hands the container environment to the units in
`/run/agentdev/container.env`; a `docker.service` drop-in requires it, so the
firewall is in place before the engine starts; `agentdev-created.service` runs
the create phase as `dev`; and the user unit `agentdev-xpra.service` runs Xpra.
A standalone OpenCode or Coder workspace uses plume-works' Coder template image
instead of a runtime of this repository.

## Considered Options

- Rebuild `agentdev-deploy` on plume-works' core systemd image. Rejected: the
  Coder template image already runs OpenCode and Remote Control under systemd,
  so a second runtime would duplicate it.
- Keep the `agent` account and rename `dev` in this image. Rejected: every
  plume-works image shares the `dev` account, its home, and its file ownership.
- Keep the D-Bus session bus and GNOME Keyring for `gh`. Rejected: an unlocked
  keyring in a container protects the token no better than `gh`'s `hosts.yml` at
  mode `0600`.

## Consequences

- systemd restarts a failed unit; nothing latches, and `agentdev-runtime health`
  only reads unit states from systemd.
- Node.js is not installed: Bun runs the `playwright` and `mcp-inspector`
  commands through `bun --bun` wrappers.
- git comes from the base image's Ubuntu snapshot; the Git Core PPA and its
  release cache are gone.
- The descriptor mounts volumes on `/home/dev`, `/var/lib/docker`, and
  `/var/lib/containerd`, and runs privileged. GitHub Codespaces is not
  supported, and no host connects to an `sshd` in the container.
