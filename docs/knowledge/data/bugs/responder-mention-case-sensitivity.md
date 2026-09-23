---
type: bug
description: The workflow gate that admits an `@claude` mention folds case while the JavaScript that classified it did not, so `@Claude review` started the free-form task responder instead of a review and resolved no effort tier.
generated:
  by: claude-code/opus-5
  at: 2026-09-21T07:45:00Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: https://github.com/plume-works/agent-devcontainer/pull/163
stage: done
---

# A capitalized `@Claude` mention was admitted, then misrouted

## Symptom

`@Claude review` on a pull request starts the AI Responder and runs the
free-form task responder. The review job is skipped, no review is published, no
effort tier resolves, and the `require-review` check never applies because it
belongs to the job that did not run.

The same comment written `@claude review` runs the review job. Nothing in the
run reports the divergence: the responder that starts is a legitimate job doing
what its prompt says, so the only symptom is a review that never arrives.

`@Claude review light` loses the tier the same way — the label reaches the
dispatch as part of a free-form task body rather than as `review_effort`.

## Reproduction

Comment `@Claude review` on a pull request. The preflight job runs and reports

``` text
DISPATCH_TASK: @Claude review
DISPATCH_REVIEW_EFFORT:
```

`Claude Task Responder` runs; `Claude PR Review Responder`, `ai-review-present`,
and the branch dispatch job are all skipped. Run `35573230682` is that case, and
run `35526047450` the lowercase control: same pull request, same head commit, a
review job that ran to a published review.

## Root cause

Two admission tests disagree about case.

The preflight `if:` gate at `.github/workflows/ai-responder.yml:107-118` uses
the workflow expression language's `startsWith`, which compares strings
case-insensitively, so `@Claude` opens a run. Every test downstream is
JavaScript `String.prototype.startsWith` or a case-sensitive regex against the
literal `@claude`: the bridge's review-versus-task split at `:401`, the effort
label at `:402`, and `mentions()` at `:300-307`. A mention the gate admits is
therefore classified as though it carried no mention at all, which for a pull
request comment means a free-form task.

The bridge's `task:` test predates the effort tiers; the `review_effort` regex
inherited its case sensitivity rather than introducing the defect.

## Fix

Every mention test folds case, so the whole path admits exactly what the gate
admits. `opensWith` lowercases before comparing and `mentions()` calls it for
each field; the bridge lowercases before its review-versus-task `startsWith`,
and the label regex carries `i` and lowercases what it captures, so a dispatched
`review_effort` is always canonical.

The gate that runs first sets the rule. It cannot narrow to match the
JavaScript: `if:` has no case-sensitive string test, and a mention the gate
rejects never reaches a job at all.

The spec needs nothing: `A @claude mention opening a comment` in
[AI review gate](../spec/ai-review-gate.md) never named a case, so the code was
narrower than the behavior the spec already described.

## Key references

Verified anchor points (line numbers as of 2026-09-21):

- `.github/workflows/ai-responder.yml:107-118` — the case-insensitive `if:` gate
  that sets the rule
- `.github/workflows/ai-responder.yml:298-306` — `opensWith` and `mentions()`
- `.github/workflows/ai-responder.yml:401-403` — the bridge's review-versus-task
  split and the effort label
