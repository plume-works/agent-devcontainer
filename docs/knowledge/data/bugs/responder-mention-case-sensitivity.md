---
type: bug
description: The workflow gate that admits an `@claude` mention is case-insensitive while the JavaScript that classifies it is not, so `@Claude review` starts the free-form task responder instead of a review and resolves no effort tier.
generated:
  by: claude-code/opus-5
  at: 2026-09-21T07:45:00Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: https://github.com/plume-works/agent-devcontainer/pull/163
---

# A capitalized `@Claude` mention is admitted, then misrouted

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

Open. The narrow change is to fold case in the JavaScript tests so they admit
exactly what the gate admits — one `toLowerCase()` before the `startsWith` pair
and an `i` flag on the label regex. That leaves one case rule for the whole
path, chosen by the gate that runs first.

The wider question the defect raises is whether the gate and the classifier
should share a single mention test rather than two written in different
languages, which is what let them drift apart.

## Key references

Verified anchor points (line numbers as of 2026-09-21):

- `.github/workflows/ai-responder.yml:107-118` — the case-insensitive `if:` gate
- `.github/workflows/ai-responder.yml:300-307` — `mentions()`, case-sensitive
- `.github/workflows/ai-responder.yml:401` — the bridge's review-versus-task
  split
- `.github/workflows/ai-responder.yml:402` — the effort label extraction
