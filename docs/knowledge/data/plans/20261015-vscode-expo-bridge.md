---
type: plan
created: 2026-10-15
release:
- features/vscode-expo-bridge
description: A VS Code extension in the sibling repository plume-works/vscode-expo-bridge that lets agents in a devcontainer opened on a Mac build, install, launch, and screenshot an Expo iOS app on that Mac through a fixed Expo-only action set, with EAS cloud as the fallback; the template's Expo profile lists the extension.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-21T00:00:00Z
sources:
- resource: docs/knowledge/data/plans/20261014-expo-eas-template-profile.md
- resource: .devcontainer/devcontainer.json
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: https://docs.expo.dev/build-reference/local-builds/
- resource: https://github.com/expo/eas-build
- resource: https://code.visualstudio.com/api/advanced-topics/remote-extensions
---

# Build iOS on the Mac host through a VS Code bridge

## Context

The [Expo profile](20261014-expo-eas-template-profile.md) builds iOS on EAS
cloud Macs from the Linux devcontainer. When that devcontainer is opened by VS
Code on a Mac, the Mac itself has Xcode and the iOS Simulator, and a build there
costs no EAS quota and lets agents see the running app.

The pieces that make this possible:

- **`eas build --local`** runs the EAS build steps on the local machine. It
  builds in a working directory under `/tmp` with its own dependency install,
  reads the same `eas.json` profiles, and authenticates with `EXPO_TOKEN`. It
  ignores the `node`, `bun`, `cocoapods`, `fastlane`, and `image` fields of
  `eas.json`, has no build cache, and does not resolve EAS "Secret" environment
  variables. `EAS_LOCAL_BUILD_ARTIFACTS_DIR` sets where the artifact lands.
- **VS Code routes a command to whichever extension host registered it.** A `ui`
  extension runs in the Mac's local extension host with full Node; a `workspace`
  extension runs in the container. Command arguments and results cross the
  boundary as JSON.
- **The workspace is one directory on disk** seen by both sides, so a file the
  Mac writes under the workspace is visible in the container at once.

## Approach

A two-part extension, `plume-works.vscode-expo-bridge`, in the sibling
repository `plume-works/vscode-expo-bridge`:

```
 devcontainer                                 Mac host
┌──────────────────────────────┐   VS Code   ┌───────────────────────────────────┐
│ eas-host <action> ...        │   command   │ ui half                           │
│   │ unix socket              │   routing   │  ├ resolves the workspace's host  │
│   ▼                          │ ──────────▶ │  │   path, validates arguments     │
│ workspace half ──────────────┤             │  ├ eas build --local -p ios       │
│                              │             │  ├ xcrun simctl install/launch/   │
│ tails the log file ◀─────────┼─workspace───┼──┤   screenshot                   │
│ reads the artifact           │  directory  │  └ writes .tmp/expo-bridge/        │
└──────────────────────────────┘             └───────────────────────────────────┘
```

- **Fixed Expo-only protocol.** The `ui` half accepts exactly these actions:
  `status`, `build`, `install`, `launch`, `screenshot`. It never runs a command
  string from the container. `build` takes a profile name that must exist in the
  workspace's `eas.json`; `install` takes a workspace-relative path that must
  resolve under `.tmp/expo-bridge/`; `launch` reads the bundle identifier from
  the app config; `screenshot` takes no argument. Every path in the protocol is
  workspace-relative; the `ui` half resolves it against the host path.
- **`status`** reports whether the bridge can serve a build: a Mac host, a
  workspace host path that exists locally, Xcode, CocoaPods, fastlane, Node, a
  host bun at least as new as the container's (the container sends its
  `bun --version`), `EXPO_TOKEN` in the host environment, a booted simulator,
  whether port 8081 is forwarded, and the protocol version.
- **Nothing Mac-specific lands in the shared workspace.** The `ui` half never
  runs `expo run:ios`, `expo prebuild`, or a package install in the workspace;
  the only files it writes there are under `.tmp/expo-bridge/` — logs, build
  artifacts, screenshots.
- **One-click fix.** When `status` finds a missing tool, the `ui` half offers a
  fix in the VS Code UI that runs Homebrew in a visible local terminal. Xcode is
  a guided step (it opens the App Store page), after which the fix runs
  `xcode-select`, accepts the license, and downloads the iOS platform. A fix is
  only ever started by the user's click, never by a protocol action.
- **`eas-host`** is the container-side command. The workspace half installs it
  into `~/.local/bin` on activation and listens on a fixed socket; it streams
  the build log by tailing the log file the `ui` half writes. When the bridge is
  unavailable, `eas-host status` says so and exits non-zero, and the agent uses
  the Expo profile's EAS cloud path.
- **Dev-client loop.** Metro runs in the container; VS Code forwards port 8081
  to the Mac, where the simulator's development build connects to it, so the
  native build reruns only when native code changes.
- **Template wiring.** The Expo profile lists the extension, forwards 8081, and
  adds an `AGENTS.md` rule telling agents to use `eas-host` for iOS when
  `eas-host status` succeeds.

The protocol is specified in the sibling repository, which owns the code; this
repository's spec covers only the template wiring and the fallback.

Rejected: a generic host-command bridge such as `dc2host` — any process in the
container could run anything on the Mac. Rejected: wrapping `eas` so that
`eas build -p ios` routes to the Mac — Expo's plugin skills call `eas` directly,
and silently changing a third-party command's meaning is fragile. Rejected:
`expo run:ios` on the Mac — it builds in the shared workspace against the
container's Linux `node_modules`. Rejected: a self-hosted GitHub Actions runner
on the Mac — it needs CI plumbing and is not available from an open editor
window. Rejected: a host network port — the protocol travels over VS Code's
command routing, so the firewall allowlist does not change.

Assumptions:

- The socket is `/tmp/vscode-expo-bridge.sock` inside the container; one VS Code
  window serves one container.
- The workspace half activates on `workspaceContains:eas.json`.
- No per-action confirmation prompt: the fixed action set is the security
  boundary.
- The first workspace folder is the Expo project root.
- CocoaPods and fastlane are owned by the one-click fix, not by the [macOS
  bootstrap](20261013-macos-native-bootstrap.md).

## Implementation Steps

### Task 1: Spike the bridge end to end

**Files:** Create: a scratch extension outside both repositories

- [ ] A container-side command calls a `ui`-side command through
  `vscode.commands.executeCommand`, and the `ui` side resolves the workspace's
  host path from the remote window.
- [ ] The `ui` side runs `eas build --local -p ios --profile development` for an
  `ios.simulator: true` profile on a blank `bun create expo` app, and the
  artifact is readable in the container.

### Task 2: Spike the `eas build --local` behavior the design relies on

**Files:** none — run against the Task 1 scratch app on a Mac

- [ ] The build runs outside the workspace: the workspace's `node_modules` is
  unchanged and no `ios/` directory appears in it.
- [ ] `EAS_LOCAL_BUILD_ARTIFACTS_DIR` set to `.tmp/expo-bridge/` places the
  artifact there.
- [ ] The build uses the host's bun regardless of the `bun` field in `eas.json`,
  as the build log reports.
- [ ] `EXPO_TOKEN` in the host environment authenticates the build with no
  `eas login`.
- [ ] An EAS environment variable with "Secret" visibility is absent from the
  build, and the same variable set in the host environment is present.
- [ ] The built app contains a change to a tracked file that was not committed
  and a new untracked file. When either is missing, find the eas-cli setting
  that includes them.
- [ ] Any check that fails is recorded under `## Verification results` and the
  plan goes back to revise before Task 6.

### Task 3: Spike how Expo's plugin skills invoke `eas`

**Files:** none — read `expo/skills`

- [x] Every build command in the skills of `expo@claude-plugins-official` is a
  direct `eas` invocation with no configurable command or hook; when one exists,
  record it under `## Verification results` and take the separate-command
  decision back to revise before Task 6.
  - **Evidence:** `anthropics/claude-plugins-official` pins `expo` to
    `expo/skills@d4f484024fec15196bfd3c272e953e3f983972cf` (`plugins/expo`). At
    that commit, the 29 build invocations across 12 files in
    `plugins/expo/skills/` are literal `eas build …` or
    `npx eas-cli@latest build …`. `hooks/hooks.json` holds only the
    `skill-event.cjs` telemetry hooks (`PostToolUse` on `Skill`,
    `UserPromptExpansion`), and `.mcp.json` only `mcp.expo.dev`. No configurable
    command exists.

### Task 4: Create the sibling repository

**Files:** Create: `plume-works/vscode-expo-bridge` on GitHub

- [ ] The repository exists with an MIT license, a bun-managed TypeScript
  extension skeleton, and `package.json` declaring `plume-works` as publisher.

### Task 5: Specify the protocol in the sibling repository

**Files:** Create: `docs/protocol.md` in `plume-works/vscode-expo-bridge`

- [ ] It defines the five actions, their arguments and validation, the result
  and error shapes, workspace-relative paths, the `.tmp/expo-bridge/` write
  boundary, the protocol version and how `status` reports a mismatch, and that
  fixes are never protocol actions.

### Task 6: Workspace half and `eas-host`

**Files:** Create: in `plume-works/vscode-expo-bridge`

- [ ] The workspace half activates on `workspaceContains:eas.json`, installs
  `eas-host` into `~/.local/bin`, and serves `/tmp/vscode-expo-bridge.sock`.
- [ ] `eas-host` maps each action to one socket request, streams the build log,
  prints the result as JSON, and exits non-zero when the bridge is unavailable
  or the action fails.
- [ ] `bun test` covers argument handling, the unavailable path, and log
  streaming.

### Task 7: `ui` half — `status`

**Files:** Create: in `plume-works/vscode-expo-bridge`

- [ ] `status` reports every check in `## Approach`, and reports unavailable on
  a non-Mac host and when the workspace host path does not exist locally.
- [ ] `bun test` covers each check's pass and fail result with the system probes
  stubbed.

### Task 8: `ui` half — `build`

**Files:** Create: in `plume-works/vscode-expo-bridge`

- [ ] `build` rejects a profile absent from `eas.json`, runs
  `eas build --local -p ios --profile <name>` with the artifact and log under
  `.tmp/expo-bridge/`, and returns the artifact's workspace-relative path and
  the exit code.
- [ ] `bun test` covers profile validation and the command line built, with
  process spawning stubbed.

### Task 9: `ui` half — `install`, `launch`, `screenshot`

**Files:** Create: in `plume-works/vscode-expo-bridge`

- [ ] `install` rejects a path outside `.tmp/expo-bridge/`, unpacks the
  artifact, and installs it on the booted simulator; `launch` starts the app by
  the bundle identifier from the app config; `screenshot` writes a PNG under
  `.tmp/expo-bridge/` and returns its workspace-relative path.
- [ ] `bun test` covers path validation and the `xcrun simctl` invocations.

### Task 10: One-click fix

**Files:** Create: in `plume-works/vscode-expo-bridge`

- [ ] For each failing `status` check that a tool install resolves, the VS Code
  UI offers a fix that runs the Homebrew command in a visible local terminal;
  for Xcode it opens the App Store page and then runs `xcode-select`, the
  license acceptance, and `xcodebuild -downloadPlatform iOS`.
- [ ] No protocol action can start a fix.

### Task 11: Sibling repository CI

**Files:** Create: `.github/workflows/` in `plume-works/vscode-expo-bridge`

- [ ] A workflow runs lint, `bun test`, and a VSIX package build on every pull
  request, and passes on `main`.

### Task 12: Publish to the Visual Studio Marketplace

- [ ] `plume-works.vscode-expo-bridge` is installable from the Visual Studio
  Marketplace.

### Task 13: Publish to Open VSX

- [ ] `plume-works.vscode-expo-bridge` is installable from Open VSX.

### Task 14: Wire the bridge into the Expo profile

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [ ] `## Optional Expo setup` adds `plume-works.vscode-expo-bridge` to
  `customizations.vscode.extensions` and `8081` to `forwardPorts` in the
  consumer's `.devcontainer/devcontainer.json`.
- [ ] The `## Expo` section of the merged `AGENTS.md` gains a rule: for an iOS
  build, run `eas-host status`; when it succeeds use `eas-host`, otherwise use
  EAS cloud.

### Task 15: Record the bridge in the template boundary and architecture

**Files:** Modify: `docs/knowledge/data/architecture/template-boundary.md`;
Create: `docs/knowledge/data/architecture/vscode-expo-bridge.md`; Modify:
`docs/knowledge/data/architecture.md`

- [ ] The template boundary's Expo profile section names the extension, the
  forwarded port, and the `AGENTS.md` rule.
- [ ] `data/architecture/vscode-expo-bridge` records the design in `## Approach`
  with its rejected alternatives and links the sibling repository's protocol
  document; `data/architecture.md` links it.

### Task 16: Validate the catalog change

- [ ] `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.

### Task 17: End to end on a Mac

- [ ] In an Expo consumer adopted with the Expo profile and opened by VS Code on
  a Mac, an agent runs `eas-host status`, `build` for a simulator profile,
  `install`, `launch`, and `screenshot`, and reads the screenshot from the
  container.
- [ ] With Metro running in the container, the launched development build loads
  the JavaScript bundle over forwarded port 8081.

### Task 18: Fallback when the bridge is unavailable

- [ ] In a Codespace of the same consumer opened by VS Code on a Mac,
  `eas-host status` reports unavailable and exits non-zero, and
  `bunx eas-cli@latest build -p ios --non-interactive --no-wait` still submits
  to EAS cloud.

## Spec changes

Modifies [Template consumption](../spec/template-consumption.md):

``` markdown
## ADDED Requirements

### Requirement: an Expo consumer can build iOS on a Mac host through the bridge

When the consumer's `optional_bundles` includes `"expo"`, setup SHALL list
`plume-works.vscode-expo-bridge` in `customizations.vscode.extensions`, add
`8081` to `forwardPorts`, and add to the `## Expo` section of the root
`AGENTS.md` a rule that an iOS build uses `eas-host` when `eas-host status`
succeeds and EAS cloud otherwise. Setup SHALL NOT add any host command bridge
other than this extension, and SHALL NOT change the firewall allowlist for it.

#### Scenario: an Expo consumer is opened by VS Code on a Mac

- **WHEN** an Expo consumer's devcontainer is opened by VS Code on a Mac with
  the extension installed and the tools `eas-host status` checks present
- **THEN** `eas-host status` succeeds
- **AND** `eas-host build` with a profile from `eas.json` leaves the artifact
  under `.tmp/expo-bridge/`

#### Scenario: the bridge is unavailable

- **WHEN** the devcontainer runs where the workspace is not on the VS Code host
  — a Codespace, a non-Mac host, or no VS Code window
- **THEN** `eas-host status` exits non-zero
- **AND** the EAS cloud build path works unchanged

#### Scenario: a non-Expo consumer

- **WHEN** the consumer's `optional_bundles` omits `"expo"`
- **THEN** setup adds neither the extension, the forwarded port, nor the rule
```

The protocol contract is specified in `plume-works/vscode-expo-bridge`
(`docs/protocol.md`), not in this repository.

## Depends on

- [Expo profile for template adoption](20261014-expo-eas-template-profile.md) —
  Task 14 extends its `## Optional Expo setup` section and its `## Expo`
  `AGENTS.md` section.

## Verification

- The Task 1–3 spikes pass, or their findings have been taken back to revise.
- The sibling repository's CI passes on `main`.
- The extension installs from both the Visual Studio Marketplace and Open VSX.
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.
- Task 17's end-to-end run and Task 18's fallback run behave as described.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Android builds through the bridge; the container builds Android itself.
- Device and store builds that need Apple signing; the bridge covers simulator
  builds, and `eas credentials` stays a one-time human step.
- A generic host-command facility.
- Hosts other than VS Code desktop on macOS, and editors that cannot run a `ui`
  extension locally.
- Changes to this repository's own `.devcontainer/`.
- Installing Xcode itself unattended.

## Key references

Verified anchor points (line numbers as of 2026-10-20):

- `.devcontainer/devcontainer.json:53` — `forwardPorts`
- `.devcontainer/devcontainer.json:115` — `customizations.vscode.extensions`
- `.devcontainer/docker-compose.yml:84` — the workspace bind mount at
  `/workspaces/<basename>`
- `.gitignore:11` — `.tmp/` ignored
- `ansible/roles/bash_setup/tasks/main.yml:3` — `~/.local/bin` on `PATH`
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:50` —
  `optional_bundles` row of the marker table
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:928`
  — `## Optional Expo setup`
- `docs/knowledge/data/architecture/template-boundary.md:256` —
  `## Optional Expo profile`
- `docs/knowledge/data/spec/template-consumption.md:82` — Requirement: adoption
  is recorded for later updates
