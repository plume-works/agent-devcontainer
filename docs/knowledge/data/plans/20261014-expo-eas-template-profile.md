---
type: plan
created: 2026-10-14
description: EXPO_TOKEN passthrough in the template devcontainer, plus an opt-in Expo profile in the template-consume skill that prepares an adopted devcontainer for Expo's official Claude plugin and EAS cloud iOS builds — Expo firewall hosts, a bun pin in eas.json, and an AGENTS.md merge rule.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-15T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: docs/knowledge/data/spec/template-consumption.md
- resource: docs/knowledge/data/architecture/template-boundary.md
- resource: docs/knowledge/data/spec/coder-ide-baseline.md
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
  project is linked once with `eas init --non-interactive`. An empty
  `EXPO_TOKEN` is treated as no token, so passing an unset host variable through
  is inert.
- **Coder:** in a `coder-ide-baseline` workspace, a Coder user secret reaches
  the processes the Dev Container's sub-agent starts — terminals, IDE sessions,
  agents — and not the Dev Container's lifecycle hooks ([Coder IDE baseline
  template](../spec/coder-ide-baseline.md)).
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

The template's own `.devcontainer/devcontainer.json` passes the token for every
consumer: `containerEnv` gains `"EXPO_TOKEN": "${localEnv:EXPO_TOKEN}"`. The
token stays in the host environment or the hosting platform's secret store,
never in a volume or the repository. A consumer that never sets it gets an
empty, inert variable. On a local Docker host the token comes from the
environment that runs `devcontainer up`; on Coder it is a Coder user secret,
which the sub-agent supplies to the sessions it starts.

On top of that, add an opt-in **Expo profile** to `/agentdev:template-consume`.
Setup mode asks whether the consumer is an Expo app; when it is, a new guide
section, "Optional Expo setup", applies these edits to the consumer's copied
files:

1. `.devcontainer/firewall-allowlist.txt` gains an Expo section listing the
   hosts in `## Context`, with a comment that the two CDN hosts may need a
   container restart when their addresses rotate.
2. `.gitignore` gains `.env.eas-simulator`.
3. Every build profile in `eas.json` sets `"bun"` to the output of
   `bun --version` inside the devcontainer.
4. The root `AGENTS.md` keeps the template's content and gains an `## Expo`
   section holding the Expo template's `AGENTS.md` body verbatim, followed by
   the command-translation line in Task 3. The Expo template's `AGENTS.md` is
   then deleted, and the progress document records the root `AGENTS.md` as
   customized so update mode merges it manually.
5. `.claude/settings.json` keeps `expo@claude-plugins-official` in
   `enabledPlugins` alongside the template's entries.

The marker records the choice as `"expo"` in `optional_bundles`. It adds no
`tracked_paths`: every edit lands in files the template already tracks or the
consumer owns. Update mode, when it applies a change to
`devcontainer-compose-pins.yml`, compares `bun --version` in the rebuilt
container with `eas.json` and updates the pin.

Rejected: an agentdev EAS skill — it would duplicate Expo's official plugin.
Rejected: passing the token only from the profile —
`.devcontainer/devcontainer.json` is Template-class, so an Expo-only edit makes
the consumer's copy diverge from upstream and turns every later devcontainer
update into a manual merge, while the template-wide variable costs non-Expo
consumers nothing. Rejected: guidance alone with no profile — update mode would
have no record that the consumer is an Expo app, so the bun pin and the
`AGENTS.md` merge would be missed on update. Rejected: persisting the token on
the `agentdev-agents-auth` volume — the token belongs to the hosting
environment, where it can be scoped and revoked, not to agent state shared by
every devcontainer instance.

Assumptions:

- `"expo"` joins `optional_bundles` rather than a new marker field; the field
  already means "an optional piece this consumer opted into".
- The Expo `AGENTS.md` is merged as a verbatim section rather than kept as a
  second file, because the root `AGENTS.md` is the one instruction file every
  agent reads and `CLAUDE.md` only includes it.

## Implementation Steps

### Task 1: Ask the Expo scope question and record it

**Files:** Modify: `.agents/plugins/agentdev/skills/template-consume/SKILL.md`

- [x] Setup step 3 asks whether the consumer is an Expo app and, when it is,
  runs the guide's "Optional Expo setup".
  - **Evidence:** committed with this tick — `template-consume/SKILL.md` setup
    step 3 adds "Is the consumer an Expo app?" and routes an Expo app to the
    guide's Optional Expo setup; `validate_agent_files` reports 62/62 skills
    valid, 0 errors.
- [x] The marker table's `optional_bundles` row names `"expo"` and states that
  it adds no `tracked_paths`.
  - **Evidence:** committed with this tick — the `optional_bundles` row of the
    `template-consume/SKILL.md` marker table adds `"expo"` with "it adds no
    `tracked_paths`".
- [x] Update mode gains the bun-pin check after a
  `devcontainer-compose-pins.yml` change for consumers whose `optional_bundles`
  includes `"expo"`.
  - **Evidence:** committed with this tick — `template-consume/SKILL.md` update
    step 5 compares each `eas.json` build profile's `bun` with `bun --version`
    in the rebuilt devcontainer when an applied change touches
    `devcontainer-compose-pins.yml` and `optional_bundles` includes `"expo"`.

### Task 2: Write "Optional Expo setup" in the consumption guide

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [x] A new `## Optional Expo setup` section, placed before
  `## Optional custom-image setup`, with the numbered edits from `## Approach`
  plus the `containerEnv` token edit that Task 9 removes, the git-root
  requirement, the one-time `eas init --non-interactive`, and where to set
  `EXPO_TOKEN` for a local Docker host and for Codespaces.
  - **Evidence:** committed with this tick — `consumption-guide.md`
    `## Optional Expo setup` sits directly before
    `## Optional custom-image setup` and carries the six numbered edits, the
    git-root paragraph, `bunx eas-cli@latest init --non-interactive`, and the
    local Docker host and Codespaces token bullets.
- [x] Workflow A step 6 and Workflow B step 2 point an Expo consumer at that
  section.
  - **Evidence:** committed with this tick — Workflow A step 6 item 6 and
    Workflow B `### 2. Merge agent-facing configuration` each link
    `#optional-expo-setup`.

### Task 3: Write the command-translation line

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [x] The guide's `## Expo` merge instruction carries this line verbatim, to be
  appended after the Expo template's body:
  - **Evidence:** committed with this tick — `consumption-guide.md`
    `## Optional Expo setup` edit 5 carries the line below in a fenced
    `markdown` block, word for word.

``` markdown
Expo's skills and documentation write `npx`; in this repository run the same
command with `bunx` (for example `bunx eas-cli@latest build`), as the bun rule
above requires.
```

### Task 4: Record the profile in the template boundary

**Files:** Modify: `docs/knowledge/data/architecture/template-boundary.md`

- [x] A `## Optional Expo profile` section after the knowledge-base bundle
  states that the profile edits Template and Customize files without adding
  tracked paths, and that it leaves the root `AGENTS.md` customized.
  - **Evidence:** committed with this tick — `template-boundary.md`
    `## Optional Expo profile` follows `## Optional knowledge-base bundle`,
    names the edited files with no added `tracked_paths`, and records the root
    `AGENTS.md` as customized; `iwe schema validate` passes.

### Task 5: Validate the catalog change

- [x] `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.
  - **Evidence:** run at 25057b7 — 62/62 skills valid, 0 errors, 0 warnings.
- [x] `uv run pytest .agents/plugins/agentdev/tests/test_template_consume_check_updates.py`
  passes.
  - **Evidence:** run at 25057b7 — 14 passed.

### Task 6: Adopt the profile end to end on a scratch Expo app

- [x] In a new repository holding a blank `bun create expo` app, run
  `/agentdev:template-consume` setup with the Expo profile, rebuild the
  devcontainer with `EXPO_TOKEN` set on the host, and submit
  `bunx eas-cli@latest build -p ios --profile development --non-interactive --no-wait --json`
  for an `ios.simulator: true` profile; the build reaches `FINISHED`. This
  spends one EAS iOS build.
  - **Evidence:** at 3fddc4c, a local git repository holding a blank
    `bun create expo` app adopted Workflow B steps 1–2 plus Optional Expo setup
    edits 1–5, with `"expo"` in `optional_bundles`; the tooling-baseline,
    GitHub, and project-memory steps were not applied. Its devcontainer, started
    with `devcontainer up` on docker-in-docker with `EXPO_TOKEN` exported, ran
    `eas init --non-interactive` and, with `expo.ios.bundleIdentifier` set in
    `app.json`, the `development` simulator build. EAS build
    `0ba2cbd9-c0ec-4be4-a3ba-73e089a6f0f7` on project
    `@antonmatosov/expo-scratch` reached `FINISHED`.

### Task 7: Token on a Coder workspace

- [ ] In a `coder-ide-baseline` workspace with an `EXPO_TOKEN` Coder user
  secret, its Dev Container rebuilt from a branch carrying the Task 8
  passthrough, a shell started by the Dev Container's sub-agent sees
  `EXPO_TOKEN` and `bunx eas-cli@latest whoami` reports the account. Record in
  `## Verification results` whether `${localEnv:EXPO_TOKEN}` resolves into the
  container's own environment there (the environment of PID 1 or of a
  `docker exec` shell).

### Task 8: Pass `EXPO_TOKEN` through the template devcontainer

**Files:** Modify: `.devcontainer/devcontainer.json`

- [x] `containerEnv` carries `"EXPO_TOKEN": "${localEnv:EXPO_TOKEN}"` with a
  one-line comment that the value comes from the host environment or the hosting
  platform's secret store.
  - **Evidence:** committed with this tick — `.devcontainer/devcontainer.json`
    `containerEnv` adds `EXPO_TOKEN` after `DEV_WORKSPACE_FOLDER`; the file
    parses as JSONC with `containerEnv.EXPO_TOKEN` equal to
    `${localEnv:EXPO_TOKEN}`.

### Task 9: Point the profile's token guidance at the template devcontainer

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`docs/knowledge/data/architecture/template-boundary.md`

- [x] The guide's `## Optional Expo setup` no longer edits `containerEnv`; its
  numbered edits are the five in `## Approach`, and its token paragraph states
  that the template devcontainer already passes `EXPO_TOKEN`, keeping the local
  Docker host and Codespaces instructions.
  - **Evidence:** committed with this tick — `consumption-guide.md`
    `## Optional Expo setup` numbers edits 1–5 (allowlist, `.gitignore`,
    `eas.json`, `AGENTS.md`, `.claude/settings.json`) with no `containerEnv`
    edit; the token paragraph opens "The template devcontainer already passes
    `EXPO_TOKEN`" and keeps both host bullets.
- [x] `template-boundary`'s `## Optional Expo profile` no longer lists
  `.devcontainer/devcontainer.json` among the files the profile edits, and
  states that the template devcontainer passes `EXPO_TOKEN` for every consumer.
  - **Evidence:** committed with this tick — `template-boundary.md`
    `## Optional Expo profile` lists four tracked files plus `eas.json` and adds
    a paragraph that the profile leaves `.devcontainer/devcontainer.json`
    untouched because the template devcontainer passes `EXPO_TOKEN` for every
    consumer; `iwe schema validate` passes.

### Task 10: Token passthrough on a local Docker host

- [x] With `EXPO_TOKEN` exported on a local Docker host, rebuild this
  repository's devcontainer; a shell opened with `docker exec` (not inherited
  from an agent session) sees `EXPO_TOKEN`, and `bunx eas-cli@latest whoami`
  reports the account. With the variable unset on the host, the rebuilt
  container's `EXPO_TOKEN` is empty and `whoami` reports "Not logged in".
  - **Evidence:** at 3fddc4c, `devcontainer up` (`@devcontainers/cli`) against a
    docker-in-docker daemon, from a scratch copy of this repository: with
    `EXPO_TOKEN` exported, a `docker exec` shell sees a 40-character
    `EXPO_TOKEN` and `bunx eas-cli@latest whoami` lists the account; after
    `--remove-existing-container` with the variable unset, `EXPO_TOKEN` is
    defined and empty and `whoami` reports "Not logged in". Not repeated through
    VS Code on a macOS Docker host.

### Task 11: Replace the Codespaces token bullet with Coder

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [ ] In `## Optional Expo setup`, the `**GitHub Codespaces:**` token bullet is
  replaced by this bullet, verbatim:

``` markdown
- **Coder (`coder-ide-baseline`):** add a Coder user secret named
  `EXPO_TOKEN`, then restart the workspace. The secret reaches the processes
  the Dev Container's sub-agent starts — terminals, IDE sessions, and agents —
  but not lifecycle hooks.
```

## Spec changes

Modifies [Template consumption](../spec/template-consumption.md):

``` markdown
## ADDED Requirements

### Requirement: an Expo consumer is prepared for EAS cloud builds

The template devcontainer SHALL pass `EXPO_TOKEN` from the host environment
into the container through `containerEnv` for every consumer, and SHALL store it
nowhere in the repository or a volume.

When the consumer is an Expo app, setup SHALL record `"expo"` in
`optional_bundles` without adding any `tracked_paths`, SHALL NOT add a second
`EXPO_TOKEN` definition, and SHALL leave the consumer with: the Expo hosts in the
firewall allowlist; `.env.eas-simulator` ignored
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
- **AND** the devcontainer still passes `EXPO_TOKEN`, empty when the host does
  not set it

#### Scenario: a Coder workspace supplies the token

- **WHEN** `EXPO_TOKEN` is a Coder user secret and the Dev Container is rebuilt
  with the passthrough
- **THEN** a shell started by the Dev Container's sub-agent sees `EXPO_TOKEN`
  and `eas whoami` reports the account
```

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.
- `uv run pytest .agents/plugins/agentdev/tests/test_template_consume_check_updates.py`
  passes.
- Task 6's EAS build reaches `FINISHED` from a devcontainer set up only by the
  guide, plus the app config that Expo's plugin owns.
- Task 7's `whoami` succeeds in a sub-agent shell of a rebuilt Coder workspace.
- Task 10's `whoami` succeeds in a devcontainer rebuilt on a local Docker host
  with `EXPO_TOKEN` exported, and reports "Not logged in" without it.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- An agentdev skill for EAS builds, a fingerprint gate, or build polling —
  Expo's official plugin owns the agent workflow.
- App config such as `expo.ios.bundleIdentifier`, which a non-interactive
  `eas build` requires; Expo's plugin owns the app's configuration.
- Apple signing for device and store builds; the profile covers simulator
  builds, which need none, and `eas credentials` remains a one-time human step.
- EAS Simulator and Maestro, which are account- and plan-gated.
- Token passthrough on GitHub Codespaces.
- Changes to the `coder-ide-baseline` template.
- Native macOS hosts.
- Any change to this repository's own `.devcontainer/` beyond the `EXPO_TOKEN`
  passthrough; the Expo firewall hosts stay in the profile, since only Expo
  consumers need them.

## Key references

Verified anchor points (line numbers as of 2026-10-16):

- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:50` —
  `optional_bundles` row of the marker table
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:96` — setup step 3,
  the scope questions
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:241` —
  `## Default Template Surface`; `:271` the `custom-image` path addition
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:227`
  — Workflow A step 6 item 6, the firewall allowlist review
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:583`
  — Workflow B `### 2. Merge agent-facing configuration`
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:998`
  — `## Optional custom-image setup`; `:1043` `## Ongoing maintenance`
- `.devcontainer/devcontainer.json:20` — `containerEnv` block; `:30`
  `EXPO_TOKEN`
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md:928`
  — `## Optional Expo setup`; `:980` the token paragraph; `:989` the
  `**GitHub Codespaces:**` bullet that Task 11 replaces
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md:199` — update-mode
  bun-pin check for `"expo"` consumers
- `docs/knowledge/data/architecture/template-boundary.md:254` —
  `## Optional Expo profile`
- `.claude/settings.json:48` — `enabledPlugins`, already holding
  `claude-plugins-official` entries
- `docs/knowledge/data/spec/template-consumption.md:81` — Requirement: adoption
  is recorded for later updates
- `docs/knowledge/data/architecture/template-boundary.md:196` —
  `## Optional custom-image bundle`; `:222` `## Optional knowledge-base bundle`
- `docs/knowledge/data/spec/coder-ide-baseline.md:51` — Requirement: Coder user
  secrets reach only agent-started processes
