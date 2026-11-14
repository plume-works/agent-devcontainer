---
type: adr
stage: accepted
description: The runtime images set one fixed D-Bus session bus address as an image ENV, so that each process uses the same bus.
---

# The session bus address is an image ENV

`gh` reads its token from the Secret Service at each call. When a process has no
session bus address, the D-Bus client library starts a new bus through
`dbus-launch`. The token lookup then starts a new `gnome-keyring-daemon`, and
neither process stops. Each process must get one fixed address. Only an image
`ENV` goes to all processes: supervised programs, `docker exec` shells, the VS
Code server, and agent sessions.

## Considered Options

- A random bus address in a file that scripts read. Rejected: only the processes
  that read the file use the bus. Each other `gh` call starts a bus and a
  keyring that do not stop.
