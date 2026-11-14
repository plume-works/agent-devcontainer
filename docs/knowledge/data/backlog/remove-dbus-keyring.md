---
type: task
created: 2026-11-14
stage: pending
priority: medium
description: Remove the supervised D-Bus session bus and GNOME Keyring from the agentdev runtime images, because they give no security and their only consumer, gh, can keep its token in its own file.
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
  it at start. Thus the password is in the same boundary as the keyring.

When `gh` finds no keyring, it keeps its token in `~/.config/gh/hosts.yml` with
mode `0600`. That file gives the same protection as the keyring in the
container. The bus and the keyring add two supervised services, a restart chain,
health checks, an image `ENV`, three packages, and spec requirements. The `gh`
bus-autolaunch leak that the image `ENV` prevents occurs only because `dbus-x11`
and `gnome-keyring` are installed.

## Work

- Remove the `dbus` and `keyring` programs from both `supervisord.conf` files,
  and remove their services, dependencies, and refresh rules from the supervisor
  service tables.
- Remove `agentdev-runtime keyring`, its health and doctor checks, the
  keyring-session file (`AGENTDEV_KEYRING_ENV_FILE`), and the keyring wait
  before git credential setup.
- Remove `dbus-x11`, `gnome-keyring`, and `libsecret-1-0` from `basic_prereqs`,
  and remove `DBUS_SESSION_BUS_ADDRESS` from both Dockerfiles.
- Make sure that Xpra starts with no session bus, or that Xpra starts its own
  bus.
- Move a `gh` token that is in an existing keyring into `hosts.yml`, or tell the
  user to log in again. Find out which one is necessary first.
- Remove or change the D-Bus and keyring requirements in
  `spec/agentdev-runtime-images`, `spec/standalone-opencode-runtime`, and
  `spec/devcontainer-git-credentials`, and the keyring terms in the glossary.

## Dependencies

None.
