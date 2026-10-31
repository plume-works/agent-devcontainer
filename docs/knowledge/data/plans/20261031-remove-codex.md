---
type: plan
created: 2026-10-31
release:
- features/claude-and-opencode-only-harnesses
- features/codex-full-access-config
description: Remove Codex from the images, the agentdev-runtime package, the agentdev catalog, CI, the e2e suites, and the knowledge graph, leaving Claude Code and OpenCode as the only supported harnesses.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T05:45:00Z
sources:
- resource: docs/knowledge/data/features/claude-and-opencode-only-harnesses.md
- resource: py_packages/agentdev_runtime/agentdev_runtime/catalog.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/cbm.py
- resource: ansible/roles/agentic_tools/tasks/install_catalog.yml
- resource: scripts/e2e/iwe-workflows/harness_codex.py
---

# Remove Codex support

## Context

The maintainer decided that Claude Code and OpenCode are the only harnesses this
repository supports, and that Codex goes entirely: [Claude Code and OpenCode are
the only supported
harnesses](../features/claude-and-opencode-only-harnesses.md). Codex support
today reaches the image build, the `agentdev-runtime` package, the catalog's
packaging, CI, the e2e suites, and about forty knowledge documents, and every
plan that touches the runtime carries Codex work alongside it.

This lands after [Replace the runtime shell scripts with one agentdev-runtime
CLI](20261029-off-bash-migration.md), which moves the Codex code this plan
deletes into `agentdev_runtime` and already deletes the Codex Cloud bootstrap,
and after [Port the catalog's bundled shell scripts to
Python](20261029-catalog-scripts-python.md), and after [Let any session asked to
implement a named plan start Implement](20261031-model-invocable-implement.md),
which removes the Codex gate from `iwe-implement` and whose wording this plan's
spec delta builds on. It lands before [Run the Dev Container as a non-root
account with one home volume](20261030-devcontainer-home-volume.md), so that
plan no longer carries Codex volume and auth work.

[Codex full-access config](../features/codex-full-access-config.md) is
superseded and becomes `deprecated`.

## Approach

Delete, do not deprecate in place. Every Codex code path, file, volume, test,
and e2e harness goes; the catalog stops shipping a Codex package. Documentation
is rewritten to name Claude Code and OpenCode as the two harnesses, and the
decision gets its own architecture document so the repository records why Codex
is absent.

Two things are not Codex support and stay:

- `validate_agent_files` keeps its general `codex` ecosystem, because it is
  released independently and validates other repositories' catalogs (product
  constraint). Only this repository's own CI call drops `codex`.
- Handling of the `chatgpt-codex-connector[bot]` GitHub actor (the review
  acceptance test, the draft-AI-PR override in `reformat.yml`) concerns a
  third-party reviewer on GitHub, not a harness running here.

Rejected: keeping `.codex-plugin/plugin.json` as an untested, install-yourself
package. Without `bin/install-codex-agents.py` Codex loads none of the catalog
agents its skills dispatch, so the package would ship broken.

## Implementation Steps

### Task 1: Confirm the base this plan was written against

**Files:** none

- [ ] Both [off-bash-migration](20261029-off-bash-migration.md) and
  [catalog-scripts-python](20261029-catalog-scripts-python.md) are `stage: done`
  on `main`.
- [ ] Every `## Key references` anchor resolves on `main` to the named symbol,
  and the base text of each `## Spec changes` MODIFIED requirement matches the
  shipped spec apart from the Codex wording this plan removes. Any mismatch
  stops implementation for `/agentdev:iwe-plan` revise mode.

### Task 2: Record the supported-harness decision

**Files:** Create: `docs/knowledge/data/architecture/supported-harnesses.md`;
Modify: `docs/knowledge/data/architecture.md`, `docs/knowledge/data/product.md`

- [ ] `architecture/supported-harnesses` states that Claude Code and OpenCode
  are the supported harnesses and Codex is not, records the rejected
  install-yourself package and why, and records that `validate_agent_files`
  keeps its Codex ecosystem; it is linked from `data/architecture.md`.
- [ ] `data/product.md` names Claude Code and OpenCode wherever it names the
  preinstalled agents or the catalog's audience, and its authoring rule about
  `.codex/` is removed.

### Task 3: Stop shipping a Codex package in the catalog

**Files:** Delete: `.agents/plugins/agentdev/.codex-plugin/plugin.json`,
`.agents/plugins/marketplace.json`, the six
`.agents/plugins/agentdev/skills/*/agents/openai.yaml`,
`.agents/plugins/agentdev/bin/install-codex-agents.py`,
`.agents/plugins/agentdev/tests/test_install_codex_agents.py`,
`.agents/plugins/agentdev/tests/test_explicit_only_parity.py`; Modify:
`.agents/AGENTS.md`, `.claude-plugin/AGENTS.md`,
`.agents/plugins/agentdev/README.md`

- [ ] The files above are gone and
  `git ls-files .agents | grep -i -E 'codex|openai.yaml'` prints nothing.
- [ ] `.agents/AGENTS.md`, `.claude-plugin/AGENTS.md`, and the plugin README
  describe the catalog as consumed by Claude Code and by OpenCode through the
  bridge, validate with `--require-marketplace claude`, and carry no manifest
  version-alignment rule for Codex.
- [ ] `uv run validate_agent_files --recommend . --require-marketplace claude`
  and `uv run pytest .agents/plugins/agentdev/tests` pass.

### Task 4: Remove Codex instructions from catalog skills

**Files:** Modify: `.agents/plugins/agentdev/skills/create-agent/SKILL.md`,
`.agents/plugins/agentdev/skills/create-skill/SKILL.md`,
`.agents/plugins/agentdev/skills/local-reformat/SKILL.md`,
`.agents/plugins/agentdev/skills/pr-review/SKILL.md`,
`.agents/plugins/agentdev/skills/template-consume/SKILL.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [ ] No skill gives Codex-specific instructions: `create-skill` loses its Codex
  skill-creator pointer, `codex plugin add`, and `openai.yaml` guidance;
  `local-reformat` loses its Codex managed-sandbox section; `pr-review` loses
  its Codex tool, model column, and Codex waiting and budget rules;
  `create-agent` names Claude Code and OpenCode as consumers.
- [ ] `template-consume` and its consumption guide no longer list `.codex/`, the
  `agentdev-codex` volume, Codex policy configuration, or Codex in the
  catalog-install check, and recommend `--require-marketplace claude`.
- [ ] `git grep -i codex -- .agents` prints only lines about the
  `chatgpt-codex-connector[bot]` GitHub actor.

### Task 5: Remove Codex from the agentdev-runtime package

**Files:** Delete:
`py_packages/agentdev_runtime/agentdev_runtime/codex_config.py`,
`py_packages/agentdev_runtime/agentdev_runtime/codex_hooks.py`,
`py_packages/agentdev_runtime/tests/test_codex_config.py`,
`py_packages/agentdev_runtime/tests/test_codex_hooks.py`; Modify:
`py_packages/agentdev_runtime/agentdev_runtime/{catalog,agent_state,cbm,bootstrap,doctor,lifecycle,settings,workspace,cli}.py`,
`py_packages/agentdev_runtime/README.md`,
`py_packages/agentdev_runtime/tests/test_settings.py`

- [ ] `catalog install` registers Claude Code and OpenCode only, and
  `catalog.complete` treats a root as complete when it holds
  `.claude-plugin/marketplace.json` and the OpenCode bridge; a test covers a
  root without `.agents/plugins/marketplace.json` being complete.
- [ ] `agent_state` shares only Claude's credentials, has no Codex auth link,
  applies only the OpenCode policy, and the `state links` subcommand is removed
  along with its call in `lifecycle.ready`.
- [ ] `cbm install` neither creates `$CODEX_HOME/hooks.json` nor repairs a Codex
  `config.toml`.
- [ ] `bootstrap`, `doctor`, `settings`, `workspace`, and `cli` name no Codex
  agent, tool, link check, or `CODEX_HOME`; the package README's settings table
  has no `CODEX_HOME` row.
- [ ] `uv run pytest py_packages/agentdev_runtime` passes.

### Task 6: Update the runtime tests under scripts/tests

**Files:** Delete: `scripts/tests/test_configure_codex.py`,
`scripts/tests/test_repair_codex_cbm_hooks_block.py` (where still present);
Modify:
`scripts/tests/test_agent_runtime_{acceptance,cbm,identity,state,workspace}.py`,
`scripts/tests/test_agentdev_devcontainer_{image,lifecycle,repository}.py`,
`scripts/tests/test_environment_health.py`

- [ ] No test asserts Codex behavior, and the catalog-root fixtures in
  `test_agent_runtime_workspace.py` and
  `test_agentdev_devcontainer_lifecycle.py` no longer write
  `.agents/plugins/marketplace.json`.
- [ ] `git grep -i codex -- scripts/tests` prints nothing, and each modified
  test file passes under `uv run pytest`.

### Task 7: Stop installing Codex in the images and the devcontainer

**Files:** Modify: `ansible/roles/agentic_tools/defaults/main.yml`,
`ansible/roles/agentic_tools/tasks/install_catalog.yml`,
`ansible/roles/agentic_tools/tasks/stage_catalog.yml`,
`ansible/roles/agentic_tools/README.md`,
`ansible/roles/dev_tools/defaults/main.yml`,
`ansible/roles/dev_tools/README.md`, `docker/base/agentdev-base.Dockerfile`,
`docker/deploy/agentdev-deploy.Dockerfile`, `.devcontainer/devcontainer.json`,
`.devcontainer/docker-compose.yml`, `.devcontainer/firewall-allowlist.txt`,
`.dockerignore`; Delete: `.codex/`

- [ ] The `agentic_tools` role installs no `@openai/codex` package (its Renovate
  annotation goes with it), registers no Codex marketplace or plugin, installs
  no Codex agents, and no longer compares a Codex manifest version.
- [ ] `devcontainer.json` declares no `agentdev-codex` volume, the deploy image
  sets no `CODEX_HOME`, and no comment in the touched files names `~/.codex`.
- [ ] The firewall allowlist keeps `api.openai.com` and `chatgpt.com`, now
  labelled as OpenAI provider hosts for OpenCode.
- [ ] `.codex/` and its `.dockerignore` entry are gone.

### Task 8: Remove Codex from CI and repository configuration

**Files:** Modify: `.github/workflows/validate-agent-files.yml`,
`.github/actions/run-claude-responder/action.yml`, `.pre-commit-config.yaml`

- [ ] `validate-agent-files.yml` runs
  `validate_agent_files --recommend . --require-marketplace claude` and its path
  filter has no `.codex/agents/**` entry.
- [ ] The responder action no longer creates `/root/.codex`, and the pre-commit
  hook's `files` pattern no longer names `.codex/agents`.

### Task 9: Remove Codex from the e2e suites

**Files:** Delete: `scripts/e2e/iwe-workflows/harness_codex.py`,
`scripts/e2e/iwe-workflows/test_iwe_workflows_codex.py`,
`scripts/tests/test_e2e_iwe_workflows_codex_publish.py`,
`scripts/tests/test_e2e_iwe_workflows_codex_rollout.py`; Modify:
`scripts/e2e/iwe-workflows/scenarios.py`,
`scripts/tests/test_e2e_iwe_workflows_clone.py`

- [ ] `scenarios.py` has no `CODEX_BUDGET`, no scenario branches on Codex, and
  `git grep -i codex -- scripts/e2e` prints nothing.
- [ ] `uv run pytest scripts/tests/test_e2e_iwe_workflows_clone.py` passes and
  the Claude and OpenCode e2e modules still collect
  (`uv run pytest --collect-only scripts/e2e/iwe-workflows`).

### Task 10: Rewrite the README for two harnesses

**Files:** Modify: `README.md`, `docker/deploy/README.md`

- [ ] Both READMEs name Claude Code and OpenCode wherever they list the
  preinstalled agents, shared logins, or catalog consumers, show no
  `codex login` step, and the validation command reads
  `--require-marketplace claude`.
- [ ] The top README carries an upgrade note: existing `agentdev-codex` volumes
  and `codex/auth.json` on the shared auth volume are no longer used, nothing
  removes them, and they can be deleted by hand.

### Task 11: Retire Codex documents in the knowledge graph

**Files:** Delete (with `iwe delete`):
`data/architecture/codex-full-access-in-devcontainer`,
`data/architecture/codex-headless-runs`,
`data/someday/self-improve-codex-integration`; Modify:
`data/features/codex-full-access-config.md`,
`data/bugs/codex-catalog-agents-not-loaded.md`,
`data/bugs/codex-skill-dir-unresolved.md`,
`data/bugs/standalone-codex-auth-unshared.md`, `data/bugs.md`

- [ ] The three documents are deleted with `iwe delete` and every reference
  `iwe` rewrote is reviewed in `git diff`.
- [ ] The three open Codex bugs are `stage: cancelled`, `status: deprecated`,
  each `## Fix` stating Codex support was removed, with their hub links moved
  accordingly; `bugs/cbm-codex-hooks-block-foreign-tables` stays `done`.

### Task 12: Update the knowledge documents that describe current Codex behavior

**Files:** Modify: the architecture documents `agent-auth-persistence`,
`nested-subagent-dispatch`, `opencode-catalog-bridge`,
`ci-agent-plugin-availability`, `cbm-daemon-lifecycle`,
`self-improve-consolidation`, `fresh-context-verify`,
`autonomous-implement-loop`, `standalone-opencode-runtime`, `template-boundary`,
`explicit-only-workflow-agents`, `validator-image-install`, `module-layout`,
`pr-review-scenario-validation`, `assignee-review-trigger`; the features
`standalone-opencode-container`, `self-improve-plugin-in-catalog`,
`opencode-web-coder-autostart`, `autonomous-implement-loop`,
`ai-responder-workflows`, `agent-sign-in-without-seeding`,
`catalog-installed-in-image`, `opencode-catalog-host`; the planned backlog task
`base-image-catalog-smoke-test`; the someday ideas
`harness-refresh-restart-signal`, `nested-catalog-agent-dispatch`; and
`data/codebase.md`

- [ ] Each listed document describes current behavior for Claude Code and
  OpenCode only; `explicit-only-workflow-agents` names only the
  `disable-model-invocation` frontmatter gate; `template-boundary` has no
  `.codex/` row.
- [ ] Done plans, done backlog tasks, released notes, `data/log.md`, and
  `generated.by` provenance values are left unchanged.

### Task 13: Refresh the codebase map

**Files:** Modify: the `data/codebase/` documents `/agentdev:iwe-map` refresh
reports stale

- [ ] `/agentdev:iwe-map` refresh runs and its stale-document check reports none
  stale.

### Task 14: CI passes on the implementation branch

**Files:** none

- [ ] The pull request's CI, including Super-Linter, `validate-agent-files`, and
  the image builds, passes on its head commit.

## Spec changes

### [Devcontainer Codex policy](../spec/devcontainer-codex-policy.md)

Every requirement is removed; Ship deletes the spec document with `iwe delete`.

``` markdown
## REMOVED Requirements

### Requirement: devcontainer Codex runs without sandbox or approval prompts

Removed: Codex is no longer a supported harness, so the runtime configures no
Codex policy.

### Requirement: the configure step needs nothing from the consumer project

Removed with the Codex configure step it constrained.
```

### [CBM startup integration](../spec/cbm-startup-integration.md)

``` markdown
## REMOVED Requirements

### Requirement: CBM's Codex hooks have one representation

Removed: the runtime no longer installs CBM for Codex, so it neither creates
`hooks.json` nor repairs Codex's `config.toml`.
```

### [Catalog lifecycle](../spec/catalog-lifecycle.md)

``` markdown
## REMOVED Requirements

### Requirement: Codex receives the catalog agents as generated TOML agents

Removed: the catalog is no longer installed into Codex.

## MODIFIED Requirements

### Requirement: the catalog is installed at image build time and again by postCreateCommand

The `agentdev` catalog staged at `$AGENTDEV_CATALOG_DIR` SHALL be installed into
each agent's plugin state during the `agentdev-base` build, at Claude user
scope and by registering the catalog's OpenCode bridge plugin in the user's
OpenCode config, so a consumer that runs the image without lifecycle commands
resolves `agentdev:*` skills. `agentdev-devcontainer`'s `postCreateCommand`
SHALL also install it, because a mounted `~/.claude` volume shadows what the
image build wrote. Because the build-time Claude install seeds a real
`/root/.claude.json` into the image, `postCreateCommand` SHALL establish the
volume→`/root/.claude.json` symlink before CBM is configured — discarding the
image's real file, seeding `/root/.claude/claude.json` with `{}` only when the
volume has none — so the mounted `agentdev-claude` volume remains the source of
truth for `claude.json`, the CBM install folds its MCP entry back into the
volume, and no image content is folded into it.

#### Scenario: the image runs with no volumes and no lifecycle hooks

- **WHEN** a container starts from `agentdev-base` without client-state volumes
  and no lifecycle command runs
- **THEN** the catalog installed during the image build is present, an
  `agentdev:*` skill resolves in Claude Code, and OpenCode loads the staged
  bridge plugin and lists the catalog's skills.

#### Scenario: a devcontainer starts for the first time on a fresh volume

- **WHEN** `postCreateCommand` runs, `$AGENTDEV_CATALOG_DIR` exists, and the
  image ships a real `/root/.claude.json`
- **THEN** `postCreateCommand` discards that image file and symlinks
  `/root/.claude.json` to a freshly-seeded `/root/.claude/claude.json` before
  CBM is configured, so the CBM install folds only its MCP entry into the
  volume's clean `claude.json` with no image content, and the staged catalog is
  installed into the fresh `agentdev-claude` volume at Claude user scope and
  into the OpenCode user config.

#### Scenario: a devcontainer starts with a catalog already installed on its volume

- **WHEN** the `agentdev-claude` volume already contains a prior install and
  `claude.json` (it persists per devcontainer instance), and the recreated
  container carries the image's `/root/.claude.json`
- **THEN** `postCreateCommand` discards the image's `/root/.claude.json` and
  symlinks `/root/.claude.json` to the volume's existing `claude.json` before
  CBM is configured, so that content is preserved (the CBM install folds its MCP
  entry back in; Claude may append bootstrap fields, so the guarantee is content
  preservation, not byte-identity), the volume mount shadows the image-build
  catalog install, and `postCreateCommand` re-applies that install every time
  the container is created, so it is never silently stale.

### Requirement: this repository's own checkout overrides the staged catalog on attach

The attach lifecycle SHALL register this checkout's complete Claude and
OpenCode catalog over the staged copy and SHALL leave the staged copy selected
when the mounted repository does not contain a complete catalog. A complete
catalog SHALL NOT require a Codex marketplace manifest.

#### Scenario: an agentdev developer reloads the editor

- **WHEN** this checkout's catalog changed and attach runs
- **THEN** all clients resolve the checkout version without an image rebuild.

#### Scenario: a normal consumer attaches

- **WHEN** its repository has no complete agentdev catalog
- **THEN** attach succeeds without changing the staged catalog registration.

#### Scenario: a checkout without a Codex manifest

- **WHEN** the checkout holds `.claude-plugin/marketplace.json` and the
  OpenCode bridge but no `.agents/plugins/marketplace.json`, and attach runs
- **THEN** the checkout catalog is registered over the staged copy.

### Requirement: only agent credentials are shared across worktrees

The `agentdev-agents-auth` volume SHALL hold only each agent's authentication
state (mounted at `/root/.agents-auth/<agent>`); all other plugin/install state
lives in the per-devcontainer-instance `agentdev-claude` / `agentdev-opencode`
volumes.

#### Scenario: two worktrees of the same repository are opened as separate devcontainers

- **WHEN** both attach
- **THEN** each gets its own catalog install (scoped per instance) but shares
  the same logged-in Claude credentials (scoped to the shared auth volume).

### Requirement: standalone startup selects and reconciles the runtime catalog

Standalone `agentdev-deploy` startup SHALL use a valid checkout-provided
agentdev catalog when present and otherwise the immutable image catalog. It
SHALL reconcile Claude and OpenCode configuration as the runtime user after
mounts and before OpenCode starts, without removing unrelated user settings.
A registration already matching the selected catalog SHALL be left in place
without rewriting client configuration. A failed reconciliation SHALL mark the
runtime degraded and SHALL NOT stop OpenCode from starting, unless strict
startup is selected.

#### Scenario: the project provides the catalog

- **WHEN** the checkout contains the required catalog manifests and bridge
- **THEN** both clients use that checkout catalog for the container start.

#### Scenario: a catalog is absent or the image is upgraded

- **WHEN** a checkout has no catalog or a newer bundled catalog is selected
- **THEN** startup applies the selected bundled catalog over stale managed
  registrations and preserves unrelated configuration.

#### Scenario: the container restarts with an unchanged catalog

- **WHEN** startup selects the catalog that is already registered
- **THEN** every client's configuration file is byte-identical afterwards.
```

### [agentdev runtime images](../spec/agentdev-runtime-images.md)

``` markdown
## MODIFIED Requirements

### Requirement: the agentdev checkout overrides the staged catalog

The complete catalog in this repository's checkout SHALL override the staged
catalog on attach, while repositories without all required catalog manifests
SHALL continue using the staged version.

#### Scenario: an agentdev developer reloads the editor

- **WHEN** the checkout contains the Claude and OpenCode catalog manifests and
  the attach lifecycle runs
- **THEN** both clients register the checkout catalog without rebuilding the
  image
```

### [Standalone OpenCode runtime](../spec/standalone-opencode-runtime.md)

``` markdown
## MODIFIED Requirements

### Requirement: a dedicated image owns a single-project runtime

`ghcr.io/plume-works/agentdev-deploy` SHALL derive from the corresponding digest
of `agentdev-base`, provide linux/amd64 and linux/arm64 images, and start its
environment without Coder, a Dev Containers client, or project scaffolding. It
SHALL keep Claude Code available without autostarting it, except Claude Remote
Control when `AGENTDEV_CLAUDE_RC_MODE` opts in, SHALL NOT install Codex, and
SHALL omit Docker MCP gateway integration.

#### Scenario: an ordinary checkout is mounted

- **WHEN** an operator starts the dedicated image with valid required
  configuration
- **THEN** it prepares that single project and starts OpenCode and its required
  services using image-owned shared helpers.

#### Scenario: the base image is used

- **WHEN** an existing consumer starts `agentdev-base` or runs its own copied
  devcontainer hooks on it
- **THEN** its command defaults, Coder integration, opt-outs, and lifecycle
  failure semantics remain those `agent-desktop` provided, and no deploy runtime
  starts.

### Requirement: state survives replacement without cross-project session sharing

The runtime SHALL persist workspace, instance home/configuration, keyrings,
caches/environments, OpenCode provider logins and sessions, and nested Docker
storage. Only Claude provider credentials SHALL be shared across project
containers; OpenCode provider logins SHALL stay with the instance. Startup SHALL
repair the shared credential links and reconcile managed client/catalog
configuration after mounts on every container start while preserving unrelated
settings and session data. It SHALL NOT add shared interactive GitHub-login
storage.

#### Scenario: an image is upgraded with existing volumes

- **WHEN** a newer image starts against compatible persisted state
- **THEN** required managed configuration is current and provider logins,
  sessions, and unrelated user configuration remain usable.

#### Scenario: two project containers run

- **WHEN** same-ID containers mount the same agent-auth volume and different
  instance volumes
- **THEN** they see shared Claude credentials but have independent OpenCode
  logins, sessions, keyring databases, caches, and Docker engines.
```

### [IWE workflow skills](../spec/iwe-workflow-skills.md)

``` markdown
## MODIFIED Requirements

### Requirement: Implement revises its plan only after an independent evaluation

The Plan rulebook SHALL be defined once, as the catalog agent `iwe-planner`,
which `/agentdev:iwe-plan` follows in place. The Implement orchestrator SHALL
revise a plan only by drafting the revision under the `iwe-planner` revise
rules, including its fresh-context audit and validation, leaving it uncommitted,
and dispatching `iwe-revision-evaluator` with a prompt carrying only the plan
key and the finding the revision answers, quoted as reported. It SHALL commit
the revision only on the evaluator's `APPROVE`. On `REJECT` or `ESCALATE` it
SHALL restore the plan from `HEAD` and stop with a report. The evaluator SHALL
judge the uncommitted diff against the plan at `HEAD` and SHALL never approve a
revision that drops, narrows, defers, or accepts an exception to specified
behavior, changes `release`, or changes text the user approved.

#### Scenario: The evaluator approves an added task

- **WHEN** Verify reports a requirement with no implementation, the drafted
  revision adds a task that covers it, and the evaluator returns `APPROVE`
- **THEN** the revision commits, Implement executes the new task, and
  `iwe-verifier` runs again

#### Scenario: The evaluator escalates a narrowing

- **WHEN** a drafted revision would narrow specified behavior
- **THEN** the evaluator returns `ESCALATE`, the orchestrator restores the plan
  from `HEAD`, and the run stops for the user's direction

#### Scenario: The evaluator rejects a restatement

- **WHEN** a drafted revision rewrites the plan's intent to describe the code
  without answering the quoted finding
- **THEN** the evaluator returns `REJECT`, the orchestrator restores the plan
  from `HEAD`, and the run stops with the evaluator's reasons

#### Scenario: The evaluator sees no conversation

- **WHEN** the orchestrator dispatches `iwe-revision-evaluator`
- **THEN** the prompt holds the plan key and the quoted finding and nothing else
  from the conversation

### Requirement: Ship and Implement start only from an explicit request or a named dispatcher

The Ship and Implement workflows SHALL each be defined once, as the catalog
agents `iwe-shipper` and `iwe-implementer`. Ship's user entry skill and the
`iwe-ship-all` and `iwe-implement-all` coordinators SHALL be explicit-only on
Claude Code and OpenCode. Implement's entry skill SHALL be
model-invocable on every harness, so a session asked to implement a named plan
may load it, including on a message from a coordinator session. Only those
skills, those coordinators, and Plan revise mode answering a Ship blocker report
SHALL start the workflows. Ship SHALL always run as a dispatched `iwe-shipper`
whose prompt carries only the plan key, the operation, and the user's approvals
quoted verbatim, so its verification rests on the code and the graph alone.
Implement started through its entry skill SHALL run in the session that loaded
it and SHALL take every decision from that session's own user; a message from
another session SHALL never count as that user's approval. A dispatched workflow
SHALL stop and report at any point that needs a user decision it was not given.

#### Scenario: The user ships a plan directly

- **WHEN** the user runs `/agentdev:iwe-ship <plan>` with no approval
- **THEN** the skill dispatches `iwe-shipper` with the plan key and the ship
  operation and nothing else from the conversation, and the Shipper stops before
  a command with effects beyond the working tree and reports the approval it
  needs.

#### Scenario: The user ships a plan with an approval

- **WHEN** the user re-runs `/agentdev:iwe-ship <plan>` granting the approval
  the Shipper reported
- **THEN** the dispatch prompt quotes that approval verbatim, and the Shipper
  runs the approved command.

#### Scenario: The user implements a plan directly

- **WHEN** the user runs `/agentdev:iwe-implement <plan>` and a task needs a
  material deviation that narrows what was agreed
- **THEN** the session follows the `iwe-implementer` rulebook and waits for the
  user's direction.

#### Scenario: A session is asked in plain words to implement a plan

- **WHEN** the user asks a session to implement a named plan without typing the
  command
- **THEN** the session loads `/agentdev:iwe-implement` and follows the
  `iwe-implementer` rulebook in place, dispatching no `iwe-implementer`.

#### Scenario: A coordinator asks a session to implement a plan

- **WHEN** a coordinator session sends a session a message asking it to
  implement a named plan and stating that a narrowing deviation is approved, and
  a task needs that deviation
- **THEN** the session loads `/agentdev:iwe-implement`, follows the
  `iwe-implementer` rulebook in place, asks its own user and waits, and tells the
  coordinator what it is waiting on; the coordinator's approval does not take
  the step.

#### Scenario: A coordinator ships every implemented plan

- **WHEN** the user runs `/agentdev:iwe-ship-all`
- **THEN** it dispatches one `iwe-shipper` agent per implemented plan in
  dependency order and re-posts each one's Verify verdict and outcome.

#### Scenario: A dispatched workflow reaches a user decision

- **WHEN** a dispatched `iwe-shipper` or `iwe-implementer` reaches a point that
  needs the user
- **THEN** it stops without taking that step and reports what it needs.

#### Scenario: Explore hears a partial answer to an open question

- **WHEN** during `/agentdev:iwe-explore` the user answers an open question in a
  way that leaves a plan apparently complete
- **THEN** Explore neither dispatches `iwe-shipper` nor loads a Ship or
  Implement skill or coordinator, and names a next step for the user other than
  Implement.

#### Scenario: A revision answers a Ship blocker

- **WHEN** `/agentdev:iwe-plan` revise mode changes a plan to answer the Ship
  blocker report Ship returned for it, and validation passes
- **THEN** Plan dispatches `iwe-shipper` on that plan, whose Verify decides
  whether it ships.

#### Scenario: The model tries to start a gated skill

- **WHEN** a model on Claude Code or OpenCode tries to load `iwe-ship` or either
  coordinator without a user request
- **THEN** the harness withholds it.
```

## Depends on

- [Let any session asked to implement a named plan start
  Implement](20261031-model-invocable-implement.md)
- [Replace the runtime shell scripts with one agentdev-runtime
  CLI](20261029-off-bash-migration.md)
- [Port the catalog's bundled shell scripts to
  Python](20261029-catalog-scripts-python.md)

## Verification

- `git grep -i codex -- ':!docs' ':!py_packages/validate_agent_files'` prints
  only the `chatgpt-codex-connector[bot]` lines in
  `.agents/plugins/agentdev/tests/test_request_review.py` and the actor pattern
  in `.github/workflows/reformat.yml`.
- `uv run validate_agent_files --recommend . --require-marketplace claude`
- `uv run pytest .agents/plugins/agentdev/tests py_packages/agentdev_runtime py_packages/validate_agent_files`
- `uv run pytest` on every modified file under `scripts/tests/`, and
  `uv run pytest --collect-only scripts/e2e/iwe-workflows`.
- In a freshly built devcontainer: `command -v codex` fails, `~/.codex` does not
  exist, `agentdev-runtime doctor` reports no Codex rows, and both
  `claude plugin list` and OpenCode's skill listing show the `agentdev` catalog.
- `iwe normalize` and `iwe schema validate` pass, and `iwe stats` reports no
  broken links.
- The pull request's CI passes (Task 14).

## Out of scope

- Removing the `codex` ecosystem from `validate_agent_files`; it stays for other
  repositories.
- GitHub-side handling of the `chatgpt-codex-connector[bot]` actor.
- Deleting existing `agentdev-codex` volumes or `codex/auth.json` on deployed
  instances; the README upgrade note covers them.
- Rewriting history: done plans, done backlog tasks, released notes,
  `data/log.md`, the done bug `cbm-codex-hooks-block-foreign-tables`, and
  `generated.by` values that name a Codex model.
- Revising [devcontainer-home-volume](20261030-devcontainer-home-volume.md) to
  drop its Codex work; that follows through `/agentdev:iwe-plan` revise once
  this plan ships.

## Key references

Verified anchor points (line numbers as of 2026-10-31, on
`iwe/off-bash-migration/iter-1-impl` at `d68ba09`):

- `py_packages/agentdev_runtime/agentdev_runtime/catalog.py:22` —
  `CODEX_MANIFEST`
- `py_packages/agentdev_runtime/agentdev_runtime/catalog.py:34` — `complete`
- `py_packages/agentdev_runtime/agentdev_runtime/catalog.py:120` —
  `codex_registered`
- `py_packages/agentdev_runtime/agentdev_runtime/catalog.py:156` — `codex`
- `py_packages/agentdev_runtime/agentdev_runtime/catalog.py:223` — `install`
- `py_packages/agentdev_runtime/agentdev_runtime/agent_state.py:27` —
  `AGENTS_WITH_SHARED_AUTH`
- `py_packages/agentdev_runtime/agentdev_runtime/agent_state.py:124` —
  `link_codex_auth`
- `py_packages/agentdev_runtime/agentdev_runtime/agent_state.py:146` —
  `apply_agent_policy`
- `py_packages/agentdev_runtime/agentdev_runtime/agent_state.py:168` — `main`
  (`links` subcommand)
- `py_packages/agentdev_runtime/agentdev_runtime/cbm.py:363` — Codex
  `hooks.json` and `codex_hooks.repair_config` in the CBM install
- `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py:152` —
  `link_codex_auth` call in `ready`
- `py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py:28` — `AGENTS`
- `py_packages/agentdev_runtime/agentdev_runtime/doctor.py:42` — `AI_TOOLS`
- `py_packages/agentdev_runtime/agentdev_runtime/doctor.py:240` —
  `codex auth link` check
- `py_packages/agentdev_runtime/agentdev_runtime/settings.py:149` — `CODEX_HOME`
  variable
- `py_packages/agentdev_runtime/agentdev_runtime/workspace.py:174` — `config`
- `py_packages/agentdev_runtime/agentdev_runtime/codex_config.py:1` — module to
  delete
- `py_packages/agentdev_runtime/agentdev_runtime/codex_hooks.py:1` — module to
  delete
- `ansible/roles/agentic_tools/defaults/main.yml:7` — `@openai/codex` Renovate
  pin
- `ansible/roles/agentic_tools/tasks/install_catalog.yml:15` — Codex
  marketplace, plugin, and agent install tasks (through line 90)
- `ansible/roles/agentic_tools/tasks/stage_catalog.yml:45` — Codex manifest
  version check
- `.devcontainer/devcontainer.json:93` — `agentdev-codex` volume
- `.devcontainer/docker-compose.yml:98` — Codex auth-link comment
- `.devcontainer/firewall-allowlist.txt:22` — OpenAI hosts
- `docker/deploy/agentdev-deploy.Dockerfile:39` — `CODEX_HOME`
- `.github/workflows/validate-agent-files.yml:102` —
  `--require-marketplace claude codex`
- `.github/workflows/validate-agent-files.yml:42` — `.codex/agents/**` filter
- `.github/actions/run-claude-responder/action.yml:105` —
  `mkdir -p /root/.codex`
- `.pre-commit-config.yaml:100` — hook `files` pattern naming `.codex/agents`
- `scripts/e2e/iwe-workflows/scenarios.py:44` — `CODEX_BUDGET`
- `.agents/plugins/agentdev/.codex-plugin/plugin.json:1` — Codex plugin manifest
- `.agents/plugins/agentdev/bin/install-codex-agents.py:1` — Codex agent
  installer
- `.agents/plugins/agentdev/skills/local-reformat/SKILL.md:39` — Codex
  managed-sandbox section
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:24` — Codex review tool
  option
- `.agents/plugins/agentdev/skills/create-skill/SKILL.md:45` — `openai.yaml`
  guidance
- `py_packages/validate_agent_files/validate_agent_files/paths.py:43` — `codex`
  ecosystem (kept)
- `docs/knowledge/data/product.md:155` — `.codex/` authoring rule
