---
type: plan
description: Add non-blocking, repository-aware CBM registration to the agentdev OpenCode bridge.
created: 2026-10-18
release:
- features/opencode-workspace-cbm-indexing
generated:
  by: opencode/gpt-6.1-sol
  at: 2026-10-18T18:47:00Z
sources:
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
- resource: .agents/plugins/agentdev/tests/opencode/bridge.test.ts
- resource: .devcontainer/scripts/codebase-memory-mcp-start.sh
- resource: .devcontainer/scripts/codebase-memory-mcp-index.sh
- resource: .devcontainer/scripts/reinstall-agentdev-opencode.sh
---

# Automatically index OpenCode workspaces in CBM

## Context

[Automatic CBM indexing for OpenCode
workspaces](../features/opencode-workspace-cbm-indexing.md) lets a developer
open another repository in an existing container and use its codebase graph
without asking an agent to initialize it. The container's CBM start and attach
scripts index `DEV_WORKSPACE_FOLDER`; the OpenCode bridge currently loads the
catalog but does not register the active repository.

The scope is OpenCode first, owned by agentdev and distributed with its catalog.
No active plan in the plans hub covers this topic.

## Approach

Pass OpenCode's `PluginInput.directory` into the bridge and launch one
best-effort registration attempt from the config hook after applying the
catalog. Keep CBM-specific logic in a dependency-free sibling TypeScript module.
Only act when merged configuration contains an enabled local
`mcp["codebase-memory-mcp"]` entry with a command. Use that command and its
configured environment over the inherited environment, preserving the
daemon/cache and allowed-root settings. Do not add or rewrite MCP config.

Resolve the canonical Git worktree root with
`git -C <directory> rev-parse --show-toplevel` and realpath. List CBM projects
using `cli --json list_projects --format json`, following every `next_offset`
while `has_more` is true; compare canonical root paths, not project names or
ancestor containment. For an absent root, ensure the daemon is running with
`daemon start`, then submit
`cli --json index_repository --repo-path <root> --async true`. A CLI success
requires a valid response and no MCP `isError`. Use CBM's default indexing mode
and leave repository snapshot persistence off.

The registration promise is not awaited by catalog initialization. Deduplicate
in-flight attempts by canonical root within the plugin process and use CBM's
join semantics across processes. Bound each child command to ten seconds,
terminate timed-out children, limit captured output to 1 MiB per command, and
report errors through OpenCode's logging client without unhandled promise
rejections. A failed attempt is eligible again on the next workspace
initialization; do not poll for completion or run a periodic retry loop.

Implement registration in the existing agentdev bridge and leave CBM's generated
augmentation plugin unchanged. Scanning all of `/workspaces` is rejected: the
active repository is sufficient, and unopened repositories need no indexing
work.

## Implementation Steps

### Task 1: Register the active repository without blocking OpenCode

**Files:** Create:
`.agents/plugins/agentdev/.opencode-plugin/workspace-index.ts`,
`.agents/plugins/agentdev/tests/opencode/workspace-index.test.ts`; Modify:
`.agents/plugins/agentdev/.opencode-plugin/index.ts`,
`.agents/plugins/agentdev/tests/opencode/bridge.test.ts`.

- [x] First add failing Bun tests with injected subprocess/logging adapters and
  isolated Git fixtures under repository `.tmp/`. Cover another repository than
  the catalog/container root, a subdirectory, symlink, linked worktree, non-Git
  directory, exact-root matching, a matching project on a later page, and an
  absent root. Verify the configured command/environment are used, registered
  roots are skipped, missing/disabled/remote MCP is skipped, duplicate attempts
  share work, and separate roots register independently.
  - **Evidence:** The focused Bun run first failed on the missing helper; the
    combined bridge/workspace suite now passes 36 tests, including real Git,
    symlink, linked-worktree, pagination, environment, and concurrency fixtures.
- [x] Add failing bridge tests proving a pending indexing request does not delay
  config/catalog availability, and error-path tests for spawn failure, timeout,
  oversized output, malformed JSON, MCP `isError`, denied roots, and a failed
  attempt followed by a fresh initialization. Assert diagnostics and no index
  submission after an unsuccessful project lookup.
  - **Evidence:**
    `bun test ./.agents/plugins/agentdev/tests/opencode/bridge.test.ts ./.agents/plugins/agentdev/tests/opencode/workspace-index.test.ts`
    passes 36 tests; logging initially failed before wiring. Subprocess tests
    verify timeout termination and both output streams' bounds.
- [x] Implement the helper and bridge wiring to satisfy those tests, using
  argument arrays rather than shell interpolation, preserving the existing
  catalog and skill-hook behavior and adding no runtime dependencies. Missing
  optional CBM configuration and non-Git directories are quiet skips.
  - **Evidence:** The combined Bun suite passes 38 tests;
    `uv run pytest .agents/plugins/agentdev/tests` passes 139 tests;
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    reports zero errors and warnings.

### Task 2: Verify the installed-host and shared-daemon behavior

**Files:** Create: none; Modify: this plan's `## Verification results`.

- [x] Run the installed OpenCode bridge against a small disposable Git
  repository under `.tmp/`, using an isolated OpenCode config and CBM cache.
  Keep a daemon running for the test. Open a second disposable repository
  through the same host setup; poll CBM status explicitly for verification, and
  confirm both roots remain indexed. Repeat opening from a subdirectory and
  confirm no duplicate project or new indexing job. Record commands and results.
  Stop the test daemon and clean up its resources afterward.
  - **Evidence:** Installed-host verification with OpenCode 1.19.3 and CBM
    0.12.1 passed: two exact roots reached `succeeded`; reopening a subdirectory
    preserved the original job and the two-project list. See Verification
    results.
- [x] Verify with the pinned OpenCode host that disabled CBM and an unavailable
  CBM executable leave skills and commands usable and produce the specified
  skip/diagnostic behavior. Record the observed config-hook timing and local MCP
  command compatibility, including the CBM JSON envelope used by the helper.
  - **Evidence:** Pinned-host checks passed for both configurations:
    `opencode debug skill` and `opencode debug config` retained the catalog;
    disabled CBM emitted no registration warning, and an unavailable executable
    emitted an `agentdev` warning. The combined Bun suite passes 40 tests.

### Task 3: Document and map the shipped integration

**Files:** Modify:
`docs/knowledge/data/architecture/opencode-catalog-bridge.md`,
`docs/knowledge/data/codebase/agents/plugins/agentdev/opencode-plugin.md`;
Create: codebase-map children only if required by the map skill.

- [ ] Document workspace registration, its configuration gate, background
  readiness, failure diagnostics, and restart requirement in the bridge
  architecture document. Refresh the touched codebase map with current source
  digests using the map workflow. Keep the generated CBM plugin unmodified.

## Spec changes

Create `data/spec/opencode-workspace-cbm-indexing` at Ship and link it from the
spec hub. Existing catalog requirements remain applicable. Intended delta:

``` markdown
## ADDED Requirements

### Requirement: register the active Git workspace

The bridge SHALL resolve OpenCode's active directory to its canonical Git
worktree root and register an absent root with the shared CBM daemon only when
the configured codebase-memory MCP is local and enabled. It SHALL use the
configured command and environment without broadening allowed roots or changing
MCP configuration, and SHALL retain existing indexed projects.

#### Scenario: a second repository opens in the container

- **WHEN** OpenCode initializes in an unindexed Git repository with local CBM enabled
- **THEN** it submits background indexing for that repository, independently of
  the catalog location and DEV_WORKSPACE_FOLDER, retaining other projects.

#### Scenario: a registered root is found on a later project page

- **WHEN** any page of the project list contains the canonical active root
- **THEN** the bridge submits no indexing request for it.

#### Scenario: a subdirectory or linked worktree opens

- **WHEN** OpenCode initializes in a repository subdirectory, symlink, or linked worktree
- **THEN** the bridge uses the canonical worktree root and treats separate
  worktree roots as distinct repositories.

#### Scenario: automatic indexing does not apply

- **WHEN** the directory is not a Git worktree or CBM config is absent, disabled, or remote
- **THEN** the bridge skips automatic registration without changing configuration.

### Requirement: registration does not block catalog use

The bridge SHALL keep catalog initialization independent of indexing
completion, deduplicate in-flight registration for a root, and handle failed
or timed-out commands with bounded resource use and OpenCode diagnostics.

#### Scenario: indexing is pending

- **WHEN** a registration request or background index remains pending
- **THEN** catalog skills, commands, agents, and skill-name rewriting remain available.

#### Scenario: CBM lookup or submission fails

- **WHEN** a command cannot start, exceeds ten seconds or the output limit,
  returns invalid data or an MCP error, or rejects the root
- **THEN** the bridge logs a diagnostic without an unhandled rejection or
  config failure, submits no index after a failed lookup, and permits another
  attempt on a later workspace initialization.

#### Scenario: multiple initializations target the same root

- **WHEN** registration overlaps for one canonical root
- **THEN** in-process requests share the attempt and daemon requests join
  existing indexing instead of starting competing jobs.
```

## Verification

- `bun test ./.agents/plugins/agentdev/tests/opencode/workspace-index.test.ts`
  first demonstrates the new behavior failing, then passes.
- `bun test ./.agents/plugins/agentdev/tests/opencode/bridge.test.ts ./.agents/plugins/agentdev/tests/opencode/workspace-index.test.ts`
  verifies registration and existing bridge behavior together.
- For Task 2, run `opencode debug skill` and `opencode debug config` with the
  isolated fixture as working directory and the bridge registered. Verify both
  roots with `codebase-memory-mcp cli --json list_projects --format json` and
  completion with
  `cli --json index_repository --repo-path <root> --status true`, using the same
  isolated cache. No model invocation is needed.
- `iwe normalize` and `iwe schema validate` pass after knowledge edits.

## Verification results

- **Automated checks:** The combined bridge/workspace Bun suite passes 40 tests,
  the plugin pytest suite passes 139 tests, and catalog validation reports zero
  errors or warnings. Regression coverage includes detached-daemon startup pipes
  and timeout cleanup after the immediate child exits.
- **Installed host:** OpenCode 1.19.3 (the Ansible pin) and CBM 0.12.1 passed
  with isolated OpenCode config, HOME/XDG directories, and CBM cache under
  repository `.tmp/`. A private mount namespace isolated CBM's account-wide
  daemon endpoint. The installed plugin SDK was copied into the isolated config;
  no model invocation was needed.
- **Commands:** `opencode serve --hostname 127.0.0.1 --port <port>` kept the
  host alive; `GET /config?directory=<root>` initialized each workspace.
  `opencode debug skill` and `opencode debug config` verified the catalog in
  each repository and the subdirectory. Verification explicitly polled
  `codebase-memory-mcp cli --json index_repository --repo-path <root> --status true`
  and checked `cli --json list_projects --format json` against both roots. Both
  jobs reached `succeeded`; reopening preserved the original job and exactly two
  registered projects. The test host and daemon were stopped.
- **Timing and failures:** Workspace config responses completed in 125–199 ms
  while registration continued in the background. Disabled CBM was a quiet skip;
  an unavailable executable produced a registration warning through OpenCode's
  logging client. Both retained skills and namespaced commands.
- **CLI compatibility:** The local command array accepts appended CLI and daemon
  arguments with the configured environment. CBM returns an MCP JSON envelope
  with `structuredContent` and `isError`; text-content JSON is also covered by
  tests. Detached daemon startup discards output so inherited pipes cannot keep
  registration waiting after the startup command exits.

## Out of scope

Claude Code/Codex hooks, indexing unopened directories, changing CBM upstream,
editing its generated plugin, broadening CBM access controls, waiting for graph
readiness before agent tools run, periodic retries, and replacing container
start/attach indexing.

## Key references

Verified anchor points (line numbers as of 2026-10-18):

- `.agents/plugins/agentdev/.opencode-plugin/index.ts:37` — BridgeConfig.
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:125` — bridge config and
  tool hooks.
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:150` — plugin server
  forwards PluginInput to the bridge.
- `.agents/plugins/agentdev/tests/opencode/bridge.test.ts:38` — configured test
  helper.
- `.agents/plugins/agentdev/tests/opencode/bridge.test.ts:119` — skill-hook
  regression tests.
- `.devcontainer/scripts/codebase-memory-mcp-start.sh:17` — daemon start and
  original-workspace index.
- `.devcontainer/scripts/codebase-memory-mcp-index.sh:16` — attach-time
  original-workspace index.
- `.devcontainer/scripts/reinstall-agentdev-opencode.sh:14` — catalog bridge
  registration gate.
- `.devcontainer/scripts/codebase-memory-mcp-install.sh:82` — upstream
  client/plugin installation.
