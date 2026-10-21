---
type: plan
created: 2026-10-15
release:
- features/vscode-expo-bridge
description: Two VS Code extensions in the sibling repository plume-works/vscode-expo-bridge, bundled as one extension pack, that let agents in a devcontainer opened on a Mac build, install, launch, and screenshot an Expo iOS app on that Mac through a fixed Expo-only action set — trusted per workspace on the Mac, confirmed per build, and built unsandboxed as the Mac user — with EAS cloud as the fallback; the template's Expo profile lists the pack.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-21T18:00:00Z
sources:
- resource: docs/knowledge/data/plans/20261014-expo-eas-template-profile.md
- resource: .devcontainer/devcontainer.json
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: https://docs.expo.dev/build-reference/local-builds/
- resource: https://github.com/expo/eas-build
- resource: https://code.visualstudio.com/api/advanced-topics/remote-extensions
- resource: https://github.com/plume-works/vscode-expo-bridge
- resource: https://blog.theredguild.org/leveraging-vscode-internals-to-escape-containers/
- resource: https://github.com/microsoft/vscode/issues/287765
- resource: https://developer.apple.com/videos/play/wwdc19/418/
---

# Build iOS on the Mac host through a VS Code bridge

## Context

The [Expo profile](20261014-expo-eas-template-profile.md) builds iOS on EAS
cloud Macs from the Linux devcontainer. When that devcontainer is opened by VS
Code on a Mac, the Mac itself has Xcode and the iOS Simulator, and a build there
costs no EAS quota and lets agents see the running app. The user-facing behavior
is the [VS Code Expo bridge](../features/vscode-expo-bridge.md) feature.

The pieces that make this possible:

- **`eas build --local`** (eas-cli 25.3.0) runs the EAS build steps on the local
  machine. It builds in a working directory under macOS's `$TMPDIR` with its own
  dependency install, reads the same `eas.json` profiles, and authenticates with
  `EXPO_TOKEN`. It uses the host's bun whatever the `bun` field of `eas.json`
  says, and does not resolve EAS "Secret" environment variables.
  `EAS_LOCAL_BUILD_ARTIFACTS_DIR` sets where the artifact lands. It packs
  uncommitted and untracked files with default settings. It runs project code on
  the build machine: package lifecycle scripts, `eas-build-*` hooks,
  `app.config.js`, config plugins, the `Podfile`, and Xcode build phases.
- **`eas init` writes `extra.eas.projectId` into `app.json`**, a tracked project
  file.
- **VS Code routes a command to whichever extension host registered it.** A `ui`
  extension runs in the Mac's local extension host with full Node; a `workspace`
  extension runs in the container. One extension runs in exactly one host.
  Command arguments and results cross the boundary as JSON. A container-side
  extension reaches the Mac through VS Code's own commands — a local terminal,
  the clipboard — regardless of any extension the bridge installs.
- **The workspace is one directory on disk** seen by both sides, so a file the
  Mac writes under the workspace is visible in the container at once. The
  container can also place symlinks in it that resolve anywhere on the Mac.
- **The Mac user's login shell may be fish** or another shell that does not
  accept POSIX `sh` syntax.

## Approach

Two extensions in the sibling repository `plume-works/vscode-expo-bridge`,
bundled by the extension pack `plume-works.vscode-expo-bridge`:

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

**Security model.** A devcontainer window already grants the container reach
onto the Mac that the bridge neither adds nor can take away: through VS Code's
own commands a container-side extension opens a local terminal and runs a
command on the Mac, and the SSH and GPG agents are forwarded into the container.
The bridge therefore does not contain a hostile container — nothing a workspace
extension can install does. It is a consent surface, not a security boundary: it
adds no reach beyond what the window already grants, and its one privileged
action, `build`, runs project code on the Mac only behind per-workspace trust
and a per-build confirmation. The host extension treats every command invocation
as possibly the container's, whichever extension sent it, so pairing the two
extensions is not a boundary. The protocol document specified in Task 11 states
the model this way — a consent surface for a cooperative container — and does
not claim to defend against a hostile one. The checks are these:

- **Fixed Expo-only protocol.** The host extension accepts exactly these
  actions: `status`, `build`, `install`, `launch`, `screenshot`. It never runs a
  command string from the container. `build` takes a profile name that must
  exist in the workspace's `eas.json`; `install` takes a workspace-relative path
  that must resolve under `.tmp/expo-bridge/`; `launch` takes no argument and
  starts the app `install` last installed, by the `CFBundleIdentifier` in that
  artifact's `Info.plist`; `screenshot` takes no argument.
- **Per-workspace trust, granted only on the Mac.** The first request from a
  workspace with no recorded decision shows a VS Code prompt naming the
  workspace's host path. Allowing it records trust in the host extension's
  `globalState`, keyed by host path; declining fails the request. A command
  lists and revokes trusted workspaces. Trust and every other security setting
  are never read from workspace settings, `devcontainer.json`, or any other file
  the container can write.
- **A confirmation before every `build`.** The prompt names the profile and
  states that project code will run on the Mac with the user's privileges. Its
  answers are "Allow once", "Don't ask for an hour", and "Don't ask today"; a
  cooldown applies to that workspace only and is stored in `globalState`.
  `status`, `install`, `launch`, and `screenshot` never prompt beyond trust.
- **No containment of the build.** `build` runs
  `eas build --local -p ios --profile <name>` as the Mac user, unsandboxed, with
  no privileged setup on the Mac. Project code in the build can do anything the
  user can. Trust and the build confirmation are the only gate on it.
- **No project code outside `build`.** The host extension never evaluates
  `app.config.js` or any other project file as code. It reads only `eas.json`
  and `app.json`, as JSON, and refuses a symlink, a non-regular file, or a file
  over a size limit; an error returned to the container never quotes file
  contents.
- **Management commands are reachable from the container too.** The trust,
  token, and fix commands take no arguments, return nothing, and change nothing
  until the user answers a modal.
- **No-VCS packing.** The build always sets `EAS_NO_VCS=1`. eas-cli's git
  packing writes the workspace's `.git/config`; in no-VCS mode it writes nothing
  in `.git`, still honors `.gitignore`, and includes untracked files, so the
  bridge itself writes nothing in the workspace outside `.tmp/expo-bridge/`.
- **Safe paths and processes.** Every protocol path is resolved with `realpath`
  and rejected when any component is a symlink or the result leaves the
  workspace. Every file the host extension writes under `.tmp/expo-bridge/` is
  created under a fresh name with `O_CREAT | O_EXCL | O_NOFOLLOW_ANY`. The build
  writes its artifact into a directory private to the Mac, the host extension's
  global storage, and the host extension copies it in under that rule. `install`
  unpacks an artifact into a fresh private directory and rejects any archive
  entry that is absolute, contains `..`, or is a symlink. The host extension
  starts every process with `execFile` and an argument array, never a shell
  string.
- **`EXPO_TOKEN` in VS Code SecretStorage.** Commands set and clear the token on
  the Mac; the host extension puts it in the build's environment only. The build
  can still read it, so the README recommends a robot-account token scoped to
  the project.

**Host environment.** The host extension's processes (probes, the build,
`xcrun simctl`) run with the user's login environment, captured with
`$SHELL -l -c 'env -0'`, which fish and POSIX shells both accept, and starts its
processes directly with that environment — never through the login shell. Tool
lookup also searches Homebrew's prefixes `/opt/homebrew/bin` and
`/usr/local/bin`, so a shell configuration that omits them does not break the
bridge.

- **`status`** reports whether the bridge can serve a build: a Mac host, a
  workspace host path that exists locally, whether the workspace is trusted,
  Xcode, CocoaPods, fastlane, Node, a host bun at least as new as the
  container's (the container sends its `bun --version`), `EXPO_TOKEN` stored in
  SecretStorage, `extra.eas.projectId` in `app.json`, a booted simulator,
  whether port 8081 is forwarded, and the protocol version.
- **Nothing Mac-specific lands in the shared workspace.** The host extension
  never runs `eas init`, `expo run:ios`, `expo prebuild`, or a package install
  in the workspace; the only files it writes there are under `.tmp/expo-bridge/`
  — logs, build artifacts, screenshots. Linking the EAS project is a one-time
  setup step done from the container, which `status` reports when missing.
- **One-click fix.** When `status` finds a missing tool, the host extension
  offers a fix in the VS Code UI that runs Homebrew in a visible local terminal.
  Xcode is a guided step (it opens the App Store page), after which the fix runs
  `xcode-select`, accepts the license, and downloads the iOS platform. A fix is
  only ever started by the user's click, never by a protocol action.
- **`eas-host`** is the container-side command. The workspace extension installs
  it into `~/.local/bin` on activation and listens on a fixed socket; it streams
  the build log by tailing the log file the host extension writes. When the
  bridge is unavailable, `eas-host status` says so and exits non-zero, and the
  agent uses the Expo profile's EAS cloud path.
- **Dev-client loop.** Metro runs in the container; VS Code forwards port 8081
  to the Mac, where the simulator's development build connects to it, so the
  native build reruns only when native code changes.
- **Template wiring.** The Expo profile lists the extension pack, forwards 8081,
  and adds an `AGENTS.md` rule telling agents to use `eas-host` for iOS when
  `eas-host status` succeeds. Setup never pre-authorizes the bridge.

The protocol and the security model are specified in the sibling repository,
which owns the code; this repository's spec covers only the template wiring, the
fallback, and that setup grants no trust.

Rejected: a generic host-command bridge such as `dc2host` — any process in the
container could run anything on the Mac. Rejected: wrapping `eas` so that
`eas build -p ios` routes to the Mac — Expo's plugin skills call `eas` directly,
and silently changing a third-party command's meaning is fragile. Rejected:
`expo run:ios` on the Mac — it builds in the shared workspace against the
container's Linux `node_modules`. Rejected: a self-hosted GitHub Actions runner
on the Mac — it needs CI plumbing and is not available from an open editor
window. Rejected: a host network port — the protocol travels over VS Code's
command routing, so the firewall allowlist does not change. Rejected: a single
extension whose host half registers a URI handler that `eas-host` reaches with
`code --open-url` — a URI handler returns nothing, so results would come back
only by polling files. Rejected: containing the build with `sandbox-exec` —
macOS does not apply a sandbox inside another, and the build's tools (SwiftPM)
sandbox themselves; turning their sandboxes off for one build depends on Expo's
script internals, Xcode's script-phase `PATH`, and an undocumented Xcode
default. Rejected: disabling SwiftPM's manifest sandbox through global Xcode
defaults — it weakens every Xcode build on the Mac. Rejected: building as a
dedicated low-privilege macOS user — it needs a second account, a sudoers rule,
and a root-owned wrapper installed with the user's admin password, a standing
privileged path on the Mac; and the account's home persists between builds, so
one hostile build can poison the next.

Assumptions:

- The extension IDs are `plume-works.vscode-expo-bridge` (the pack),
  `plume-works.vscode-expo-bridge-host` (`ui`), and
  `plume-works.vscode-expo-bridge-workspace` (`workspace`).
- The socket is `/tmp/vscode-expo-bridge.sock` inside the container; one VS Code
  window serves one container.
- The workspace extension activates on `workspaceContains:eas.json`.
- A declined trust prompt is remembered until revoked through the trust command,
  so a hostile workspace cannot re-prompt repeatedly.
- The first workspace folder is the Expo project root.
- CocoaPods and fastlane are owned by the one-click fix, not by the [macOS
  bootstrap](20261013-macos-native-bootstrap.md).
- Listing the pack in `customizations.vscode.extensions` installs the host
  extension in the Mac's local extension host.

## Implementation Steps

### Task 1: Spike the bridge end to end

**Files:** Create: a scratch extension outside both repositories

- [x] A container-side command calls a `ui`-side command through
  `vscode.commands.executeCommand`, and the `ui` side resolves the workspace's
  host path from the remote window.
  - **Evidence:** Spike on 2026-10-21, macOS arm64 host, Dev Containers window.
    A request on a container socket reached a `ui`-kind command through
    `executeCommand`. The command decoded the folder URI authority
    `dev-container+<hex JSON>` and took its `hostPath`. It then read back, at
    that host path, a nonce file the container had written.
- [x] The `ui` side runs `eas build --local -p ios --profile development` for an
  `ios.simulator: true` profile on a blank `bun create expo` app, and the
  artifact is readable in the container.
  - **Evidence:** Spike on 2026-10-21 with eas-cli 25.3.0, Expo SDK 58 and EAS
    project `d67b0e6f-5880-4bab-b64b-77d1dd12519e`. The `ui` side ran the build,
    which exited 0. The container unpacked the resulting `.tar.gz` and read the
    `.app`'s `Info.plist`: `CFBundleSupportedPlatforms` is `iPhoneSimulator`.

### Task 2: Spike the `eas build --local` behavior the design relies on

**Files:** none — run against the Task 1 scratch app on a Mac

- [x] The build runs outside the workspace: the workspace's `node_modules` is
  unchanged and no `ios/` directory appears in it.
  - **Evidence:** In the same build, the working directory was macOS's
    `$TMPDIR/eas-build-local-nodejs/<id>/build`. A hash of the workspace's
    `node_modules` file list (path, size, mtime) matched before and after, and
    no `ios/` appeared.
- [x] `EAS_LOCAL_BUILD_ARTIFACTS_DIR` set to `.tmp/expo-bridge/` places the
  artifact there.
  - **Evidence:** In the same build, `EAS_LOCAL_BUILD_ARTIFACTS_DIR` was set to
    the host path of `.tmp/expo-bridge/`. `build-<timestamp>.tar.gz` landed
    there and was visible from the container.
- [x] The build uses the host's bun regardless of the `bun` field in `eas.json`,
  as the build log reports.
  - **Evidence:** In the same build, the profile pinned `"bun": "1.1.0"`. The
    `INSTALL_DEPENDENCIES` and `PREBUILD` phases logged `bun install v1.4.3`,
    the host's bun. An earlier run with host bun 1.3.10 failed
    `bun install --frozen-lockfile` with `UnknownLockfileVersion` on a
    `bun.lock` written by the container's 1.4.3. That confirms the `status`
    bun-version check.
- [x] `EXPO_TOKEN` in the host environment authenticates the build with no
  `eas login`.
  - **Evidence:** In the same build, `EXPO_TOKEN` came only from the host login
    environment and no `eas login` was run. Both
    `eas init --non-interactive --force` and the build authenticated with it.
- [x] An EAS environment variable with "Secret" visibility is absent from the
  build, and the same variable set in the host environment is present.
  - **Evidence:** Spike build on 2026-10-21 for the `development` profile with
    `environment: development`. eas-cli logged that it loaded only "Plain text"
    and "Sensitive" variables, `SPIKE_PLAIN` alone. In the app config embedded
    in `EXConstants.bundle`, `SPIKE_PLAIN` is the EAS value and the Secret-only
    `SPIKE_SECRET_A` is unset. `SPIKE_SECRET_B`, a Secret on EAS that the `ui`
    side also put in the build's environment, carries the host value.
- [x] The built app contains a change to a tracked file that was not committed
  and a new untracked file. When either is missing, find the eas-cli setting
  that includes them.
  - **Evidence:** Spike builds on 2026-10-21 with default eas-cli VCS settings.
    An uncommitted `ios.infoPlist` marker and display name in `app.json` appear
    in the `.app`'s `Info.plist`. An untracked solid-red
    `assets/untracked-icon.png`, set as the icon, produced red
    `AppIcon60x60@2x.png` and `AppIcon76x76@2x~ipad.png`. An untracked
    `app.config.js` set the embedded `extra` values. No setting was needed.
- [x] Any check that fails is recorded under `## Verification results` and the
  plan goes back to revise before Task 11.
  - **Evidence:** Every Task 2 check above passed, so there was nothing to
    record.

### Task 3: Spike how Expo's plugin skills invoke `eas`

**Files:** none — read `expo/skills`

- [x] Every build command in the skills of `expo@claude-plugins-official` is a
  direct `eas` invocation with no configurable command or hook; when one exists,
  record it under `## Verification results` and take the separate-command
  decision back to revise before Task 11.
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

- [x] The repository exists with an MIT license, a bun-managed TypeScript
  extension skeleton, and `package.json` declaring `plume-works` as publisher.
  - **Evidence:** `plume-works/vscode-expo-bridge` is public, and GitHub detects
    its license as `MIT`. Commit `91b9bbf` on `main` adds `package.json`
    (`"publisher": "plume-works"`), `bun.lock`, `tsconfig.json` and
    `src/extension.ts`. `bun run typecheck`, `bun run build` and
    `bun run package` passed on it.

### Task 5: Spike a contained `eas build --local`

**Files:** none — a `sandbox-exec` profile driven by the Task 1 scratch
extension; its findings are recorded under `## Verification results`

- [x] A `postinstall` script added to the app that reads `~/.ssh` fails under
  the profile, and one that writes to `~/Library/LaunchAgents` fails.
  - **Evidence:** Spike builds on 2026-10-21 under a profile that allows by
    default, denies `file-write*` except `/dev`, `/private/tmp`, the user's
    `/private/var/folders/<id>`, the package and Xcode caches, and the output
    directory, and denies `file-read*` of `~/.ssh`, `~/.gnupg`, `~/.aws`,
    `~/.config/gh`, `~/Library/Keychains` and `~/.netrc`. In both
    `INSTALL_DEPENDENCIES` and `PREBUILD`, `ls ~/.ssh` and
    `touch ~/Library/LaunchAgents/<file>` failed with `Operation not permitted`.
- [x] When either check fails, it is recorded under `## Verification results`
  and the plan goes back to revise before Task 17.
  - **Evidence:** Commit `363370b` records the nested-sandbox failure under
    `## Verification results`.
- [x] When the build's inner tool sandboxes cannot be turned off for the build's
  process tree alone, it is recorded under `## Verification results` and the
  plan goes back to revise its containment before Task 17.
  - **Evidence:** Commit `2455170` records under `## Verification results` that
    the inner-sandbox override cannot be scoped to the build.

### Task 6: Spike what a container-side extension can do through VS Code commands

**Files:** none — an attacker workspace extension added beside the Task 1
scratch extension, in a Dev Containers window on a Mac

- [ ] The attacker, a workspace extension other than the bridge's, invokes a
  command the `ui` side registers, and the handler receives nothing that
  identifies the calling extension or host.
- [ ] The attacker changes the workspace folders through
  `vscode.workspace.updateWorkspaceFolders`, and the `ui` side still resolves
  the window's original host path.
- [ ] With a bridge modal actually on screen, the attacker runs the workbench
  commands that focus, accept, or dismiss dialogs and notifications, and the
  prompt stays unanswered.
- [ ] A command sent from a second window's container does not reach this
  window's `ui` side.
- [ ] The attacker cannot read the `ui` side's SecretStorage or `globalState`.
- [ ] Every result is recorded under `## Verification results`; any check that
  fails takes the plan back to revise before Task 11.

### Task 7: Spike what the container reaches on the Mac without the bridge

**Files:** none — the Task 6 attacker extension and a container shell, in a Dev
Containers window on a Mac

- [ ] The attacker opens a local terminal and sends it text
  (`workbench.action.terminal.newLocal`,
  `workbench.action.terminal.sendSequence`); whether a command runs on the Mac
  is recorded.
- [ ] Whether the attacker can open a URL or a `file:` URI on the Mac
  (`vscode.env.openExternal`, `vscode.open`) and read or write the Mac clipboard
  is recorded.
- [ ] Each Mac-side socket forwarded into the container (SSH agent, GPG agent,
  git credential helper) is recorded with what a container process can do
  through it.
- [ ] Whether the container writing `initializeCommand` into
  `.devcontainer/devcontainer.json` or a setting into `.vscode/settings.json`,
  then triggering a reload, takes effect on the Mac is recorded.
- [ ] Whether the attacker can install an extension into the Mac's local
  extension host, and whether a port it listens on is forwarded to the Mac's
  `localhost` without a prompt, is recorded.
- [ ] The results are recorded under `## Verification results`. They inform the
  security model rather than gate it: the model already assumes the window
  grants host reach the bridge cannot remove.

### Task 8: Spike iOS Simulator containment

**Files:** none — the Task 1 scratch app with probes, on a Mac

- [ ] A probe in the app's native code, run on the booted simulator, records
  whether it can read the user's `~/.ssh` and write the user's
  `~/Library/LaunchAgents`.
- [ ] JavaScript the development build loads from Metro in the container records
  whether it can read a file in the user's home through any API the app ships.
- [ ] An `.app` the container writes into `.tmp/expo-bridge/`, not produced by a
  build, installs and launches through `xcrun simctl`; the result is recorded.
- [ ] When a probe escapes the simulator, the finding is recorded under
  `## Verification results` and the plan goes back to revise `install`,
  `launch`, and the dev-client loop before Task 11.

### Task 9: Spike the workspace file boundary

**Files:** none — the Task 1 scratch extension, on a Mac

- [ ] From the `ui` side, Node's `fs.open` with `O_NOFOLLOW_ANY` (`0x20000000`)
  refuses a path with a symlink in any component, and with `O_CREAT | O_EXCL`
  creates a fresh file otherwise.
- [ ] Whether eas-cli writes through a symlink the container planted at the
  artifact's file name, or in place of `EAS_LOCAL_BUILD_ARTIFACTS_DIR`, is
  recorded.
- [ ] Container-written `.tar.gz` archives holding an absolute path, a `..`
  entry, and a symlink followed by an entry through it, unpacked the way
  `install` will unpack them, write nothing outside a fresh directory.
- [ ] Reading `eas.json` as a symlink, a FIFO, and an oversized file fails
  without blocking, and the returned error contains none of the file's bytes.
- [ ] Every failure is recorded under `## Verification results` and the plan
  goes back to revise before Task 11.

### Task 10: Spike the unverified `eas build --local` behavior

**Files:** none — the Task 1 scratch app, on a Mac

- [ ] Whether a build honors the `node`, `cocoapods`, `fastlane`, and `image`
  fields of `eas.json` is recorded from the tool versions the build log reports.
- [ ] Whether a second build of the unchanged app reuses anything from the first
  — dependency install, pods, DerivedData — is recorded.
- [ ] The results are recorded under `## Verification results`; when a field is
  honored, `status`'s tool checks are revised before Task 11.

### Task 11: Specify the protocol and security model in the sibling repository

**Files:** Create: `docs/protocol.md` in `plume-works/vscode-expo-bridge`

- [ ] It defines the five actions, their arguments and validation, the result
  and error shapes, workspace-relative paths and the symlink rule, the
  `.tmp/expo-bridge/` write boundary, the protocol version and how `status`
  reports a mismatch, and that fixes are never protocol actions.
- [ ] It states the threat model as a consent surface, not a security boundary —
  the bridge adds no reach beyond what the devcontainer window already grants
  and does not claim to contain a hostile container — and each control from
  `## Approach`: the per-workspace trust prompt, the build confirmation and its
  cooldowns, that a build runs uncontained with the user's privileges, no
  project code outside `build`, management commands gated by a modal, the write
  rule for `.tmp/expo-bridge/` and archive unpacking, `execFile` without a
  shell, and `EXPO_TOKEN` in SecretStorage.

### Task 12: Split the repository into the two extensions and the pack

**Files:** Modify: the skeleton in `plume-works/vscode-expo-bridge`

- [ ] The repository builds `plume-works.vscode-expo-bridge-host`
  (`extensionKind: ["ui"]`), `plume-works.vscode-expo-bridge-workspace`
  (`extensionKind: ["workspace"]`), and the pack
  `plume-works.vscode-expo-bridge` listing both, each packaged as a VSIX.

### Task 13: Workspace extension and `eas-host`

**Files:** Create: in `plume-works/vscode-expo-bridge`

- [ ] The workspace extension activates on `workspaceContains:eas.json`,
  installs `eas-host` into `~/.local/bin`, and serves
  `/tmp/vscode-expo-bridge.sock`.
- [ ] `eas-host` maps each action to one socket request, streams the build log,
  prints the result as JSON, and exits non-zero when the bridge is unavailable
  or the action fails.
- [ ] `bun test` covers argument handling, the unavailable path, and log
  streaming.

### Task 14: Host extension — environment, processes, and paths

**Files:** Create: in `plume-works/vscode-expo-bridge`

- [ ] The host extension captures the login environment with
  `$SHELL -l -c 'env -0'`, resolves tools through it plus `/opt/homebrew/bin`
  and `/usr/local/bin`, and starts every process with `execFile` and an argument
  array.
- [ ] A protocol path is rejected when any component is a symlink or its
  `realpath` leaves the workspace, and every write under `.tmp/expo-bridge/`
  uses a fresh name with `O_CREAT | O_EXCL | O_NOFOLLOW_ANY`.
- [ ] `eas.json` and `app.json` are read as JSON only, refusing a symlink, a
  non-regular file, or an oversized file, with errors that quote no file
  contents.
- [ ] `bun test` covers environment parsing for fish and POSIX shells, tool
  lookup, path rejection for symlinks and `..`, the write flags, and the file
  read refusals.

### Task 15: Host extension — trust, build confirmation, and the token

**Files:** Create: in `plume-works/vscode-expo-bridge`

- [ ] The first request from an untrusted workspace prompts for trust, recorded
  in `globalState` by host path; a declined workspace fails every request until
  a command revokes the decision; a command lists and revokes trusted
  workspaces.
- [ ] Each `build` prompts with "Allow once", "Don't ask for an hour", and
  "Don't ask today", and a cooldown suppresses the prompt for that workspace
  only until it expires.
- [ ] Commands set and clear `EXPO_TOKEN` in SecretStorage, and the README
  recommends a robot-account token scoped to the project.
- [ ] The trust, token, and fix commands take no arguments, return nothing, and
  change nothing until the user answers a modal.
- [ ] `bun test` covers trust grant, decline, and revocation, each cooldown's
  expiry, and per-workspace scoping, with the clock and prompts stubbed.

### Task 16: Host extension — `status`

**Files:** Create: in `plume-works/vscode-expo-bridge`

- [ ] `status` reports every check in `## Approach`, and reports unavailable on
  a non-Mac host and when the workspace host path does not exist locally.
- [ ] `bun test` covers each check's pass and fail result with the system probes
  stubbed.

### Task 17: Host extension — `build`

**Files:** Create: in `plume-works/vscode-expo-bridge`

- [ ] `build` rejects a profile absent from `eas.json`, requires trust and the
  build confirmation, and runs `eas build --local -p ios --profile <name>` with
  the login environment plus `EXPO_TOKEN` from SecretStorage, `EAS_NO_VCS=1`,
  and the artifact built into the host extension's global storage, then copied
  with the log into `.tmp/expo-bridge/` under the write rule. `build` returns
  the artifact's workspace-relative path and the exit code, and never runs
  `eas init`.
- [ ] `bun test` covers profile validation, the gating order, and the `eas`
  arguments and environment, with process spawning stubbed.

### Task 18: Host extension — `install`, `launch`, `screenshot`

**Files:** Create: in `plume-works/vscode-expo-bridge`

- [ ] `install` rejects a path outside `.tmp/expo-bridge/`, unpacks the artifact
  into a fresh private directory rejecting absolute, `..`, and symlink entries,
  and installs it on the booted simulator; `launch` starts the app `install`
  last installed, by the `CFBundleIdentifier` in its `Info.plist`; `screenshot`
  writes a PNG under `.tmp/expo-bridge/` and returns its workspace-relative
  path.
- [ ] `bun test` covers path validation, archive entry rejection, and the
  `xcrun simctl` invocations.

### Task 19: One-click fix

**Files:** Create: in `plume-works/vscode-expo-bridge`

- [ ] For each failing `status` check that a tool install resolves, the VS Code
  UI offers a fix that runs the Homebrew command in a visible local terminal;
  for Xcode it opens the App Store page and then runs `xcode-select`, the
  license acceptance, and `xcodebuild -downloadPlatform iOS`.
- [ ] No protocol action can start a fix.

### Task 20: Sibling repository CI

**Files:** Create: `.github/workflows/` in `plume-works/vscode-expo-bridge`

- [ ] A workflow runs lint, `bun test`, and the three VSIX package builds on
  every pull request, and passes on `main`.

### Task 21: Publish to the Visual Studio Marketplace

- [ ] `plume-works.vscode-expo-bridge`, `plume-works.vscode-expo-bridge-host`,
  and `plume-works.vscode-expo-bridge-workspace` are installable from the Visual
  Studio Marketplace.

### Task 22: Publish to Open VSX

- [ ] `plume-works.vscode-expo-bridge`, `plume-works.vscode-expo-bridge-host`,
  and `plume-works.vscode-expo-bridge-workspace` are installable from Open VSX.

### Task 23: Wire the bridge into the Expo profile

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [ ] `## Optional Expo setup` adds `plume-works.vscode-expo-bridge` to
  `customizations.vscode.extensions` and `8081` to `forwardPorts` in the
  consumer's `.devcontainer/devcontainer.json`, and writes no bridge trust or
  security setting.
- [ ] The `## Expo` section of the merged `AGENTS.md` gains a rule: for an iOS
  build, run `eas-host status`; when it succeeds use `eas-host`, otherwise use
  EAS cloud.

### Task 24: Record the bridge in the template boundary and architecture

**Files:** Modify: `docs/knowledge/data/architecture/template-boundary.md`;
Create: `docs/knowledge/data/architecture/vscode-expo-bridge.md`; Modify:
`docs/knowledge/data/architecture.md`

- [ ] The template boundary's Expo profile section names the extension pack, the
  forwarded port, the `AGENTS.md` rule, and that setup grants no trust.
- [ ] `data/architecture/vscode-expo-bridge` records the design in `## Approach`
  with its security model and rejected alternatives, and links the sibling
  repository's protocol document; `data/architecture.md` links it.

### Task 25: Validate the catalog change

- [ ] `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.

### Task 26: End to end on a Mac

- [ ] In an Expo consumer adopted with the Expo profile and opened by VS Code on
  a Mac, the pack from `devcontainer.json` puts the host extension in the local
  extension host and the workspace extension in the container.
- [ ] An agent runs `eas-host status`, `build` for a simulator profile,
  `install`, `launch`, and `screenshot`, and reads the screenshot from the
  container; the trust prompt appears on the first request and the build
  confirmation on `build`.
- [ ] With Metro running in the container, the launched development build loads
  the JavaScript bundle over forwarded port 8081.

### Task 27: Fallback when the bridge is unavailable

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
other than this extension pack, SHALL NOT change the firewall allowlist for it,
and SHALL NOT pre-authorize the bridge: trust in a workspace is granted only on
the Mac.

#### Scenario: an Expo consumer is opened by VS Code on a Mac

- **WHEN** an Expo consumer's devcontainer is opened by VS Code on a Mac with
  the extension pack installed, the tools `eas-host status` checks present, and
  the workspace trusted on the Mac
- **THEN** `eas-host status` succeeds
- **AND** `eas-host build` with a profile from `eas.json` leaves the artifact
  under `.tmp/expo-bridge/`

#### Scenario: setup grants no trust

- **WHEN** setup applies the Expo profile
- **THEN** it writes no bridge trust or security setting into any consumer file
- **AND** the first bridge request from the consumer's workspace asks for trust
  on the Mac

#### Scenario: the bridge is unavailable

- **WHEN** the devcontainer runs where the workspace is not on the VS Code host
  — a Codespace, a non-Mac host, or no VS Code window
- **THEN** `eas-host status` exits non-zero
- **AND** the EAS cloud build path works unchanged

#### Scenario: a non-Expo consumer

- **WHEN** the consumer's `optional_bundles` omits `"expo"`
- **THEN** setup adds neither the extension pack, the forwarded port, nor the
  rule
```

The protocol contract and security model are specified in
`plume-works/vscode-expo-bridge` (`docs/protocol.md`), not in this repository.

## Depends on

- [Expo profile for template adoption](20261014-expo-eas-template-profile.md) —
  Task 23 extends its `## Optional Expo setup` section and its `## Expo`
  `AGENTS.md` section.

## Verification

- The Task 1–3 and Task 5–10 spikes pass, or their findings have been taken back
  to revise.
- The sibling repository's CI passes on `main`.
- The pack and both extensions install from both the Visual Studio Marketplace
  and Open VSX.
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.
- Task 26's end-to-end run and Task 27's fallback run behave as described.
- `iwe normalize` and `iwe schema validate` pass.

## Verification results

### Task 5: a `sandbox-exec` build fails on nested sandboxing

Under the Task 5 profile, the Expo SDK 58 simulator build fails in the
`ExpoModulesJSI` pod's `[CP-User] Build ExpoModulesJSI xcframework` script
phase. That phase runs `xcodebuild`, which resolves Swift packages, and SwiftPM
sandboxes manifest evaluation with `sandbox-exec`. Inside the outer sandbox it
fails with
`Could not resolve package dependencies: sandbox-exec: sandbox_apply: Operation not permitted`.
macOS does not apply a sandbox inside another, so no change to the profile's
rules fixes it. The probe check passed under the same profile.

Two constraints on any sandboxed build follow:

- eas-cli's default git packing runs `git config core.ignorecase false` in the
  project's repository, a write to the workspace's `.git/config`. With
  `EAS_NO_VCS=1` it writes nothing in `.git`. Its archive still honors
  `.gitignore` (no `node_modules`) and includes untracked files.
- The build's inner tools may sandbox themselves. A containment mechanism must
  allow that, or turn it off for the build's process tree only.

### Task 5: the inner-sandbox override cannot be scoped to the build

The failing nested build is started by `expo-modules-jsi`'s
`build-xcframework.sh` as `env -i PATH HOME PODS_ROOT RN_ROOT … xcodebuild`.
That rules out any override passed in the environment, such as
`CFFIXED_USER_HOME`. An `xcodebuild` shim that adds
`-IDEPackageSupportDisableManifestSandbox=YES` is accepted when called directly,
but it never reaches the nested call. Xcode puts its own tool directories,
including `Contents/Developer/usr/bin`, ahead of the script phase's `PATH`, even
when an `XCODE_XCCONFIG_FILE` sets `PATH = <shim>:$(inherited)`. The user's
`com.apple.dt.Xcode` defaults stayed unchanged throughout, and the `postinstall`
probes stayed blocked.

Turning off the inner sandboxes for one build would mean depending on Expo's
script internals, Xcode's `PATH` assembly, and an undocumented Xcode default.

### Task 7: the window already grants the container host reach

A workspace (container) extension that is not the bridge reaches the Mac through
VS Code's own commands. On a macOS Dev Containers window it ran
`workbench.action.terminal.newLocal` then
`workbench.action.terminal.sendSequence` with no consent prompt, and a marker
command executed on the Mac — a file with the attacker's nonce appeared under
the Mac's `/tmp` and was absent in the container's. The same extension read and
wrote the Mac clipboard. `VSCODE_IPC_HOOK_CLI` is present in the container and
the remote `code` CLI answers, so a detached container process reaches it. The
SSH agent (`SSH_AUTH_SOCK`) and the GPG agent are forwarded into the container;
`ssh-add -l` from the container listed the user's private keys. `openExternal`
to a URL was gated by a Mac consent prompt rather than opening silently.

The bridge installs nothing that changes this. The plan's security model is
therefore the narrower one in `## Approach`: the bridge adds no reach beyond
what the window grants, and gates its own `build` behind trust and confirmation.
The forwarded SSH and GPG agents are a devcontainer-wide exposure independent of
this feature, recorded as the someday idea [Narrow the devcontainer's forwarded
agent exposure](../someday/devcontainer-forwarded-agent-exposure.md) for
research into whether it can be narrowed without breaking the workflows that
rely on it.

### Task 6: a command invocation carries no caller identity

The non-bridge attacker extension invoked the `ui` side's command and received
the full host path back; the handler saw only its own arguments, nothing naming
the caller or its host. After the attacker injected a workspace folder with
`updateWorkspaceFolders`, the `ui` side still resolved the window's original
`dev-container+…` authority and host path, so folder injection does not redirect
the bridge. A workspace extension holds no handle to another extension's
`SecretStorage` or `globalState`. The modal-not-answerable and
second-window-isolation checks were not exercised and stay open.

## Out of scope

- Android builds through the bridge; the container builds Android itself.
- Device and store builds that need Apple signing; the bridge covers simulator
  builds, and `eas credentials` stays a one-time human step.
- A generic host-command facility.
- Hosts other than VS Code desktop on macOS, and editors that cannot run a `ui`
  extension locally.
- Changes to this repository's own `.devcontainer/`.
- Installing Xcode itself unattended.
- Linking the EAS project (`eas init`) through the bridge.
- Containing a build on the Mac: a trusted, confirmed build runs with the Mac
  user's privileges.
- Removing the host reach a devcontainer window already grants (local terminal,
  forwarded agents); the bridge adds none of it and cannot take it away.
  Narrowing the forwarded SSH and GPG agent exposure is tracked separately as a
  someday idea.

## Key references

Verified anchor points (line numbers as of 2026-10-21):

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
