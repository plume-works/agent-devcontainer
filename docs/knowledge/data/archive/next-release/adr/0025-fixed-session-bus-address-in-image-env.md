---
type: adr
stage: superseded
---

# The session bus address is an image ENV

`gh` looks its token up in the Secret Service on every call. With no session bus
address in its environment, the D-Bus client library autolaunches a new bus
through `dbus-launch`, the lookup activates a fresh `gnome-keyring-daemon`, and
neither exits. Every process (supervised programs, `docker exec` shells, the VS
Code server, agent sessions) must therefore inherit one fixed address, and only
an image `ENV` reaches them all.

## Considered Options

- A random bus address published in a file that scripts source. Rejected: only
  the processes that source the file name the bus, and every other `gh` call
  leaks a bus and a keyring.
