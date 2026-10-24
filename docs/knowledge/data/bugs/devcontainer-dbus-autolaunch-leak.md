---
type: bug
stage: done
description: In the devcontainer, processes started outside a shell that sourced the keyring session had no DBUS_SESSION_BUS_ADDRESS, so every gh call autolaunched a session bus and a gnome-keyring-daemon that never exited; a fixed containerEnv address now gives every process the one bus setup-keyring.sh starts.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-24T02:48:59Z
sources:
- resource: .devcontainer/devcontainer.json
- resource: .devcontainer/scripts/setup-keyring.sh
- resource: .devcontainer/scripts/setup-gh-credential-helper.sh
- resource: scripts/tests/test_agent_runtime_keyring.py
---

# Bug: every gh call in the devcontainer leaks a D-Bus session and a keyring

## Symptom

A long-running devcontainer accumulates orphaned root processes in pairs: one
`dbus-daemon --syslog --fork --print-pid 5 --print-address 7 --session` and one
`gnome-keyring-daemon --start --foreground --components=secrets`, both
reparented to PID 1. An agent session that polled GitHub through `gh` once a
minute left about 620 pairs in a day. Each pair keeps its memory until the
container stops.

## Reproduction

1. In the devcontainer, from a process that did not source
   `.tmp/keyring-session.env` (an agent's tool shell, for example), confirm
   `DBUS_SESSION_BUS_ADDRESS` is unset and `DISPLAY` is `:100`.
2. Count `pgrep -c dbus-daemon`, run `gh auth status`, and count again: one more
   bus.
3. Repeat with `DBUS_SESSION_BUS_ADDRESS=disabled:`: `gh` still authenticates,
   and no bus is added.

## Root cause

`gh` looks its token up in the Secret Service on every call. With no session bus
address in its environment, the D-Bus client library autolaunches a new session
bus through `dbus-launch`, and the lookup then activates a fresh
`gnome-keyring-daemon` on it. Neither exits when `gh` does.

`setup-keyring.sh` started the devcontainer's real bus at a random address and
published it only in `.tmp/keyring-session.env`, which only
`setup-gh-credential-helper.sh` sources. The VS Code server, agent sessions, and
every process they start inherit the container environment, which named no bus.

## Fix

`devcontainer.json` sets `DBUS_SESSION_BUS_ADDRESS` in `containerEnv` to the
fixed `unix:path=/tmp/agentdev-dbus/bus`, so every process names the same bus.
`setup-keyring.sh` starts its bus at that address when one is given, reuses a
live bus there, replaces a stale socket, and skips restoring a saved random
session. With no address in its environment it keeps its previous behavior. The
standalone runtime already uses a fixed address from `runtime-keyring.sh`.

`test_a_fixed_address_gets_one_bus_that_every_client_reuses` starts the bus over
a stale socket, reruns setup to show the bus is reused, and has a client with
`DISPLAY` set store and read a secret through it.

## Key references

Verified anchor points (line numbers as of 2026-10-24):

- `.devcontainer/devcontainer.json:28` — the fixed `DBUS_SESSION_BUS_ADDRESS`
- `.devcontainer/scripts/setup-keyring.sh:38` — the fixed address is detected;
  `:48` — `load_saved_session`, skipped for it; `:103` — the stale socket is
  replaced and the bus started at the address
- `.devcontainer/scripts/setup-gh-credential-helper.sh:11` — the only consumer
  of the saved session file
- `scripts/tests/test_agent_runtime_keyring.py:216` — the fixed-address test
