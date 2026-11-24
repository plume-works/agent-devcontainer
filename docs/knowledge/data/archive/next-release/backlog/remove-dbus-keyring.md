---
type: task
created: 2026-11-14
stage: done
priority: medium
description: Remove the supervised D-Bus session bus and GNOME Keyring from the agentdev runtime images, because they give no security and their only consumer, `gh`, can keep its token in its own file.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/keyring.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/supervisor.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/git.py
- resource: ansible/roles/basic_prereqs/tasks/main.yml
- resource: docker/devcontainer/supervisord.conf
- resource: docker/deploy/supervisord.conf
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/deploy/agentdev-deploy.Dockerfile
completed: 2026-11-23
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
which the supervisor restarts them, health checks, an image `ENV`, and three
packages. The `gh` bus-autolaunch leak that the image `ENV` prevents occurs only
because the images install `dbus-x11` and `gnome-keyring`.

## Work

- Remove the `dbus` and `keyring` programs from the two `supervisord.conf`
  files, and remove their services, dependencies, and refresh rules from the
  service tables in `agentdev_runtime/supervisor.py`.
- Remove `agentdev-runtime keyring`, its checks in `agentdev-runtime health` and
  `agentdev-runtime doctor`, the keyring-session file
  (`AGENTDEV_KEYRING_ENV_FILE`), and the step that waits for the keyring before
  the git credential configuration.
- Remove `dbus-x11`, `gnome-keyring`, and `libsecret-1-0` from `basic_prereqs`,
  and remove `DBUS_SESSION_BUS_ADDRESS` from both Dockerfiles.
- Make sure that Xpra starts with no session bus, or that Xpra starts its own
  bus.
- Move a `gh` token that is in an existing keyring into `hosts.yml`, or tell the
  user to run `gh auth login` again. Find out first which of the two is
  necessary.

## Dependencies

None.
