---
type: architecture
description: How an Expo consumer's devcontainer builds, installs, launches, and screenshots its iOS app on the Mac that opened it — two VS Code extensions bridged by command routing, a fixed Expo-only action set, and a consent surface rather than a security boundary.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-23T09:30:00Z
sources:
- resource: docs/knowledge/data/plans/20261015-vscode-expo-bridge.md
- resource: https://github.com/plume-works/vscode-expo-bridge
- resource: https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/protocol.md
- resource: https://docs.expo.dev/build-reference/local-builds/
- resource: https://code.visualstudio.com/api/advanced-topics/remote-extensions
---

# VS Code Expo bridge

## Context

An Expo consumer builds iOS on EAS cloud Macs from its Linux devcontainer
([Template boundary](template-boundary.md), Optional Expo profile). When VS Code
on a Mac opens that devcontainer, the Mac has Xcode and the iOS Simulator: a
build there costs no EAS quota and lets agents see the running app. The bridge
code lives in the sibling repository
[plume-works/vscode-expo-bridge](https://github.com/plume-works/vscode-expo-bridge),
which owns the protocol contract and security model in
[`docs/protocol.md`](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/protocol.md).
This repository owns only the template wiring, the EAS cloud fallback, and that
setup grants no trust.

## Approach

The extension pack `plume-works.vscode-expo-bridge` bundles two extensions:

- `plume-works.vscode-expo-bridge-host` (`extensionKind: ["ui"]`) runs in the
  Mac's local extension host with full Node.
- `plume-works.vscode-expo-bridge-workspace` (`extensionKind: ["workspace"]`)
  runs in the container. It installs `eas-host` into `~/.local/bin` and serves
  `/tmp/vscode-expo-bridge.sock`.

The Expo profile lists the pack in `customizations.vscode.extensions`, which Dev
Containers installs into the container: that brings the workspace extension, and
leaves the host extension disabled there until the user clicks its **Install
Locally**, once per Mac. In a Codespace the workspace extension activates after
one **Developer: Reload Window**.

```
 devcontainer                                 Mac host
┌──────────────────────────────┐   VS Code   ┌───────────────────────────────────┐
│ eas-host <action> ...        │   command   │ host extension (ui)               │
│   │ unix socket              │   routing   │  ├ trust + build confirmation     │
│   ▼                          │ ──────────▶ │  ├ resolves the workspace's host  │
│ workspace extension ─────────┤             │  │   path, validates arguments     │
│                              │             │  ├ eas build --local              │
│ tails the log file ◀─────────┼─workspace───┼──┤ xcrun simctl install/launch/   │
│ reads the artifact           │  directory  │  │   screenshot                   │
└──────────────────────────────┘             │  └ writes .tmp/expo-bridge/        │
                                             └───────────────────────────────────┘
```

VS Code routes a command to whichever extension host registered it, so a request
crosses from container to Mac as a JSON command argument and opens no network
port; the firewall allowlist does not change. The workspace is one directory
seen by both sides, so the build log, the artifact, and screenshots reach the
container as files under `.tmp/expo-bridge/`.

The host accepts exactly five actions — `status`, `build`, `install`, `launch`,
`screenshot` — and never runs a command string from the container. `build` runs
`eas build --local -p ios --profile <name>` for a profile that must exist in
`eas.json`; `install` takes an artifact under `.tmp/expo-bridge/`; `launch`
starts the app `install` last installed; `screenshot` captures the booted
simulator. When the bridge is unavailable, `eas-host status` exits non-zero and
the agent builds on EAS cloud. Metro runs in the container and reaches the
simulator's development build over forwarded port 8081, so the native build
reruns only when native code changes.

The host runs its processes with the Mac user's login environment, captured with
`$SHELL -l -c 'env -0'` (which fish and POSIX shells both accept), plus the
Homebrew prefixes for tool lookup, and starts each with an argument array, never
through a shell. It writes nothing Mac-specific into the shared workspace: no
`eas init`, `expo prebuild`, or package install; linking the EAS project is a
one-time step from the container.

### Security model

A devcontainer window already grants the container reach onto the Mac: through
VS Code's own commands a container-side extension opens a local terminal and
runs commands on the Mac, and the SSH and GPG agents are forwarded into the
container. The bridge cannot remove that reach and adds none beyond it. It is
therefore a **consent surface for a cooperative container, not a security
boundary**, and its one privileged action, `build`, runs only behind:

- **per-workspace trust**, granted in a Mac-side prompt naming the workspace's
  host path and stored in the host extension's `globalState`; a decline sticks
  until revoked, so a workspace cannot re-prompt;
- **a confirmation before every `build`**, naming the profile and that project
  code runs with the user's privileges, with an optional per-workspace cooldown.

Every command invocation is treated as possibly the container's: VS Code tells a
handler nothing about its caller, so pairing the two extensions is not a
boundary. No security setting is read from any file the container can write.
Outside `build`, the host never evaluates project code; it reads only `eas.json`
and `app.json` as size-limited regular JSON files. Every path is
workspace-relative and rejected when any component is a symlink, and every file
written into the workspace is created fresh with
`O_CREAT | O_EXCL | O_NOFOLLOW_ANY`; tools write into the host's private storage
and the host copies their output in. `build` sets `EAS_NO_VCS=1` so eas-cli
writes nothing in the workspace's `.git`. `EXPO_TOKEN` lives in VS Code
SecretStorage on the Mac and is placed only in the build's environment.

The build itself is not contained: a trusted, confirmed build runs project code
— lifecycle scripts, config plugins, the `Podfile`, Xcode build phases — as the
Mac user, unsandboxed. The iOS Simulator is no containment boundary either:
simulator processes run with the Mac user's file access.

### Constraints

- `eas build --local` builds in a fresh directory under the Mac's temporary
  directory with its own dependency install, so it never touches the workspace's
  Linux `node_modules`. It uses the Mac's bun and Node whatever `eas.json` pins,
  so `status` checks that the Mac's bun is at least the container's — an older
  bun cannot read the container's `bun.lock`.
- A local build does not resolve EAS "Secret" environment variables; values the
  build needs must come from the host environment.
- `cocoapods`, `fastlane`, and `image` are not `eas.json` build fields, so
  `status` probes those tools on the Mac directly.

### Rejected alternatives

- **A generic host-command bridge** such as `dc2host` — any container process
  could run anything on the Mac.
- **Wrapping `eas`** so `eas build -p ios` routes to the Mac — Expo's plugin
  skills invoke `eas` directly, and silently changing a third-party command's
  meaning is fragile.
- **`expo run:ios` on the Mac** — it builds in the shared workspace against the
  container's Linux `node_modules`.
- **A self-hosted GitHub Actions runner on the Mac** — it needs CI plumbing and
  is not reachable from an open editor window.
- **Listing only the workspace extension** in `devcontainer.json` and telling
  users to install the pack on the Mac — a window opened without that step shows
  nothing to click.
- **A host network port** — command routing needs none and leaves the firewall
  allowlist unchanged.
- **One extension with a URI handler** reached through `code --open-url` — a URI
  handler returns nothing, so results would come back only by polling files.
- **Containing the build with `sandbox-exec`** — macOS does not apply a sandbox
  inside another, and the build's own tools (SwiftPM) sandbox themselves;
  turning theirs off for one build depends on Expo's script internals, Xcode's
  script-phase `PATH`, and an undocumented Xcode default.
- **Disabling SwiftPM's manifest sandbox through global Xcode defaults** — it
  weakens every Xcode build on the Mac.
- **Building as a dedicated low-privilege macOS user** — it needs a second
  account, a sudoers rule, and a root-owned wrapper installed with the admin
  password, a standing privileged path on the Mac; and the account's home
  persists, so one hostile build can poison the next.
