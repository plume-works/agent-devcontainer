---
type: bug
description: The container does not see the Mac's build log grow while the host holds it open, so the Expo bridge streams no build log lines; the log appears only when the build ends and the host closes it.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-27T12:00:00Z
sources:
- resource: https://github.com/plume-works/vscode-expo-bridge
- resource: docs/knowledge/data/plans/20261026-expo-bridge-panel.md
- resource: docs/knowledge/data/bugs/expo-bridge-build-log-tail-drops-lines.md
---

# Bug: the container sees the Expo bridge's build log only after the build ends

## Symptom

A build started from the workspace panel or from `eas-host build` streams none
of the eas-cli output while the build runs. The panel's `Expo Bridge Build`
channel shows only its header line and the result line. The log file under
`.tmp/expo-bridge/` is complete afterwards.

## Reproduction

On an Apple silicon Mac with Docker Desktop and 0.4.0 of the bridge, in an Expo
consumer's Dev Containers window:

1. In a container terminal, print `date +%s.%N` and
   `stat -c 'size=%s mtime=%.Y'` of the newest `.tmp/expo-bridge/build-*.log`
   once a second.
2. Start a clean build from the panel.

The log appears within a second of its creation with the bytes of the host's
first `expo-bridge:` lines (147). Its size and mtime then stay fixed for the
whole build (about 100 s) and jump to the full log (59331 bytes) when the build
ends. The container's clock and the log's mtime agree to within a second.

## Root cause

The host writes the log through one file descriptor it opens at the start of a
build and closes at the end, with a `writeSync` per eas-cli output chunk. Over
Docker Desktop's file sharing of the Mac folder, the container sees the
attributes the file had when the writer last opened or closed it, so `fstat` in
`tailLog` keeps returning the size at creation. `tailLog` reads only up to that
size, and its final flush is a no-op ([the build log tail drops
lines](expo-bridge-build-log-tail-drops-lines.md)), so no eas-cli line is ever
passed on.

Eliminated: clock skew between the Mac and the container. `newestBuildLog`
filters on `mtimeMs >= since`, but the measured skew is under a second and the
log was found.

## Fix

Not fixed. Polling the file from the container cannot follow a log the Mac holds
open. The log must reach the container another way while the build runs, or the
host must write it so that each write becomes visible.

## Key references

Verified anchor points (line numbers as of 2026-10-27):

In `plume-works/vscode-expo-bridge` at `530b160`:

- `packages/host/src/build.ts:88` — the log opened once per build; `:160` —
  `writeSync` per eas-cli output chunk; `:180` — the only `closeSync`
- `packages/workspace/src/requests.ts:25` — `tailLog`; `:32` — the `fstat` whose
  size stays fixed; `:51` — `newestBuildLog`
