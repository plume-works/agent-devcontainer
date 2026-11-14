---
type: task
created: 2026-11-14
stage: pending
priority: medium
description: Remove the supervised D-Bus session bus and GNOME Keyring from the agentdev runtime images. They give no security, and `gh` can keep its token in its own file.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/keyring.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/supervisor.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/git.py
- resource: ansible/roles/basic_prereqs/tasks/main.yml
- resource: docker/devcontainer/supervisord.conf
- resource: docker/deploy/supervisord.conf
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: docs/knowledge/data/spec/agentdev-runtime-images.md
- resource: docs/knowledge/data/spec/standalone-opencode-runtime.md
- resource: docs/knowledge/data/spec/devcontainer-git-credentials.md
---

# Remove the D-Bus session bus and GNOME Keyring from the runtime images

The runtime images `agentdev-devcontainer` and `agentdev-deploy` supervise a
D-Bus session bus and a GNOME Keyring Secret Service. The keyring holds only the
`gh` login token. The D-Bus bus is there only so that `gh` can reach the
keyring.

The keyring gives no security in a container:

- `gh` must run with no person to type a password. Thus the keyring must stay
  unlocked for the full life of the container.
- When the keyring is unlocked, each process of the same user can read every
  secret through the bus. The Secret Service has no access control for each
  application.
- A master password must come from inside the container, because no person types
  it when the container starts. Thus the password is in the same boundary as the
  keyring.

When `gh` finds no keyring, it keeps its token in `~/.config/gh/hosts.yml` with
mode `0600`. That file gives the same protection as the keyring in the
container. The bus and the keyring add two supervised services, the order in
which the supervisor restarts them, health checks, an image `ENV`, three
packages, and spec requirements. The image `ENV` prevents `gh` from starting a
D-Bus bus that does not stop. This problem occurs only because the images
install `dbus-x11` and `gnome-keyring`.

## Work

- Remove the `dbus` and `keyring` programs from the two `supervisord.conf`
  files. Then remove their services, dependencies, and refresh rules from the
  service tables in `agentdev_runtime/supervisor.py`.
- Remove `agentdev-runtime keyring`, its checks in `agentdev-runtime health` and
  `agentdev-runtime doctor`, the keyring-session file
  (`AGENTDEV_KEYRING_ENV_FILE`), and the step that waits for the keyring before
  the git credential configuration.
- Remove `dbus-x11`, `gnome-keyring`, and `libsecret-1-0` from `basic_prereqs`.
  Then remove `DBUS_SESSION_BUS_ADDRESS` from the two Dockerfiles.
- Make sure that Xpra starts with no session bus, or that Xpra starts its own
  bus.
- Move a `gh` token that is in an existing keyring into `hosts.yml`, or tell the
  user to do the `gh auth login` procedure again. Before you start this step,
  find which of the two actions is necessary.
- Remove or change the D-Bus and keyring requirements in
  `spec/agentdev-runtime-images`, `spec/standalone-opencode-runtime`, and
  `spec/devcontainer-git-credentials`, and the keyring terms in the glossary.

## Dependencies

None.
