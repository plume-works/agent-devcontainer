---
type: plan
created: 2026-10-02
description: Make pr-feedback-resolution resolve a pull request's merge conflicts through update-branch before collecting feedback, and route a conflicted PR in pr-merge's monitoring loop to it.
generated:
  by: claude-code/opus-5-5
  at: 2026-10-02T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/update-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md
---

# Resolve merge conflicts in pr-feedback-resolution

## Context

[Resolve merge conflicts in pr-feedback-resolution](../backlog/pr-feedback-resolve-merge-conflicts.md)
records the gap: `pr-feedback-resolution` collects review threads, review
bodies, CI, CodeQL, and Codecov, but never reads the pull request's merge state.
A PR that conflicts with its base gets no `pull_request` workflow runs, so the
CI picture the skill diagnoses is missing or stale until the conflict is
resolved. `pr-merge` names a conflict as a merge blocker but routes only failing
checks to `pr-feedback-resolution`, so a conflicted PR has no remediation path
there either.

## Approach

Conflict resolution becomes the first step of `pr-feedback-resolution`'s
Workflow 1, before any feedback edit:

- Read `gh pr view <pr> --json mergeable,mergeStateStatus,baseRefName`.
- `mergeable: CONFLICTING` or `mergeStateStatus: DIRTY` → invoke
  `/agentdev:update-branch --base <baseRefName>` and follow its
  `git-merge-resolve` handoff and its Workflow 3 push, so CI starts on the
  merged head before feedback work begins.
- `mergeable: UNKNOWN` → GitHub has not computed mergeability yet; re-poll in
  bounded waits before deciding.
- Anything else → continue collecting feedback.

Running first keeps the working tree clean, which `update-branch` requires, and
lets the remaining workflows read CI results for the merged head. Using the PR's
`baseRefName` rather than `update-branch`'s `main` default keeps stacked PRs
merging their real base; `update-branch` comes to name a calling skill as a
legitimate source of `--remote` and `--base`, so that override is not read as
unrequested. Whether the merge needs a fresh AI review is already decided by
`pr-eval-review-needed`; this plan adds nothing there.

`pr-merge`'s monitoring loop gains a merge-state branch after its refresh step,
which comes to read `mergeable` as well: a `CONFLICTING` or `DIRTY` PR goes to
`pr-feedback-resolution`'s conflict step, then the loop restarts at the refresh,
because the checks it would otherwise wait on never run. An `UNKNOWN`
mergeability is re-polled from the refresh before the loop waits on checks.

Rejected: pushing the merge together with the feedback fixes. It saves one CI
cycle but leaves CI blind while the feedback is worked, which is the problem
this plan fixes.

## Implementation Steps

### Task 1: Add the merge-conflict step to pr-feedback-resolution

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md`

- [x] Workflow 1 opens with the merge-state step described in `## Approach`: the
  `gh pr view` fields, the `CONFLICTING`/`DIRTY` route to
  `/agentdev:update-branch --base <baseRefName>` with its push, the `UNKNOWN`
  re-poll, and the instruction that it runs before any feedback edit.
  - **Evidence:** commit "feat(pr-feedback-resolution): resolve merge conflicts
    before collecting feedback" — "Resolve merge conflicts first" block in
    Workflow 1.
- [x] Workflow 7's completion checklist and `## Success Criteria` each gain an
  item that the PR has no merge conflicts with its base.
  - **Evidence:** same commit — "No merge conflicts with the PR's base branch"
    heads both lists.
- [x] `## Related Resources` links `update-branch`'s `SKILL.md`.
  - **Evidence:** same commit — "Update Branch" entry in Related Resources.
- [x] `uv run validate_agent_files` passes on the edited `SKILL.md`.
  - **Evidence:** same commit; its pre-commit `validate-agent-files` hook
    passed.

### Task 2: Route a conflicted PR in pr-merge's monitoring loop

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-merge/SKILL.md`

- [x] The `## Monitoring Loop` gains a step between the refresh (step 1) and the
  pending-check wait (step 2): when `mergeStateStatus` is `DIRTY`, follow
  `pr-feedback-resolution`'s merge-conflict step, then restart at step 1.
  - **Evidence:** commit "feat(pr-merge): route a conflicted PR to the
    merge-conflict step" — new step 2 of the Monitoring Loop; later steps
    renumbered 3–7.
- [x] `uv run validate_agent_files` passes on the edited `SKILL.md`.
  - **Evidence:** same commit; its pre-commit `validate-agent-files` hook
    passed.

### Task 3: Let update-branch accept a calling skill's base

**Files:** Modify: `.agents/plugins/agentdev/skills/update-branch/SKILL.md`

- [x] Workflow 1 says to supply `--remote` or `--base` only when the user or the
  calling skill supplies different values.
  - **Evidence:** commit "docs(update-branch): accept a calling skill's --remote
    and --base".
- [x] `uv run validate_agent_files` passes on the edited `SKILL.md`.
  - **Evidence:** same commit; its pre-commit `validate-agent-files` hook
    passed.

### Task 4: Handle an uncomputed merge state in pr-merge

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-merge/SKILL.md`

- [x] The Monitoring Loop's refresh reads `mergeable`; step 2 routes
  `mergeable: CONFLICTING` as well as `mergeStateStatus: DIRTY` to the conflict
  step, and on `mergeable: UNKNOWN` restarts at step 1 after a bounded wait
  instead of waiting on checks.
  - **Evidence:** commit "feat(pr-merge): re-poll an uncomputed merge state" —
    refresh field list and step 2 of the Monitoring Loop.
- [x] `uv run validate_agent_files` passes on the edited `SKILL.md`.
  - **Evidence:** same commit; its pre-commit `validate-agent-files` hook
    passed.

## Spec changes

None — no `data/spec/` document covers the pr-* skills; the behavior this plan
changes is defined by the skill instructions it edits.

## Verification

- `uv run validate_agent_files` on the `pr-feedback-resolution`, `pr-merge`, and
  `update-branch` `SKILL.md` files exits 0.
- `pre-commit run --files` on the three files passes.
- Read the skills end to end: the conflict step in `pr-feedback-resolution`
  precedes every feedback edit, passes `--base <baseRefName>`, and pushes after
  the merge; `pr-merge`'s loop sends `CONFLICTING`/`DIRTY` there and re-polls
  `UNKNOWN` before it waits on checks; `update-branch` accepts a calling skill's
  `--base`.

## Out of scope

- `mergeStateStatus: BEHIND` — a branch behind its base without conflicts does
  not trigger an update.
- Fork PRs whose base branch lives on a remote other than `origin`; the conflict
  step uses `update-branch`'s `origin` default.
- Changes to `update-branch` beyond its flag guidance, and to
  `git-merge-resolve` or `pr-eval-review-needed`.

## Key references

Verified anchor points (line numbers as of 2026-10-02):

- `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md:51` —
  Workflow 1: Collect All Feedback Sources
- `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md:55` — Resolve
  merge conflicts first
- `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md:76` — step 1,
  Fetch PR review comments
- `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md:320` —
  Workflow 7 completion checklist
- `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md:521` —
  Success Criteria
- `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md:534` —
  Related Resources
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:129` — Monitoring Loop
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:139` — refresh step reading
  `mergeStateStatus`
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:143` — conflict and UNKNOWN
  routing step
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:165` — check classification
  routing to pr-feedback-resolution
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:56` — Workflow 1: Run
  the Update Script
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:62` — guidance on
  supplying `--remote` and `--base`
- `.agents/plugins/agentdev/skills/update-branch/SKILL.md:77` — Workflow 3: Push
  the Updated Branch
- `.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md:56` — base
  merge with a judgment call needs re-review
