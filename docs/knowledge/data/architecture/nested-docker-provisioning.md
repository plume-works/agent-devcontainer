---
type: architecture
description: Docker-in-Docker comes from the upstream devcontainer feature rather than a hand-rolled dockerd bootstrap, and SSH comes from the sshd feature plus image-level packages, so the same image works from a Codespace.
generated:
  by: claude-code/opus-5
  at: 2026-09-04T00:00:00Z
sources:
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/devcontainer-lock.json
- resource: .devcontainer/devcontainer-init.sh
- resource: ansible/roles/basic_prereqs/tasks/main.yml
- resource: https://github.com/Dr-QP/Dr.QP/pull/406
- resource: https://github.com/Dr-QP/Dr.QP/pull/407
- resource: https://github.com/Dr-QP/Dr.QP/pull/403
---

# Nested Docker provisioning

## Decision

The nested Docker engine is provided by the upstream
`ghcr.io/devcontainers/features/docker-in-docker` feature, with its resolved
version pinned in `devcontainer-lock.json`. No repository script starts,
detects, or restarts `dockerd`.

SSH is provided the same way, by the `devcontainers/features/sshd` feature,
while the packages it needs (`openssh-server`, `rsync`) are installed in the
image by Ansible.

## Why a feature rather than a bootstrap script

A nested `dockerd` cannot use the container's own overlay-mounted writable layer
for `/var/lib/docker` — overlayfs on overlayfs, which the kernel rejects.
Solving that in the repository means carrying storage-driver fallback, PID and
socket detection, and restart logic, invoked from every lifecycle hook that
might find the daemon down.

The feature owns that problem upstream and manages its own Docker storage, so no
repository-declared volume is needed to give `dockerd` a non-overlay filesystem.

## Why the SSH capability is split across a feature and the image

The feature performs sshd **configuration**; the image supplies the
**packages**. Installing the packages at image build time keeps a Codespace
usable immediately rather than paying an apt install on every container create;
keeping configuration in the feature avoids reimplementing host-key and account
setup.

This split is what makes the image reachable over `gh codespace ssh`, which the
`/agentdev:remote-codespace-session` skill depends on as its transport when no
Docker daemon is available locally.

## The host-side precondition

`devcontainer-init.sh` runs on the **host**, before the container is built, and
Codespaces invokes it through `/bin/sh -c` with no `HOME` set. Every expansion
of `$HOME` there must be guarded. An unguarded reference aborts the whole build
and drops the user into a recovery container rather than failing with a legible
error.

## Consequences

- Upgrading either capability is a version bump in `devcontainer.json` plus a
  regenerated `devcontainer-lock.json`, not a script change.
- The features run at container-create time, so they take effect even before a
  rebuilt image carries the packages.
