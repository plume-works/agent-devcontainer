---
type: plan
created: 2026-10-28
release:
- features/expo-eas-builds
description: Move the 28 Expo bridge documents from this graph into a new IWE workspace in plume-works/vscode-expo-bridge, give that repository contributor instructions and a README that stand without this template, file its agent-skill task there, and leave this graph only the template's Expo profile wiring, linked to the new home by URL.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-28T16:12:37Z
sources:
- resource: https://github.com/plume-works/vscode-expo-bridge
- resource: docs/knowledge/data/architecture/vscode-expo-bridge.md
- resource: docs/knowledge/data/features/vscode-expo-bridge.md
- resource: docs/knowledge/data/architecture/template-boundary.md
- resource: docs/knowledge/data/features/expo-eas-builds.md
- resource: .agents/plugins/agentdev/skills/iwe-bootstrap/SKILL.md
---

# Move the Expo bridge knowledge into its own repository

## Context

[plume-works/vscode-expo-bridge](https://github.com/plume-works/vscode-expo-bridge)
holds the bridge's code, protocol contract (`docs/protocol.md`), versioning, and
releases, while its design, plans, bugs, and backlog live in this graph. The
bridge is now a product with its own users: someone adopting it without this
template finds none of that record, and its repository's `AGENTS.md` covers only
packaging a VSIX.

This plan changes [Expo apps build for iOS through
EAS](../features/expo-eas-builds.md): its behaviour gains the Expo profile's
bridge wiring, which today only the moved [VS Code Expo
bridge](../features/vscode-expo-bridge.md) feature describes.

Decisions made with the maintainer:

- The extension repository gets a blank IWE workspace from
  `/agentdev:iwe-bootstrap`, not the whole template through
  `/agentdev:template-consume`. Contributors get the IWE skills from the
  `agentdev` plugin.
- All 28 bridge documents move, finished plans and fixed bugs included: they are
  the product's record.
- The bridge entries leave this repository's `releases/unreleased.md`; the
  bridge ships in its own `vX.Y.Z` releases. Only the template's wiring stays in
  this repository's release notes.
- An agent skill that teaches `eas-host` is not built here. It is filed as a
  high-priority task in the extension repository's backlog, with its delivery
  left open (Task 5).

The 28 documents, by key (identical in both graphs):

- `architecture/vscode-expo-bridge`, `features/vscode-expo-bridge`,
  `someday/expo-bridge-codespaces`
- plans: `20261015-vscode-expo-bridge`,
  `20261023-expo-bridge-workspace-folders`,
  `20261023-expo-bridge-fingerprint-reuse`,
  `20261023-expo-bridge-incremental-builds` (cancelled),
  `20261023-openvsx-trusted-publishing`,
  `20261024-expo-bridge-fix-terminal-mac-shell`,
  `20261025-expo-bridge-bun-fix-resolved-bun`, `20261026-expo-bridge-panel`
- bugs: every `bugs/expo-bridge-*` (10; three open:
  `expo-bridge-cocoapods-fix-misses-unlinked-keg`,
  `expo-bridge-project-id-diagnostic-stale-after-config-edit`,
  `expo-bridge-simulator-profile-quick-fix-omits-bun`)
- backlog: `expo-bridge-build-controls` (high), `expo-bridge-icons`,
  `expo-bridge-one-status-bar-item`, `expo-bridge-section-status-icons`,
  `expo-bridge-sideload-procedure`, `expo-bridge-agent-guidance` (done),
  `document-expo-bridge-vscodium-support` (done)

## Approach

Copy the 28 documents into the extension repository at the same keys, list each
in that graph's hubs at the section it holds here, and rewrite every link that
crosses the repository line into an absolute GitHub URL on `main`: links from
moved documents to documents staying here, and links from staying documents to
moved ones. Sources and code anchors that name the extension repository by URL
become local paths there; paths into this repository become URLs. The extension
repository's pull request merges first, so no URL written here points at
nothing; this repository then removes the documents with `iwe delete`, after its
inbound links are already URLs.

Rejected: keeping finished plans and fixed bugs here as history — the product's
record would be split across two repositories, and every open bug's root cause
links back into finished plans. Adopting the whole template in the extension
repository — it brings a devcontainer and catalog the extension does not need to
keep project memory.

Assumptions:

- The extension repository is worked on in a checkout at
  `/workspaces/vscode-expo-bridge`, on a branch from `/agentdev:git-new-branch`;
  no clone under `./.tmp/` is used.
- The extension's README documents `eas-host` for a human reader; instructions
  written for an agent are the deferred skill's job.
- Its `releases/unreleased.md` stays empty: past `v0.x` releases are recorded as
  GitHub Releases and are not backfilled into the graph.
- A docs-only change there still bumps the patch, per its README's versioning
  rule.

## Implementation Steps

### Task 1: Bootstrap the IWE workspace in the extension repository

**Files:** Create: `.iwe/`, `docs/knowledge/` (extension repository); Modify:
`.prettierignore` (extension repository)

- [x] Run `/agentdev:iwe-bootstrap --root /workspaces/vscode-expo-bridge`;
  result `SUCCESS`.
  - **Evidence:** plume-works/vscode-expo-bridge `d66c5ac` on `expo-repo-kb`
    adds `.iwe/` and `docs/knowledge/`; `iwe schema validate` exits 0 there.
- [x] Add `docs/knowledge/**` and `.iwe/**` to `.prettierignore`:
  `iwe normalize` owns the knowledge base and the scaffold owns `.iwe/`, and
  `bun run lint` runs `prettier --check .` over the repository.
  - **Evidence:** vscode-expo-bridge `d66c5ac` `.prettierignore`; `bun run lint`
    passes there.
- [x] Run `/agentdev:iwe-setup` there with the maintainer so `data/product.md`
  describes the extension and holds no ✏️ placeholder; delete the scaffold's
  `.example.md` documents as setup does.
  - **Evidence:** vscode-expo-bridge `d66c5ac` `docs/knowledge/data/product.md`
    (Users, Constraints, stage, and rules from the maintainer's answers), no
    `.example.md` left, `backlog/fill-product-doc` done.

### Task 2: Copy the 28 documents and list them in the new hubs

**Files:** Create: the 28 documents under `docs/knowledge/data/`; Modify:
`data/architecture.md`, `data/features.md`, `data/plans.md`, `data/bugs.md`,
`data/backlog.md`, `data/someday.md` (extension repository)

- [x] Copy each document byte for byte to the same key.
  - **Evidence:** vscode-expo-bridge `bf1aea5`; `cmp` of all 28 against this
    repository's copies reports no difference.
- [ ] Add each one's inclusion link to the matching hub at the section it holds
  here (`## Active`/`## Done`/`## Cancelled` for plans,
  `## High`/`## Medium`/`## Low`/`## Done` for backlog).
  - **Evidence:** vscode-expo-bridge `bf1aea5` hubs: 8 plans (7 Done, 1
    Cancelled), 7 backlog (1 High, 3 Medium, 1 Low, 2 Done), 10 bugs, and one
    each in architecture, features, and someday; `iwe schema validate` exits 0.

### Task 3: Rewrite cross-repository references in the moved documents

**Files:** Modify: the 28 moved documents (extension repository)

- [x] Links to the six documents staying here —
  `architecture/template-boundary`, `features/expo-eas-builds`,
  `plans/20261013-macos-native-bootstrap`,
  `plans/20261014-expo-eas-template-profile`,
  `someday/devcontainer-forwarded-agent-exposure`, `spec/template-consumption` —
  become
  `https://github.com/plume-works/agent-devcontainer/blob/main/docs/knowledge/data/<key>.md`.
  - **Evidence:** vscode-expo-bridge `0d413c8`; `iwe stats` there lists no
    broken link.
- [x] `sources` entries and code anchors naming
  `https://github.com/plume-works/vscode-expo-bridge/blob/main/<path>` or
  `plume-works/vscode-expo-bridge:<path>` become `<path>`; entries naming paths
  in this repository (`.agents/…`, `.devcontainer/…`, staying
  `docs/knowledge/data/…` documents) become URLs into it; a bare
  `https://github.com/plume-works/vscode-expo-bridge` source, which names the
  repository itself, is dropped; a backticked commit ID that resolves only in
  this repository becomes its commit URL.
  - **Evidence:** vscode-expo-bridge `0d413c8`: this-repository sources and
    `plans/20261015-vscode-expo-bridge` anchors carry
    `plume-works/agent-devcontainer`, extension paths are local, and the 13
    commit IDs found only here link to their commits.
- [x] `architecture/vscode-expo-bridge`'s Context says the extension repository
  owns the bridge and `agent-devcontainer` owns only its template wiring, and
  keeps its link to `docs/protocol.md` as a URL: `iwe` counts a relative
  Markdown link outside `docs/knowledge/` as a broken graph link.
  - **Evidence:** vscode-expo-bridge `0d413c8`
    `docs/knowledge/data/architecture/vscode-expo-bridge.md` `## Context`.
- [x] Stamp `generated` on every document this task changed.
  - **Evidence:** vscode-expo-bridge `0d413c8`: all 28 carry
    `generated.at: 2026-10-28T16:52:14Z`.

### Task 4: Write the extension repository's agent instructions and README

**Files:** Modify: `AGENTS.md`, `README.md`, the package `version` fields;
Create: `CLAUDE.md` (extension repository)

- [x] `AGENTS.md` keeps its packaging section and adds what a contributor needs
  without this template: the `bun` commands (`install`, `lint`, `typecheck`,
  `test`, `package`, `bump`) and `bun` only for JavaScript; the patch bump on
  every change; `docs/protocol.md` as the contract, changed together with the
  code, with the protocol version raised for any incompatible change; the
  security invariants the protocol states (fixed action set, no command string
  from the container, writes into the workspace only under `.tmp/expo-bridge/`,
  no security setting read from a container-writable file); scratch files in
  `./.tmp/`; and the project memory in `docs/knowledge/data/`, run with `iwe`
  from the repository root, following `docs/knowledge/AGENTS.md`.
  - **Evidence:** vscode-expo-bridge `41b964b` `AGENTS.md`.
- [x] `CLAUDE.md` holds only `@AGENTS.md`.
  - **Evidence:** vscode-expo-bridge `41b964b` `CLAUDE.md`.
- [x] `README.md` lets a user adopt the bridge with no other repository: the
  `devcontainer.json` wiring (the pack in `customizations.vscode.extensions`,
  `8081` in `forwardPorts` with `"onAutoForward": "silent"`), `EXPO_TOKEN` set
  on the Mac through the host's token command, the `eas-host` actions in the
  order `eas-host --help` lists them, artifacts under `.tmp/expo-bridge/`, Metro
  in the container before `launch`, and EAS cloud when `eas-host status` exits
  non-zero.
  - **Evidence:** vscode-expo-bridge `41b964b` `README.md`, sections "Setting up
    a project" and "Using `eas-host`".
- [x] `bun run bump`; `bun run lint`, `bun run typecheck`, and `bun test` pass.
  - **Evidence:** vscode-expo-bridge `41b964b` bumps to `0.4.1`; lint and
    typecheck clean, `bun test` 409 pass, 0 fail.

### Task 5: File the agent-skill task in the extension repository's backlog

**Files:** Create: `docs/knowledge/data/backlog/expo-bridge-agent-skill.md`;
Modify: `docs/knowledge/data/backlog.md` (extension repository)

- [x] File it with `/agentdev:iwe-capture task` at `priority: high`. The task:
  ship a skill that teaches an agent the bridge — run `eas-host status` first,
  then `build <profile>`, `install`, start Metro, `launch`, `screenshot`;
  artifacts under `.tmp/expo-bridge/`; EAS cloud when `status` exits non-zero;
  run inside the Expo app's folder — generated from the same source as
  `eas-host --help`. Its delivery stays open among three options:

  - **A. A plugin marketplace in this repository** —
    `skills/expo-bridge/SKILL.md` and `.claude-plugin/marketplace.json`,
    installed with `/plugin install`; Claude Code only, a manual step per
    machine.
  - **B. The workspace extension installs it** — on activation it writes the
    skill into the container's per-user agent skill directories, as it writes
    `eas-host` into `~/.local/bin`, never into the workspace; it replaces only a
    copy carrying its own version marker and leaves a user's same-named skill
    alone; removal on uninstall is decided or recorded as a limit; the new write
    outside the workspace is documented in `docs/protocol.md` and the README.
  - **C. Both** — B for the devcontainer, A for agents outside one.

  Acceptance names the chosen option and, for B, the directories verified
  against each agent's current documentation.

  - **Evidence:** vscode-expo-bridge `9c4625f`
    `docs/knowledge/data/backlog/expo-bridge-agent-skill.md` under `## High`.

### Task 6: Validate the extension repository's graph

**Files:** none

- [x] From `/workspaces/vscode-expo-bridge`: `iwe normalize` leaves no diff,
  `iwe schema validate` exits 0, `iwe stats` reports no broken link and no
  orphan among the 28, and no relative link in `docs/knowledge/data/` resolves
  outside it.
  - **Evidence:** vscode-expo-bridge `9c4625f`: `iwe normalize` no-op,
    `iwe schema validate` exits 0, `iwe stats` lists no broken link and only the
    scaffold's own orphans, no relative link leaves `docs/knowledge/data/`.

### Task 7: Open the extension repository's pull request

**Files:** none

- [ ] Commit, push, and open the pull request with `/agentdev:pr-open`.

### Task 8: Merge the extension repository's pull request

**Files:** none

- [ ] The pull request is merged to `main`, CI green, and each moved document
  resolves at its
  `https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/<key>.md`
  URL.

### Task 9: Point this repository's remaining links at the new home

**Files:** Modify: `docs/knowledge/data/log.md`,
`docs/knowledge/data/architecture/template-boundary.md`,
`docs/knowledge/data/someday/devcontainer-forwarded-agent-exposure.md`,
`docs/research/vscode-vulnerability/deep-technical.md`

- [ ] Every link from a staying document to one of the 28 becomes
  `https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/<key>.md`,
  in prose and in `sources`; `log.md` entries keep their text.

### Task 10: Remove the 28 documents from this graph

**Files:** Delete: the 28 documents; Modify: `data/architecture.md`,
`data/features.md`, `data/plans.md`, `data/bugs.md`, `data/backlog.md`,
`data/someday.md`, `data/releases/unreleased.md`

- [ ] `iwe delete` each key; `git diff` shows only hub and
  `releases/unreleased.md` inclusion links removed — the feature under
  `## Added` and the seven bugs under `## Fixed` — and no prose link rewritten.

### Task 11: Describe the template's bridge wiring in its Expo feature

**Files:** Modify: `docs/knowledge/data/features/expo-eas-builds.md`

- [ ] Its Behaviour gains the profile's bridge wiring, as
  `architecture/template-boundary` records it: the pack
  `plume-works.vscode-expo-bridge` in `customizations.vscode.extensions`, port
  `8081` forwarded silently for Metro, the `AGENTS.md` rule to build through
  `eas-host` when `eas-host status` succeeds and on EAS cloud otherwise, and no
  trust granted by setup; linked to the extension repository by URL. Stamp
  `generated` and add the extension repository to `sources`.

### Task 12: Validate this repository's graph

**Files:** none

- [ ] `iwe normalize`, then `iwe schema validate` exits 0; `iwe stats` reports
  no broken link; `grep -rn "expo-bridge" docs/knowledge/data` finds only URLs,
  the backticked key list in this plan, and historical text in
  `plans/20261016-release-impact-at-plan-time`;
  `uv run pytest docs/knowledge/tests` passes.

## Spec changes

None — no behavioral change. `spec/template-consumption` already links the
extension repository by URL and its Expo profile requirement is unchanged.

## Verification

- Extension repository: `iwe schema validate` exits 0, `iwe normalize` is a
  no-op, `iwe stats` shows the 28 documents included by their hubs with no
  broken link; `bun run lint`, `bun run typecheck`, `bun test` pass; CI green on
  the pull request.
- The README read alone answers: how to install both halves, what to put in
  `devcontainer.json`, where `EXPO_TOKEN` goes, which `eas-host` commands to run
  in which order, and what happens when the bridge is unavailable.
- This repository: `iwe schema validate` exits 0, no broken link, no relative
  link to any of the 28 keys remains, `releases/unreleased.md` lists no bridge
  feature or bug, and `features/expo-eas-builds` describes the wiring.
- `backlog/expo-bridge-agent-skill` exists in the extension repository at
  `priority: high`, under `## High`, with options A, B, and C.

## Out of scope

- Building the agent skill or choosing its delivery (Task 5 files it).
- Changing the Expo profile rule in `consumption-guide.md` or
  `spec/template-consumption`.
- CI that validates the extension repository's graph, `/agentdev:iwe-map` there,
  and backfilling its past `v0.x` releases into its graph.
- Trimming `architecture/vscode-expo-bridge` where it repeats
  `docs/protocol.md`.
- Any change to the extension's code or behaviour.

## Key references

Verified anchor points (line numbers as of 2026-10-28):

- `docs/knowledge/data/releases/unreleased.md:24` — `## Added` link to
  `features/vscode-expo-bridge`
- `docs/knowledge/data/releases/unreleased.md:92` — first of seven `## Fixed`
  links to `bugs/expo-bridge-*` (through line 110)
- `docs/knowledge/data/releases/unreleased.md:45` — `features/expo-eas-builds`
  under `## Added`
- `docs/knowledge/data/architecture/template-boundary.md:272` — Expo profile
  paragraph linking `vscode-expo-bridge.md`
- `docs/knowledge/data/someday/devcontainer-forwarded-agent-exposure.md:8` —
  `sources` entry, and `:13` the prose link to
  `plans/20261015-vscode-expo-bridge`
- `docs/research/vscode-vulnerability/deep-technical.md:6` — link to
  `plans/20261015-vscode-expo-bridge`
- `docs/knowledge/data/log.md` — 25 links to moved documents
- `docs/knowledge/data/features/expo-eas-builds.md:1` — frontmatter; no bridge
  wiring in its Behaviour today
- `docs/knowledge/data/spec/template-consumption.md:203` — already links the
  extension repository by URL
- `.agents/plugins/agentdev/skills/iwe-bootstrap/SKILL.md:44` — Workflow 2,
  `bootstrap-iwe.sh [--root <dir>]`
- vscode-expo-bridge `AGENTS.md:1` — packaging-only instructions
- vscode-expo-bridge `README.md:73` — `## Versioning`, the patch bump rule
- vscode-expo-bridge `.prettierignore:1` — no `docs/knowledge` entry;
  `package.json` `lint` is `prettier --check .`
