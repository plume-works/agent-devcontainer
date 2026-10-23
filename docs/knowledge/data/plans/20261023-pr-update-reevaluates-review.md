---
type: plan
created: 2026-10-23
release:
- bugs/pr-update-skips-review-eval
description: Make every push to a reviewed pull request through pr-open's update mode or pr-merge's CI-fix step run the re-review evaluation, restate that evaluation so it works from the pull request alone, and enforce one AI review trigger per head SHA with a bundled script.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-23T15:30:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-sync/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-discover-ai-responder/agent-code/discover-ai-responder.sh
- resource: docs/knowledge/data/spec/ai-review-gate.md
---

# PR updates re-evaluate the AI review

## Context

Fixes [Bug: PR updates skip the re-review
evaluation](../bugs/pr-update-skips-review-eval.md). The [AI review
gate](../spec/ai-review-gate.md) passes on any accepted review across later
pushes and leaves refreshing it to the author; `pr-eval-review-needed` is the
skill that makes that call. Only `pr-feedback-resolution` invokes it, so
`pr-sync` — which keeps a pull request's title and body in step with what the
branch changes, and handles no feedback — and `pr-merge`'s CI-fix pushes update
reviewed pull requests without ever asking. The once-per-head-SHA trigger rule
is prose held in conversation memory, so separate sessions double-trigger.

## Approach

Three changes, each owned by one skill:

1. **Callers.** `pr-open` gains step 10, run on every update-mode run regardless
   of what the push or the body edit changed: apply `pr-eval-review-needed`.
   `pr-sync` inherits it unchanged. `pr-merge` step 5 applies the eval after a
   CI-fix push, before restarting its loop. `pr-feedback-resolution` already
   calls the eval and pushes through `push-branch.sh` rather than the `pr-open`
   skill, so it never evaluates twice.
2. **The test.** `pr-eval-review-needed` stops asking "did I change anything the
   reviewer did not direct?" and asks whether the diff since the newest reviewed
   commit goes beyond what the pull request's review threads and review comments
   since that review asked for. The evidence is read from the pull request, so a
   cold run from `pr-sync` or `pr-merge` decides on the same footing as a
   feedback pass. The request/decline lists are unchanged.
3. **One trigger per head.** A new
   `pr-request-ai-review/agent-code/request-review.sh` is the only path that
   posts an AI review trigger, used by `pr-request-ai-review` and by
   `pr-merge`'s AI Review Recovery, whose in-conversation ledger it replaces.
   The unit is the commit, not the poster: a comment whose body opens
   `@claude review` (case folded, as the responder's preflight matches it) is a
   trigger whether a skill or a person posted it. A trigger the script posts
   names the commit it requests and counts for that commit only; a hand-typed
   one counts for the head only when it provably postdates the head's arrival.
   Before posting, the script reads the pull request's head, its reviews, and
   its issue comments, and refuses when an accepted AI review already names the
   head or a trigger for the head exists.

`request-review.sh` takes `--pr <number>` (required), `--rationale <one line>`
(optional; a newline in it is a `PREFLIGHT_ERROR`), and `--repo <owner/repo>`
(optional). The head's arrival time is the earliest `created_at` among the head
commit's check suites (`repos/{owner}/{repo}/commits/<sha>/check-suites`), which
each app with checks on push or pull-request events opens within seconds of the
push. A posted trigger's body is `@claude review`, then the rationale line when
given, then `<!-- review-head: <sha> -->`; a comment carrying that marker counts
for the SHA it names and no other, whatever its date. An unmarked trigger counts
for the head only when created after the head's arrival; a head with no check
suite has no arrival time, so no unmarked trigger counts for it. Doubt resolves
toward posting: a duplicate trigger costs one redundant review, a wrongly
counted one leaves the head unreviewed. Accepted reviewers are the ones
[spec/ai-review-gate](../spec/ai-review-gate.md) names — `claude[bot]`,
`github-actions[bot]`, `chatgpt-codex-connector[bot]` — in state `APPROVED`,
`CHANGES_REQUESTED`, or `COMMENTED`. The spec's `+1` reaction from
`chatgpt-codex-connector[bot]` is not counted: a reaction names no commit, so it
cannot show that the head was reviewed. Output keys: `PR_NUMBER`, `HEAD_SHA`,
`COMMENT_URL` (the posted or the existing trigger; empty for
`ALREADY_REVIEWED`), and the `RESULT=` line:

| RESULT              | Exit | When                                                               |
| ------------------- | ---- | ------------------------------------------------------------------ |
| `SUCCESS`           | `0`  | Trigger posted for the head                                        |
| `ALREADY_REVIEWED`  | `3`  | An accepted AI review's commit is the head                         |
| `ALREADY_REQUESTED` | `4`  | A trigger names the head, or an unmarked one postdates its arrival |
| `PR_NOT_OPEN`       | `5`  | The pull request is closed, merged, or not found                   |
| `GH_UNAVAILABLE`    | `6`  | `gh` is missing, unauthenticated, or its API call failed           |
| `PREFLIGHT_ERROR`   | `2`  | Missing `--pr`, unknown argument, multi-line rationale             |
| `SCRIPT_FAILURE`    | `1`  | Unhandled error                                                    |

The maintainer decided that a hand-typed trigger counts like any other: two
review requests on one commit are never useful. One that no check suite dates
after the head is not counted, because it may belong to the previous head.
Assumption recorded here, not decided by the maintainer: the script does not
inspect responder runs — attributing a comment-triggered run to a pull request
needs its log (`pr-discover-ai-responder`); the trigger comment that started a
run already counts, and `pr-merge`'s wait on an in-progress run stays prose.

Rejected: dating the head by its commit date, alone or as a fallback — commit
dates survive rebase and amend, and an old commit pushed late would inherit the
previous head's trigger; matching a marked trigger by date instead of by its
marker — a trigger posted before the head's first check suite would be missed;
reading the issue timeline to date the head — its `committed` event carries no
timestamp; hooking the eval into `pr-sync` alone — `pr-open` reached directly in
update mode would stay uncovered; gating step 10 on whether the push moved the
head — a head pushed earlier by another path would be skipped unevaluated.

## Implementation Steps

### Task 1: Trigger script

**Files:** Create:
`.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.sh`,
`.agents/plugins/agentdev/tests/test_request_review.py`

- [ ] Tests, written first with a stub `gh` on a hermetic `PATH` in the style of
  `test_discover_ai_responder.py`, fail before the script exists and cover: no
  review and no trigger posts one whose body opens `@claude review`, carries the
  rationale line, and prints `COMMENT_URL` (`SUCCESS`); an accepted review on
  the head posts nothing (`ALREADY_REVIEWED`); an accepted review on an older
  commit still posts; a review by an unaccepted author on the head still posts;
  the posted body ends with the head's `review-head` marker; a marked trigger
  for the head posts nothing and prints its URL (`ALREADY_REQUESTED`), even when
  created before the head's earliest check suite; a marked trigger for another
  commit still posts, even when created after it; a hand-typed trigger created
  after the head's earliest check suite, in any letter case, posts nothing
  (`ALREADY_REQUESTED`); one created before it still posts; a hand-typed trigger
  on a head with no check suite still posts; a comment that mentions
  `@claude review` mid-body is not a trigger; a closed pull request
  (`PR_NOT_OPEN`); a failing `gh` call (`GH_UNAVAILABLE`); missing `--pr` and a
  multi-line rationale (`PREFLIGHT_ERROR`); `RESULT=` is the last stdout line on
  every path
- [ ] `request-review.sh` implements the Approach's arguments, checks, head
  dating, output keys, and result table per `/agentdev:skill-scripts`, sourcing
  `bin/result-codes.sh`; `--help` lists options, keys, and results;
  `shellcheck -x` is clean; the new tests pass

### Task 2: pr-request-ai-review posts through the script

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md`

- [ ] `## Post the request` runs
  `agent-code/request-review.sh --pr <pr> --rationale '<one line>'` instead of
  `gh pr comment`, with a table mapping each `RESULT` to its action
  (`ALREADY_REVIEWED` and `ALREADY_REQUESTED` are reported, not retried;
  `GH_UNAVAILABLE`, `PR_NOT_OPEN`, `PREFLIGHT_ERROR`, `SCRIPT_FAILURE` stop);
  `## Post at most once per head SHA` states that the script enforces the rule
  for every trigger on the head, hand-typed ones included when a check suite
  dates them after the head, and that no skill posts a trigger any other way;
  the frontmatter gains `allowed-tools: Bash(${CLAUDE_SKILL_DIR}/agent-code/*)`
  as `pr-open` has it

### Task 3: The eval reads intent from the pull request

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md`

- [ ] `## The test` asks whether the diff since the newest reviewed commit goes
  beyond what the pull request's review threads and review comments since that
  review asked for, replacing the first-person question; the request/decline
  lists in `## What counts as beyond the feedback` keep their items
- [ ] `## Establish what the last review saw` adds the command that reads the
  review threads and comments posted since the newest reviewed commit, and says
  that a run with no such threads judges the whole diff as undirected
- [ ] The frontmatter `description` and the opening paragraph name `pr-open`'s
  update mode and `pr-merge`'s CI-fix push as callers alongside feedback
  resolution

### Task 4: pr-open evaluates on every update

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-open/SKILL.md`

- [ ] A new `### 10. Re-Review Evaluation` follows step 9: in update mode,
  always apply [pr-eval-review-needed](../pr-eval-review-needed/SKILL.md) with
  `PR_NUMBER`, and add its decision to the step 9 report; create mode skips it.
  `### 10. Error Handling` becomes `### 11. Error Handling`

### Task 5: pr-merge evaluates CI-fix pushes and posts through the script

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-merge/SKILL.md`

- [ ] Step 5 applies [pr-eval-review-needed](../pr-eval-review-needed/SKILL.md)
  after the push and before restarting the loop
- [ ] `## AI Review Recovery` step 2 drops the in-conversation per-head-SHA
  ledger, and step 3 runs `request-review.sh` from
  [pr-request-ai-review](../pr-request-ai-review/SKILL.md) instead of
  `gh pr comment`, handling `ALREADY_REQUESTED` by finding and waiting on that
  trigger's run

### Task 6: Codebase map

**Files:** Modify:
`docs/knowledge/data/codebase/agents/plugins/agentdev/skills.md` and any other
doc `stale-map-docs.py` reports

- [ ] `/agentdev:iwe-map` refresh mode re-reads the stale docs —
  `pr-request-ai-review` joins the skills with bundled scripts — and
  `stale-map-docs.py` reports none stale

## Spec changes

- `ai-review-refresh` (new) — **normative outcome:** after any push to a pull
  request that has an accepted AI review, made through `pr-open`'s update mode,
  `pr-merge`'s CI-fix step, or feedback resolution, the agent SHALL apply the
  re-review evaluation and report its decision; and the catalog SHALL NOT post
  an AI review trigger for a head SHA that already has one, whoever posted it,
  or that an accepted AI review already names.

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_request_review.py` passes,
  and `uv run pytest .agents/plugins/agentdev/tests` stays green.
- `shellcheck -x .agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.sh`
  is clean.
- `uv run validate_agent_files` passes on the four edited skills.
- `grep -rn "gh pr comment" .agents/plugins/agentdev/skills/*/SKILL.md` shows no
  `@claude review` trigger outside `request-review.sh`.
- Manual: on a reviewed pull request, commit a behavior change no thread asked
  for and run `/agentdev:pr-sync`; the run reports a re-review decision and
  posts one trigger. Rerun `/agentdev:pr-sync` without a new commit; the script
  reports `ALREADY_REQUESTED` and nothing is posted. On a fresh head, type
  `@claude review` by hand, then run the script; it reports `ALREADY_REQUESTED`.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- `update-branch`'s own pushes — it runs no eval after a base merge, though the
  eval counts a judgment-call conflict merge as new scope.
- Inspecting responder runs inside `request-review.sh`.
- Any change to the `ai-review-present` gate or the responder workflow.
- `pr-merge-stack`, which reaches review handling through `pr-merge`.

## Key references

Verified anchor points (line numbers as of 2026-10-23):

- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:266` — step 9, create or
  update the pull request
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:311` —
  `### 10. Error Handling`, renumbered by Task 4
- `.agents/plugins/agentdev/skills/pr-sync/SKILL.md:8` — delegation to `pr-open`
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:199` — step 5, CI-fix
  commit and push
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:240` —
  `## AI Review Recovery`
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:259` — in-conversation
  trigger ledger
- `.agents/plugins/agentdev/skills/pr-merge/SKILL.md:275` — step 3, bare
  `gh pr comment` trigger
- `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md:338` — the
  eval's existing caller
- `.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md:27` —
  `## The test`
- `.agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md:67` —
  `## Establish what the last review saw`
- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md:14` —
  `## Post the request`
- `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md:67` —
  `## Post at most once per head SHA`
- `.agents/plugins/agentdev/skills/pr-discover-ai-responder/agent-code/discover-ai-responder.sh:10`
  — `RESULT_CODES` pattern for a standalone script
- `.agents/plugins/agentdev/bin/result-codes.sh` — shared result helpers
- `.agents/plugins/agentdev/tests/test_discover_ai_responder.py:19` — hermetic
  `PATH` and `gh` stub pattern
- `docs/knowledge/data/codebase/agents/plugins/agentdev/skills.md:36` — skills
  with bundled scripts
