---
type: bug
description: The Expo bridge's one-click fix opens its Mac terminal with a shell path taken from the container's detected terminal profiles, so it fails to launch when the Mac's default profile name matches a container profile whose path does not exist on the Mac.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-23T08:30:00Z
sources:
- resource: https://github.com/plume-works/vscode-expo-bridge
- resource: https://github.com/microsoft/vscode/blob/main/src/vs/workbench/contrib/terminal/browser/terminalProcessManager.ts
- resource: https://github.com/microsoft/vscode/blob/main/src/vs/workbench/contrib/terminal/browser/terminalProfileService.ts
- resource: docs/knowledge/data/plans/20261015-vscode-expo-bridge.md
---

# Bug: the Expo bridge's fix terminal launches the container's shell on the Mac

## Symptom

In `plume-works.vscode-expo-bridge-host` 0.2.0, picking a one-click fix in a Dev
Containers window on a Mac shows "The terminal process failed to launch: Path to
shell executable "/usr/bin/fish" does not exist." No fix command runs, and the
status bar item stays until a later `status` finds nothing to fix.

## Reproduction

1. On a Mac whose `terminal.integrated.defaultProfile.osx` names a profile, such
   as `fish`, that VS Code also detects in the container, open a Dev Containers
   window on an Expo consumer of the agent-devcontainer template, whose image
   has `/usr/bin/fish`, with the host extension installed locally.
2. In the container, make `status` fail a fixable check, for example by putting
   a `bun` that prints `99.0.0` first on `PATH` and running `eas-host status`.
3. Click the Expo Bridge status bar item and pick the fix.

A container with no profile of that name, such as
`mcr.microsoft.com/devcontainers/javascript-node:22`, opens the fix terminal
with the Mac's own shell.

## Root cause

The host extension creates the fix terminal with a `file:` cwd and no shell
path, so VS Code launches it on the Mac and resolves its shell from the default
profile. `TerminalProcessManager` takes the remote authority from the cwd and,
for a local launch, resolves with `os: OS`, the Mac.
`TerminalProfileService.getDefaultProfile(os)` reads
`terminal.integrated.defaultProfile.osx` and looks that name up in
`availableProfiles`, which `_detectProfiles` fetches from the window's primary
backend, the container. A matching container profile supplies its container
path, which the Mac does not have.

## Fix

Unfixed. The host extension can pass the Mac login shell it already resolves
(`$SHELL`, `/bin/zsh` when unset) as `shellPath` to `createTerminal`; VS Code
resolves an explicit executable without the default-profile lookup.

## Key references

Verified anchor points (line numbers as of 2026-10-23):

- `plume-works/vscode-expo-bridge` `packages/host/src/extension.ts:290` —
  `vscode.window.createTerminal` for the fix, with a `file:` cwd and no
  `shellPath`
- `plume-works/vscode-expo-bridge` `packages/host/src/env.ts:38` — the login
  shell, `process.env.SHELL ?? "/bin/zsh"`
- `microsoft/vscode`
  `src/vs/workbench/contrib/terminal/browser/terminalProcessManager.ts:183` —
  remote authority from the cwd; `:524` — `_launchLocalProcess` resolves with
  `os: OS`
- `microsoft/vscode`
  `src/vs/workbench/contrib/terminal/browser/terminalProfileService.ts:117` —
  `getDefaultProfile`, by name in `availableProfiles`; `:203` — profiles
  detected from the primary backend
