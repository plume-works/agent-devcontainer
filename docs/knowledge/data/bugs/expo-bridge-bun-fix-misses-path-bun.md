---
type: bug
description: The Expo bridge's bun fix installs Homebrew's bun, but the bun check runs the first bun on the Mac's login PATH, so a stale bun.sh install ahead of Homebrew keeps the fix offered forever.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-24T14:00:00Z
sources:
- resource: https://github.com/plume-works/vscode-expo-bridge
- resource: docs/knowledge/data/architecture/vscode-expo-bridge.md
---

# Bug: the Expo bridge's bun fix upgrades a bun the check never runs

## Symptom

In `plume-works.vscode-expo-bridge-host` 0.2.4 on a Mac, the status bar keeps
offering "Install or update bun — Mac bun 1.4.3 is older than the container's
1.4.4" after the fix runs. The fix terminal prints
`Warning: oven-sh/bun/bun 1.4.4 is already installed and up-to-date.`

## Reproduction

1. On a Mac, install bun through the bun.sh installer (`~/.bun/bin/bun`) at a
   version older than the container's, and Homebrew's `oven-sh/bun/bun` at the
   container's version, with `~/.bun/bin` ahead of `/opt/homebrew/bin` on the
   login shell's `PATH`. `which -a bun` lists `~/.bun/bin/bun` first.
2. Open a Dev Containers window on an Expo consumer of the agent-devcontainer
   template, with the host extension installed locally, and let `status` run.
3. Pick the bun fix from the Expo Bridge status bar item. The notice stays.

## Root cause

The bun check runs `lookupTool("bun", env)`, the first `bun` on the captured
login `PATH`. `withHomebrewPath` prepends the Homebrew prefixes only when the
`PATH` lacks them, so a login `PATH` that already lists `/opt/homebrew/bin`
after `~/.bun/bin` keeps the bun.sh copy first. The fix's only command is
`brew install oven-sh/bun/bun`, which changes Homebrew's copy and leaves the
binary the check runs untouched.

## Fix

Unfixed. The fix step needs to act on the bun the check resolved, for example
`bun upgrade` when that bun is not under a Homebrew prefix, and the check's
detail could name the resolved path.

## Key references

Verified anchor points (line numbers as of 2026-10-24):

In `plume-works/vscode-expo-bridge` at `8d8b77c`:

- `packages/host/src/fix.ts:54` — the bun fix step; `:58` — its only command,
  `brew install oven-sh/bun/bun`
- `packages/host/src/status.ts:37` — `toolVersion`, which runs the first match
  of `lookupTool`; `:106` — the bun check; `:112` — the "older than the
  container's" detail
- `packages/host/src/env.ts:26` — `withHomebrewPath`, which prepends only
  missing prefixes; `:49` — `lookupTool`, first match on `PATH`
- `packages/host/src/extension.ts:122` — `captureLoginEnv()`, the environment
  the checks run in
