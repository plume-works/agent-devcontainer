---
type: plan
created: 2026-10-21
release:
- features/opencode-catalog-host
description: Preserve the namespaced slash-command name in OpenCode v2 user messages so bare commands and commands with arguments remain visible in chat.
generated:
  by: opencode/gpt-6.1-sol
  at: 2026-10-21T17:45:25Z
sources:
- resource: .agents/plugins/agentdev/.opencode-plugin/index.ts
- resource: .agents/plugins/agentdev/tests/opencode/bridge.test.ts
- resource: docs/knowledge/data/spec/opencode-catalog-bridge.md
- resource: docs/knowledge/data/architecture/opencode-catalog-bridge.md
- resource: https://github.com/anomalyco/opencode/blob/v2.1.1/packages/app/src/composer/client-slash-command.ts
- resource: https://github.com/anomalyco/opencode/blob/v2.1.1/packages/app/src/composer/submit.ts
stage: done
completed: 2026-10-21
---

# Show the full OpenCode slash-command invocation

## Context

[OpenCode as a catalog host](../features/opencode-catalog-host.md) registers
`/agentdev:<skill>` commands. This plan changes their v2 presentation contract
so the submitted user message retains the full namespaced invocation, including
bare commands.

The user wants the submitted command and accompanying text visible together,
without expanding the skill instructions into chat. The current [bridge
spec](../spec/opencode-catalog-bridge.md) describes an arguments-only message;
this plan changes that presentation contract. The [v2
migration](20261018-opencode-v2-default.md) is already shipped; no active plan
covers this change.

## Approach

In the bridge's v2 command executor, prefix the submitted text with the
registered slash-command name. Empty arguments produce just the command;
nonempty arguments follow one separating space, with the supplied argument text
otherwise preserved. Retain the structured skill reference and the single
`session.prompt` submission. Attachment mentions must still identify their
intended text after the prefix is inserted.

Do not add an assistant acknowledgment or a second synthetic message: the user's
invocation belongs in the user message. Do not paste the skill body back into
chat. OpenCode v1 remains unchanged. The bridge can reconstruct the command and
supplied arguments, not whitespace the host has already removed.

## Implementation Steps

### Task 1: Pin complete invocation payloads

**Files:** Modify: `.agents/plugins/agentdev/tests/opencode/bridge.test.ts`

- [x] Update the v2 command test to require the slash-command name before its
  argument text. Add cases whose submitted text is exactly:

  ``` text
  /agentdev:iwe-implement fix critical
  ```

  ``` text
  /agentdev:iwe-ship
  ```

  Assert one prompt per invocation, no trailing separator for empty arguments,
  the skill still attached, no skill body pasted into text, and unchanged
  session ID and delivery mode. Cover both `steer` and `queue`, existing
  attachments and skill references, multiline argument text, and attachment
  mentions remaining aligned with their intended text. Confirm the new text
  assertions fail against the arguments-only executor.

  - **Evidence:** The targeted Bun test for `complete invocation` fails against
    the argument-only executor on both command text and mention offsets.

### Task 2: Preserve the command in the submitted message

**Files:** Modify: `.agents/plugins/agentdev/.opencode-plugin/index.ts`

- [x] Build the v2 prompt text from the registered command name and arguments
  under the rule in Approach, keeping one submission, the selected skill,
  existing attachments, and delivery semantics intact. Rebase text-span mention
  offsets where the prefix moves their referenced text; do not mutate the
  incoming invocation. Make Task 1's tests pass and keep the v1 bridge tests
  passing without changing v1 templates or command registration.
  - **Evidence:**
    `bun test ./.agents/plugins/agentdev/tests/opencode/bridge.test.ts` passes
    all 29 v1 and v2 bridge tests.

### Task 3: Reconcile guidance and map provenance

**Files:** Modify: `docs/knowledge/data/features/opencode-catalog-host.md`,
`docs/knowledge/data/architecture/opencode-catalog-bridge.md`,
`docs/knowledge/data/codebase/agents/plugins/agentdev.md`,
`docs/knowledge/data/codebase/agents/plugins/agentdev/opencode-plugin.md`,
`docs/knowledge/data/codebase/agents/plugins/agentdev/tests.md`

- [x] Describe the full command plus arguments instead of arguments-only v2
  messages in the feature and architecture documents. Refresh the affected
  codebase-map sections, verified anchors, and source digests. Run the complete
  bridge test file, catalog validation, map freshness check, normalization, and
  schema validation from Verification. Leave the durable spec merge to Ship.
  - **Evidence:** The complete bridge suite passes 29/29 tests, catalog
    validation passes 62/62 skills, the map reports 28/28 documents fresh, and
    `iwe normalize` plus `iwe schema validate` pass.

### Task 4: Verify the visible Web UI result

**Files:** Modify: `docs/knowledge/data/plans/20261021-opencode-command-echo.md`

- [x] A user or browser-capable verifier runs the Web UI check from Verification
  against the changed, reloaded bridge and records evidence that both bare and
  argument-bearing invocations have one persistent user bubble. This task stays
  unchecked until the UI result is observed; payload tests alone cannot close
  it.
  - **Evidence:** The OpenCode v2.1.1 Web UI result is recorded under
    Verification results.

## Spec changes

[OpenCode catalog bridge](../spec/opencode-catalog-bridge.md) — replace the
complete namespaced-command requirement with this delta, preserving v1 and
autocomplete behavior:

``` markdown
## MODIFIED Requirements

### Requirement: every skill is a namespaced slash command

The bridge plugin SHALL register a command `agentdev:<name>` for each catalog
skill, described by the skill's frontmatter description. On OpenCode v1 its
template SHALL be the skill body followed by the skill's base directory and the
statement that relative paths resolve against it. On OpenCode v2 running it
SHALL submit one user message whose text is `/agentdev:<name>` followed, when
arguments are nonempty, by one space and the supplied argument text. The skill
SHALL remain attached as a skill reference rather than pasted into the text.
Existing attachments and their text references, session ID, and delivery mode
SHALL be preserved. The Web UI SHALL show the invocation as a user message,
including when there are no arguments, and retain it after reload.

#### Scenario: the user types a namespaced command on v1

- **WHEN** the user types `/agentdev:pr-gen-description` in OpenCode v1
- **THEN** OpenCode sends the `pr-gen-description` skill body with its base
  directory, and a relative `agent-code/` step resolves inside that skill.

#### Scenario: the user types a namespaced command on v2

- **WHEN** the user types `/agentdev:pr-gen-description for the current branch`
  in OpenCode v2
- **THEN** the chat shows the message
  `/agentdev:pr-gen-description for the current branch` with the
  `pr-gen-description` skill attached, and the model receives the skill body
  with its base directory.

#### Scenario: the user types a command without arguments on v2

- **WHEN** the user types `/agentdev:iwe-ship` without arguments in OpenCode v2
- **THEN** the chat shows one user message containing `/agentdev:iwe-ship`,
  without a trailing space, with the `iwe-ship` skill attached
- **AND** the message remains visible after reloading the Web UI.

#### Scenario: an invocation carries attachments or queued delivery on v2

- **WHEN** a namespaced command has existing file, agent, or skill attachments,
  or requests queued delivery
- **THEN** adding the command name preserves those attachments and the text
  spans they refer to, the session ID, and the requested delivery mode
- **AND** the bridge submits only one user prompt.

#### Scenario: the user types a command prefix

- **WHEN** the user types `/pr` in the OpenCode TUI
- **THEN** the autocomplete offers `agentdev:pr-*` commands.
```

## Verification

- Red/green payload tests, then the complete v1/v2 bridge suite:
  `bun test ./.agents/plugins/agentdev/tests/opencode/bridge.test.ts`.
- Catalog:
  `uv run validate_agent_files --recommend . --require-marketplace claude codex`.
- Map: `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py`.
- Knowledge graph: `iwe normalize`, then `iwe schema validate`.
- Web UI: reload the changed bridge through a fresh OpenCode server/plugin
  instance, then use `/agentdev:iwe-explore` and
  `/agentdev:iwe-explore explain this repository; do not modify files` in a
  disposable session. Observe exactly one user bubble per invocation containing
  its command name and any supplied arguments, not the skill body. Reload the
  page and confirm both bubbles persist. Record the host version and durable
  evidence in Verification results; use the repository's default test models
  when model execution is required. Do not invoke shipping or implementation
  skills merely to test display behavior.

## Verification results

OpenCode v2.1.1 with Chromium 140 and `openai/gpt-6.1-sol` displayed exactly one
persistent user bubble for `/agentdev:iwe-explore` and exactly one for
`/agentdev:iwe-explore explain this repository; do not modify files`. Both
bubbles retained the full invocation after a page reload, and neither displayed
the skill body.

## Out of scope

- Changing OpenCode upstream, its Web UI, or its v1 command behavior.
- Reconstructing original spacing already stripped by OpenCode's command parser.
- Adding duplicate assistant echoes or pasting skill bodies into user messages.
- Rewriting existing session history or changing skill execution semantics.
- Releasing the catalog or updating image pins.

## Key references

Verified anchor points (line numbers as of 2026-10-21):

- `.agents/plugins/agentdev/.opencode-plugin/index.ts:132` — `rebaseMentions`
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:277` — v2 command
  registration
- `.agents/plugins/agentdev/.opencode-plugin/index.ts:283` — executor building
  the full invocation text
- `.agents/plugins/agentdev/tests/opencode/bridge.test.ts:200` — `fakeV2`
  context
- `.agents/plugins/agentdev/tests/opencode/bridge.test.ts:277` — v2 command
  payload test
- `docs/knowledge/data/spec/opencode-catalog-bridge.md:56` — namespaced-command
  requirement
- `docs/knowledge/data/architecture/opencode-catalog-bridge.md:66` — v2 command
  design
- `docs/knowledge/data/features/opencode-catalog-host.md:33` — catalog command
  behavior
