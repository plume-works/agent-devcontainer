---
type: feature
stage: accepted
description: Agents in a devcontainer opened by VS Code on a Mac build, install, launch, and screenshot an Expo iOS app on that Mac through the vscode-expo-bridge extension's fixed Expo-only action set, with EAS cloud as the fallback.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-21T00:00:00Z
sources:
- resource: docs/knowledge/data/plans/20261015-vscode-expo-bridge.md
- resource: https://github.com/plume-works/vscode-expo-bridge
---

# VS Code Expo bridge

## Purpose

[Expo apps build for iOS through EAS](expo-eas-builds.md) from the Linux
devcontainer on Expo's cloud Macs. When VS Code opens that devcontainer on a
Mac, the Mac already has Xcode and the iOS Simulator; building there costs no
EAS quota and lets agents see the running app.

## Behaviour

**Two extensions in one pack.** `plume-works.vscode-expo-bridge`, built in its
own repository, bundles a workspace extension in the container and a host
extension on the Mac. The workspace extension installs the `eas-host` command;
the host extension runs the work.

**A fixed action set.** `eas-host` accepts only `status`, `build`, `install`,
`launch`, and `screenshot`. The Mac half never runs a command string from the
container, and writes into the workspace only under `.tmp/expo-bridge/`.

**Trust lives on the Mac.** A devcontainer window already lets the container
reach the Mac through VS Code itself, so the bridge does not try to contain the
container; it adds no reach beyond that and gates its own build behind a person
on the Mac. The first request from a workspace asks the user on the Mac to trust
it; every build asks again, with "Don't ask for an hour" and "Don't ask today"
answers, and runs with the Mac user's own privileges. `EXPO_TOKEN` lives in VS
Code's secret storage on the Mac.

**Dev-client loop.** Metro runs in the container and VS Code forwards port 8081
to the Mac, so the native build reruns only when native code changes.

**Template wiring.** The Expo profile lists the extension, forwards port 8081,
and tells agents to use `eas-host` for iOS when `eas-host status` succeeds.

## Edge cases

- **The bridge is unavailable** — not a Mac, or a tool missing.
  `eas-host status` says so and exits non-zero, and agents use EAS cloud builds.
- **A Mac tool is missing.** The extension offers a one-click fix in the VS Code
  UI; a fix runs only on the user's click, never from a protocol action.
- **Signed device and store builds** are not covered; the bridge builds for the
  simulator.

## Open questions

None — the plan settles the design.

## References

- Plan: [Build iOS on the Mac host through a VS Code
  bridge](../plans/20261015-vscode-expo-bridge.md)
