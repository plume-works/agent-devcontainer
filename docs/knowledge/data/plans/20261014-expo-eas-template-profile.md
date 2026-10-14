---
type: plan
created: 2026-10-14
description: An opt-in Expo profile in the template-consume skill that prepares an adopted devcontainer for Expo's official Claude plugin and EAS cloud iOS builds — token passthrough, Expo firewall hosts, a bun pin in eas.json, and an AGENTS.md merge rule.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-14T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: docs/knowledge/data/spec/template-consumption.md
- resource: docs/knowledge/data/architecture/template-boundary.md
- resource: .devcontainer/devcontainer.json
- resource: https://github.com/expo/skills
- resource: https://docs.expo.dev/accounts/programmatic-access/
- resource: https://expo.dev/pricing
---

# Expo profile for template adoption

## Context

An Expo app needs native iOS builds, which need macOS and Xcode. The
devcontainer is Linux. EAS Build runs the native build on Expo's cloud Macs and
is driven entirely from the Linux devcontainer.

Expo already publishes the agent side. A new Expo app ships
`.claude/settings.json` enabling `expo@claude-plugins-official`
([expo/skills](https://github.com/expo/skills)), whose skills cover EAS build
and submit, development clients, EAS Workflows, and EAS Simulator. What the
template must supply is an environment those skills can run in, under these
constraints:

- **Auth:** `EXPO_TOKEN` authenticates every non-interactive `eas` command; a
  project is linked once with `eas init --non-interactive`.
- **bun version:** EAS macOS workers do not default to the image's bun, and the
  image's bun writes `bun.lock` `lockfileVersion: 2`, which an older bun cannot
  read under `--frozen-lockfile`; every build profile therefore pins `bun` to
  the image's bun version.
- **Git root:** EAS archives the project with `git clone` of the enclosing
  repository, so the app must be tracked in the consumer repository, never under
  an ignored path.
- **Network:** a build talks to `api.expo.dev`, `cdp.expo.dev`, and
  `storage.googleapis.com` (project upload and log files); artifacts redirect
  through `expo.dev` and `api.expo.dev` to `wf-artifacts.eascdn.net`; the Expo
  plugin's MCP server is `mcp.expo.dev`. `storage.googleapis.com` and
  `wf-artifacts.eascdn.net` are CDN hosts whose addresses rotate.
- **Secrets on disk:** EAS Simulator writes a session token to
  `.env.eas-simulator` in the project root.
- **Commands:** Expo's skills write `npx --yes eas-cli@latest`; this repository
  runs every JavaScript tool through `bunx`, so the merged `AGENTS.md`
  translates `npx` to `bunx` (`bunx eas-cli@latest`).
- **Two `AGENTS.md` files:** the Expo template ships a root `AGENTS.md`, and the
  template treats the root `AGENTS.md` as Template-class.

## Approach

Add an opt-in **Expo profile** to `/agentdev:template-consume`. Setup mode asks
whether the consumer is an Expo app; when it is, a new guide section, "Optional
Expo setup", applies these edits to the consumer's copied files:

1. `.devcontainer/devcontainer.json` `containerEnv` gains
   `"EXPO_TOKEN": "${localEnv:EXPO_TOKEN}"`. The token stays in the host
   environment or the hosting platform's secret store, never in a volume or the
   repository.
2. `.devcontainer/firewall-allowlist.txt` gains an Expo section listing the
   hosts in `## Context`, with a comment that the two CDN hosts may need a
   container restart when their addresses rotate.
3. `.gitignore` gains `.env.eas-simulator`.
4. Every build profile in `eas.json` sets `"bun"` to the output of
   `bun --version` inside the devcontainer.
5. The root `AGENTS.md` keeps the template's content and gains an `## Expo`
   section holding the Expo template's `AGENTS.md` body verbatim, followed by
   the command-translation line in Task 3. The Expo template's `AGENTS.md` is
   then deleted, and the progress document records the root `AGENTS.md` as
   customized so update mode merges it manually.
6. `.claude/settings.json` keeps `expo@claude-plugins-official` in
   `enabledPlugins` alongside the template's entries.

The marker records the choice as `"expo"` in `optional_bundles`. It adds no
`tracked_paths`: every edit lands in files the template already tracks or the
consumer owns. Update mode, when it applies a change to
`devcontainer-compose-pins.yml`, compares `bun --version` in the rebuilt
container with `eas.json` and updates the pin.

Rejected: an agentdev EAS skill — it would duplicate Expo's official plugin.
Rejected: guidance alone with no profile — update mode would have no record that
the consumer is an Expo app, so the bun pin and the `AGENTS.md` merge would be
missed on update. Rejected: persisting the token on the `agentdev-agents-auth`
volume — the token belongs to the hosting environment, where it can be scoped
and revoked, not to agent state shared by every devcontainer instance.

Assumptions:

- `"expo"` joins `optional_bundles` rather than a new marker field; the field
  already means "an optional piece this consumer opted into".
- The Expo `AGENTS.md` is merged as a verbatim section rather than kept as a
  second file, because the root `AGENTS.md` is the one instruction file every
  agent reads and `CLAUDE.md` only includes it.

## Implementation Steps

### Task 1: Ask the Expo scope question and record it

**Files:** Modify: `.agents/plugins/agentdev/skills/template-consume/SKILL.md`

- [ ] Setup step 3 asks whether the consumer is an Expo app and, when it is,
  runs the guide's "Optional Expo setup".
- [ ] The marker table's `optional_bundles` row names `"expo"` and states that
  it adds no `tracked_paths`.
- [ ] Update mode gains the bun-pin check after a
  `devcontainer-compose-pins.yml` change for consumers whose `optional_bundles`
  includes `"expo"`.

### Task 2: Write "Optional Expo setup" in the consumption guide

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [ ] A new `## Optional Expo setup` section, placed before
  `## Optional custom-image setup`, with the six edits from `## Approach`, the
  git-root requirement, the one-time `eas init --non-interactive`, and where to
  set `EXPO_TOKEN` for a local Docker host and for Codespaces.
- [ ] Workflow A step 6 and Workflow B step 2 point an Expo consumer at that
  section.

### Task 3: Write the command-translation line

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [ ] The guide's `## Expo` merge instruction carries this line verbatim, to be
  appended after the Expo template's body:

``` markdown
Expo's skills and documentation write `npx`; in this repository run the same
command with `bunx` (for example `bunx eas-cli@latest build`), as the bun rule
above requires.
```

### Task 4: Record the profile in the template boundary

**Files:** Modify: `docs/knowledge/data/architecture/template-boundary.md`

- [ ] A `## Optional Expo profile` section after the knowledge-base bundle
  states that the profile edits Template and Customize files without adding
  tracked paths, and that it leaves the root `AGENTS.md` customized.

### Task 5: Validate the catalog change

- [ ] `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.
- [ ] `uv run pytest .agents/plugins/agentdev/tests/test_template_consume_check_updates.py`
  passes.

### Task 6: Adopt the profile end to end on a scratch Expo app

- [ ] In a new repository holding a blank `bun create expo` app, run
  `/agentdev:template-consume` setup with the Expo profile, rebuild the
  devcontainer with `EXPO_TOKEN` set on the host, and submit
  `bunx eas-cli@latest build -p ios --profile development --non-interactive --no-wait --json`
  for an `ios.simulator: true` profile; the build reaches `FINISHED`. This
  spends one EAS iOS build.

### Task 7: Token passthrough in a Codespace

- [ ] In a Codespace of the Task 6 repository with an `EXPO_TOKEN` Codespaces
  secret, `bunx eas-cli@latest whoami` reports the account. Record in
  `## Verification results` if `${localEnv:EXPO_TOKEN}` does not resolve there
  and the guide needs a different mechanism.

## Spec changes

Modifies [Template consumption](../spec/template-consumption.md):

``` markdown
## ADDED Requirements

### Requirement: an Expo consumer is prepared for EAS cloud builds

When the consumer is an Expo app, setup SHALL record `"expo"` in
`optional_bundles` without adding any `tracked_paths`, and SHALL leave the
consumer with: `EXPO_TOKEN` passed from the host environment into the
devcontainer through `containerEnv` and stored nowhere in the repository or a
volume; the Expo hosts in the firewall allowlist; `.env.eas-simulator` ignored
by git; every `eas.json` build profile pinning `bun` to the devcontainer's bun
version; and one root `AGENTS.md` that keeps the template's content and holds
the Expo template's `AGENTS.md` body under an `## Expo` section.

#### Scenario: an Expo app adopts the template

- **WHEN** setup runs in a repository whose app was created by
  `create-expo-app` and the user confirms it is an Expo app
- **THEN** the marker's `optional_bundles` includes `"expo"`
- **AND** the Expo template's separate `AGENTS.md` no longer exists
- **AND** the progress document records the root `AGENTS.md` as customized

#### Scenario: the image's bun changes

- **WHEN** update mode applies a change to `devcontainer-compose-pins.yml` for a
  consumer whose `optional_bundles` includes `"expo"`
- **THEN** each `eas.json` build profile's `bun` is compared with
  `bun --version` in the rebuilt devcontainer and updated when they differ

#### Scenario: a non-Expo consumer

- **WHEN** the user says the consumer is not an Expo app
- **THEN** setup makes none of the Expo edits and `optional_bundles` omits
  `"expo"`
```

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.
- `uv run pytest .agents/plugins/agentdev/tests/test_template_consume_check_updates.py`
  passes.
- Task 6's EAS build reaches `FINISHED` from a devcontainer set up only by the
  guide.
- Task 7's `whoami` succeeds inside a Codespace.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- An agentdev skill for EAS builds, a fingerprint gate, or build polling —
  Expo's official plugin owns the agent workflow.
- Apple signing for device and store builds; the profile covers simulator
  builds, which need none, and `eas credentials` remains a one-time human step.
- EAS Simulator and Maestro, which are account- and plan-gated.
- Token passthrough on Coder workspaces, which is configured in the
  `coder-ide-baseline` template, not here.
- Native macOS hosts.
- Changes to this repository's own `.devcontainer/`.

## Key references

Verified anchor points (line numbers as of 2026-10-14):

- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:50` —
  `optional_bundles` row of the marker table
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:96` — setup step 3,
  the scope questions
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:234` —
  `## Default Template Surface`; `:264` the `custom-image` path addition
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:227`
  — Workflow A step 6 item 6, the firewall allowlist review
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:582`
  — Workflow B `### 2. Merge agent-facing configuration`
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:925`
  — `## Optional custom-image setup`; `:970` `## Ongoing maintenance`
- `.devcontainer/devcontainer.json:20` — `containerEnv` block
- `.claude/settings.json` — `enabledPlugins`, already holding
  `claude-plugins-official` entries
- `docs/knowledge/data/spec/template-consumption.md:81` — Requirement: adoption
  is recorded for later updates
- `docs/knowledge/data/architecture/template-boundary.md:195` —
  `## Optional custom-image bundle`; `:221` `## Optional knowledge-base bundle`
