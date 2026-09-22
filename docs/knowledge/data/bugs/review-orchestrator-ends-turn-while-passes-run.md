---
type: bug
description: The review orchestrator can end its turn while its dispatched passes are still running, so the responder job finishes green having published no review, and the gate accepts an older review instead of catching the miss.
generated:
  by: claude-code/opus-5
  at: 2026-09-19T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .github/workflows/ai-responder.yml
- resource: https://github.com/plume-works/agent-devcontainer/pull/163
---

# The review orchestrator ends its turn while its passes are still running

## Symptom

The `Claude PR Review Responder` job completes successfully and publishes no
review. The session's final message reads as a progress update — that the
initial passes are running in the background and it will continue when they
report back — rather than as a published result.

Nothing marks the run as failed. `is_error` is false and the job is green, so
the only signal that a review is missing is the absence of a new review on the
pull request.

The miss is silent whenever the pull request already carries an accepted review:
`ai-review-present` asserts that the pull request has been reviewed, not that
this run reviewed it, so it passes on the earlier review. A pull request with no
prior review keeps a red gate and the miss is visible; a re-review that vanishes
this way is not.

## Reproduction

Every successful review job in the available run history was checked against the
reviews on its pull request: does a review by `github-actions[bot]` or
`claude[bot]` carry a `submitted_at` inside that job's own start/finish window?

``` bash
gh run list --workflow ai-responder.yml --limit 200 \
  --json databaseId,conclusion,event,createdAt,headBranch,status
gh api repos/<owner>/<repo>/actions/runs/<run>/jobs   # the review job's window
gh api repos/<owner>/<repo>/pulls/<pr>/reviews        # reviews, with submitted_at
```

Fourteen review jobs succeeded. Eleven published a review; three did not, and
the three are consecutive runs against one head commit:

| Run           | Tier  | Turns | Published |
| ------------- | ----- | ----- | --------- |
| `35398906219` | none  | 30    | yes       |
| `35466872251` | none  | 15    | no        |
| `35467154796` | light | 13    | no        |
| `35467428112` | full  | 20    | no        |

The three that published nothing ended on a progress message rather than a
result — "Four review passes are running in the background … I'll continue as
each reports back", "Waiting for the three background review passes … I'll be
notified automatically when they complete".

Two candidate explanations are ruled out by the same history. **Model:** the
first failure ran on the pinned model, not the light one. **Trigger:** runs
`34752569108` and `34676051181` were `workflow_dispatch` re-reviews and both
published, so a dispatched re-review is not itself the trigger.

What does separate them is the review skill in the checkout. The eleven runs
that published read `pr-review/SKILL.md` as it stands on `main`; the three that
did not read the revision on this branch, which rewrote Step 4's dispatch
bullets and Step 6. Eleven of eleven before, zero of three after.

## Root cause

A headless `claude -p` session ends when its turn ends. There is no later
notification that resumes it, so a turn that dispatches background workers and
then emits text is the last thing the run does — the workers' results are never
collected and Steps 5 through 9 never execute. The orchestrator's own closing
words name the affordance it expected: the `Agent` tool reports that subagents
run in the background and notify on completion, which holds in an interactive
session and not under `-p`.

`pr-review/SKILL.md` forbids this directly. Step 4 requires blocking until every
pass reports back and states that the dispatching turn must not be the last
turn; "Waiting on Parallel Passes" adds a self-check gate requiring a blocking
call for every dispatched task before emitting text. Both survived the Step 4
rewrite unedited, so no rule was removed.

What the rewrite changed is how much sits between the dispatch instruction and
the blocking rule: a new model bullet was inserted ahead of the runner bullets,
and the model argument became the emphasized thing about a dispatch. The
correlation is strong and the mechanism is not proven — an instruction that is
present but out-competed for attention cannot be distinguished, from run logs
alone, from one the model simply did not follow.

### Hypothesis: the passes die on exhausted quota

A subagent that is refused mid-flight never reports back, and a parent holding
no completion has nothing to block on. That would make the abandonment a symptom
of quota rather than of instruction adherence, and it fails silently in exactly
the shape this document records.

The three runs' own telemetry does not confirm it. Each carries
`rate_limit_event` records reading `status: allowed` throughout, with five-hour
window utilization climbing 21% to 50% across them and never exhausting; the
limit is a rolling `five_hour` window, and `overageStatus: rejected`
(org-disabled) never engages because the window never runs out. All three report
`is_error: false`.

Nor does it eliminate the hypothesis. The telemetry belongs to the orchestrator
session, and a refusal inside a subagent need not surface there. What the
artifacts do show is that all three runs dispatched passes — four, three, and
five — and received zero completions between them, which the headless-turn
mechanism and a silent subagent death produce alike.

What would settle it: per-subagent outcome in the execution artifact, so a pass
that was refused is distinguishable from one whose result was never collected.

## Fix

Open.

**Failing a run that published nothing was tried and removed.** The responder
action took a `require-review` input: it stamped a timestamp before the Claude
step and afterwards required a review by `claude[bot]` or `github-actions[bot]`
with `submitted_at` at or after the stamp. It is not sound. The predicate
matches any qualifying review in the window with nothing tying it to the run
that is being checked — no `commit_id`, no review id, no run id, no marker in
the review body — so an abandoned run passes on a concurrent run's review, which
is the very miss it exists to catch.

Concurrent responder runs on one pull request are ordinary, not exotic. A
dispatched run's concurrency group is keyed `dispatch-<comment_id>`, so two
`@claude review` comments occupy different groups; a dispatched run and a
`pull_request`-triggered run (`pr-<n>`) are likewise distinct.
`cancel-in-progress` is set only for `pull_request` + `synchronize`, so nothing
cancels an in-flight dispatched run. Two reviews requested minutes apart overlap
for their whole duration, and the second one's stamp sits before the first one's
publication.

Closing that gap needs an identity, not a window: the run URL stamped into the
published review body, or the submitted review's id captured from the session.

The remaining candidates:

- Have the gate distinguish "reviewed" from "reviewed in this run". That is a
  deliberate property of `ai-review-present` — see
  [AI review gate](../spec/ai-review-gate.md) — and reopening it costs the
  re-review ergonomics the spec chose on purpose.
- Strengthen the skill's self-check so the blocking call is the only way to
  reach Step 5. The rule already exists; restating it more loudly is the weakest
  of the three unless the restatement changes what the orchestrator reads at the
  moment it decides to stop.
- Settle the quota hypothesis above first. A detection check and an
  instruction-adherence fix address different causes, and the evidence does not
  yet say which one this is.

A fix should not be chosen from this document alone: the failure is
intermittent, and three observed runs are too small a sample to tell an
instruction-adherence problem from a runner-behavior one.
