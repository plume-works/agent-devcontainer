---
type: plan
created: 2026-09-29
description: Keep the agentdev plugin enabled when the Claude responder hands its settings to claude-code-action, and make pr-review collect its parallel passes with foreground Agent calls, leaving the job timeout as the only ceiling.
generated:
  by: claude-code/opus-5.5
  at: 2026-09-29T00:00:00Z
sources:
- resource: https://github.com/plume-works/agent-devcontainer/issues/198
  title: Claude responder reviews fail silently
- resource: .github/actions/run-claude-responder/action.yml
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .devcontainer/scripts/reinstall-agentdev-claude.sh
---

# Keep agentdev enabled in the responder and collect review passes in the foreground

## Context

[Issue #198](https://github.com/plume-works/agent-devcontainer/issues/198)
reports two independent ways a Claude responder review ends green with no
`agentdev:pr-review` review published.

**The plugin is disabled before the session starts.** The lifecycle hooks
install `agentdev@agent-devcontainer` at user scope, in
`$HOME/.claude/settings.json`. The `Merge Claude settings` step then hands
`.claude/settings.json` (deep-merged with `settings.local.json` when present) to
`anthropics/claude-code-action@v1` as its `settings:` input, and the action
merges that input into the user settings **one level deep**. The project file's
`enabledPlugins` object replaces the hook-written one, so the plugin stays
installed but disabled and `Skill agentdev:pr-review` is unknown.

This repository is not affected: `reinstall-agentdev-claude.sh` also installs at
local scope where a marketplace is published, which puts
`agentdev@agent-devcontainer` into `settings.local.json` and so into the object
that does the replacing. A consumer repository has no marketplace, no local
layer, and loses the plugin.

**The passes are never collected.** `pr-review` starts its Step 4 passes and
Step 6 validators as background `Agent` subagents and tells Claude Code to block
on them with `TaskOutput`, which the responder's Claude Code does not provide. A
headless `claude -p` run ends with its turn, so the review is abandoned — the
failure recorded in
[The review orchestrator ends its turn while its passes are still running](../bugs/review-orchestrator-ends-turn-while-passes-run.md).

## Approach

**Settings:** hand the action a settings object that already contains the
hook-written user layer. The merge step deep-merges, in order, the user settings
the hooks wrote (when present), `.claude/settings.json`, and
`.claude/settings.local.json` (when present), with jq's recursive `*`. The
action's one-level replacement then writes back an `enabledPlugins` that still
names every plugin the hooks enabled. Project and local layers keep precedence
over the user layer, matching Claude Code's own scope order.

**Passes:** the skill tells Claude Code to dispatch every pass of a batch as
foreground `Agent` calls (`run_in_background: false`) in a single message, which
runs them in parallel and returns only when all have finished. Where the `Agent`
tool offers no foreground option, the passes run sequentially in the session.
Nothing in the Claude Code path depends on a separate wait tool.

**Timeout:** foreground calls cannot be cancelled individually, so the Claude
Code path has no per-pass ceiling and no drop-a-hung-pass fallback. The
`claude-respond` job's `timeout-minutes` bounds the whole review; a review that
exceeds it fails the job, and `ai-review-present` fails with it. The Codex path
keeps its ceilings and hard fallback unchanged.

**Rejected:**

- *Run every pass sequentially in the session* — the Codex branch's shape. It
  works everywhere but gives up parallelism and each pass's clean context, which
  foreground `Agent` calls keep.
- *Keep background dispatch and wait through another primitive* — no wait tool
  is available in the responder's Claude Code, and binding the skill to one that
  a version bump can remove is the failure being fixed.
- *Skip the `settings:` input and rely on the hook-written user settings* —
  loses the project's permissions and model pin, which only reach the session
  through that input.

## Implementation Steps

### Task 1: Layer the hook-written user settings under the project settings

**Files:** Modify: `.github/actions/run-claude-responder/action.yml`

- [x] Rewrite the `Merge Claude settings` step to deep-merge
  `$HOME/.claude/settings.json` (when present), `.claude/settings.json`, and
  `.claude/settings.local.json` (when present), in that order, with
  `jq -cs 'reduce .[] as $layer ({}; . * $layer)'`, and write the result to
  `$GITHUB_OUTPUT` as today.
  - **Evidence:** the Task 1 commit; the step's extracted script passes
    `shellcheck`, and run against a user layer enabling
    `agentdev@agent-devcontainer` plus a project layer enabling another plugin
    it emits both under `enabledPlugins`; pre-commit (prettier, zizmor) passes.
- [x] Replace the step's comment so it states why the user layer is included —
  the action merges its `settings:` input one level deep — in no more than three
  lines.
  - **Evidence:** the Task 1 commit; the three-line comment above
    `Merge Claude settings` in
    `.github/actions/run-claude-responder/action.yml`.

### Task 2: Prove the merge keeps agentdev enabled without a local layer

**Files:** none (local check in the job image)

- [ ] In the `agent-desktop` image with `HOME=/github/home`, run the three
  lifecycle hooks against a checkout with no `.claude-plugin/marketplace.json`
  and no `.claude/settings.local.json`, apply the new merge, then apply a
  one-level merge of its output onto `$HOME/.claude/settings.json`;
  `claude plugin list` reports `agentdev@agent-devcontainer` enabled. The same
  procedure with the current merge reports it disabled.

### Task 3: Dispatch Claude Code passes as foreground Agent calls

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [ ] Rewrite Step 4's Claude Code bullet: issue every pass's `Agent` call in a
  single message with `run_in_background: false`
  (`subagent_type: general-purpose`, the slot's `model`); if the `Agent` tool
  has no foreground option, run the passes sequentially in the session.
- [ ] Update Step 4's blocking bullet and Step 6's runner reference so both
  point at the foreground dispatch for Claude Code, and drop the Claude Code
  "hard-times-out" and per-validator ceiling wording.
- [ ] In `Waiting on Parallel Passes`, replace the `TaskOutput` bullet with the
  foreground dispatch rule, and scope the budget and hard-fallback bullets to
  Codex. State that on Claude Code the job timeout bounds the review.
- [ ] No reference to `TaskOutput` remains in the catalog:
  `grep -rn TaskOutput .agents/` prints nothing.

### Task 4: Record the settings layering as a CI constraint

**Files:** Modify:
`docs/knowledge/data/architecture/ci-agent-plugin-availability.md`

- [ ] Under `## What a container: job must supply itself`, add that the settings
  handed to `claude-code-action` must include the hook-written user layer,
  because the action's one-level merge otherwise replaces the `enabledPlugins`
  the hooks wrote.

### Task 5: A responder review on this repository collects its passes in the foreground

**Files:** none (CI evidence)

- [ ] The responder review of the pull request carrying Tasks 1–4 publishes an
  `agentdev:pr-review` review, and its execution artifact shows every `Agent`
  call with `run_in_background: false`.

### Task 6: A consumer repository's responder resolves agentdev:pr-review

**Files:** none (CI evidence)

- [ ] A responder review in a consumer repository running the updated action
  (for example Dr-QP/Dr.QP) invokes `Skill agentdev:pr-review` without
  `Unknown skill` and publishes a review.

## Spec changes

None — no behavioral change to a spec. No `data/spec/` document governs the
responder's settings merge or how `pr-review` waits on its passes;
[AI review gate](../spec/ai-review-gate.md) is unchanged, including its
acceptance of an earlier review. The settings-layering constraint is recorded in
the architecture document by Task 4.

## Verification

- Task 2's procedure, run in the pinned `agent-desktop` image through
  `/agentdev:microvm-sandbox`.
- `grep -rn TaskOutput .agents/` prints nothing.
- `actionlint` and the pre-commit hooks pass on
  `.github/actions/run-claude-responder/action.yml`.
- `pre-commit run validate-agent-files` passes on the edited `SKILL.md`.
- Task 5's responder run: a review is published and the execution artifact's
  `Agent` inputs all carry `run_in_background: false`.
- Task 6's consumer run.

## Out of scope

- Failing a responder run that published no review. The bug document records why
  the time-window check was removed and what an identity-based check would need;
  that stays with
  [the bug](../bugs/review-orchestrator-ends-turn-while-passes-run.md).
- Changing `ai-review-present`'s acceptance of an earlier review.
- Per-pass timeouts on the Claude Code path; the job timeout is the ceiling.
- The Codex dispatch, budget, and hard fallback wording.

## Key references

Verified anchor points (line numbers as of 2026-09-29):

- `.github/actions/run-claude-responder/action.yml:95` —
  `Run devcontainer lifecycle scripts`, which writes the user-scope settings
- `.github/actions/run-claude-responder/action.yml:112` —
  `Merge Claude settings`, the two-layer merge at line 117
- `.github/actions/run-claude-responder/action.yml:144` — `Claude Responder`,
  with the `settings:` input at line 151
- `.devcontainer/scripts/reinstall-agentdev-claude.sh:15` — local scope by
  default; the marketplace guard at line 20
- `.devcontainer/scripts/postCreateCommand.sh:91` — the user-scope install
- `.claude/settings.json:49` — the project `enabledPlugins` block
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:133` — Step 4's Claude
  Code dispatch bullet; blocking bullet at line 134
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:143` — Step 6's runner and
  ceiling reference
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:156` —
  `Waiting on Parallel Passes`; `TaskOutput` at line 177, budget at 178, hard
  fallback at 179
- `.github/workflows/ai-responder.yml:437` — `claude-respond`
  `timeout-minutes: 30`
