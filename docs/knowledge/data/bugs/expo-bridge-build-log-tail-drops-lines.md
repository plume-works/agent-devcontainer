---
type: bug
description: The Expo bridge's build log tail drops the lines written in the last poll interval before a build returns, and the start of any line it reads before the line's newline arrives.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-26T20:40:00Z
sources:
- resource: https://github.com/plume-works/vscode-expo-bridge
- resource: docs/knowledge/data/architecture/vscode-expo-bridge.md
---

# Bug: the Expo bridge's build log tail drops lines

## Symptom

`eas-host build` streams the host's build log to stderr while the build runs.
That stream loses lines in two ways:

- the lines eas-cli writes in roughly the last 250 ms before the build's
  response arrives never print;
- a line that is only partly written when a poll reads it prints only the part
  written after that poll.

The log file under `.tmp/expo-bridge/` is complete. Only the stream is affected.

## Reproduction

Call `tailLog` on an empty file, then:

1. append `one\nhal`;
2. wait 400 ms;
3. append `f\nlast\n`;
4. call the returned `stop()` at once.

The callback receives `["one"]`. Expected: `["one", "half", "last"]`.

## Root cause

`tailLog` has two faults:

- **The stop flush is a no-op.** `stop()` sets `closed = true` before its final
  `read()`, and `read()` returns early when `closed` is set.
- **Partial lines are thrown away.** `read()` advances `offset` past every byte
  it read, but passes on only the complete lines (`split("\n").slice(0, -1)`).
  The bytes of a partial line are dropped and never read again.

Both faults predate the workspace UI. The code moved unchanged from
`packages/workspace/src/extension.ts` to `requests.ts`, and the panel's
`Expo Bridge Build` output channel inherits them.

## Fix

Not fixed. `read()` should keep an unterminated tail and prepend it to the next
read. `stop()` should run its final `read()` before setting `closed`, and then
emit any tail that is left.

## Key references

Verified anchor points (line numbers as of 2026-10-26):

In `plume-works/vscode-expo-bridge` at `cce47ba`:

- `packages/workspace/src/requests.ts:25` — `tailLog`; `:29` — the `closed`
  early return; `:37` — the complete-lines split; `:45` — `stop()` setting
  `closed` before the final `read()`
- `packages/workspace/src/requests.ts:73` — `runRequest`, which calls `stopTail`
  when the build's response arrives
