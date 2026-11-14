---
type: spec
description: When the agentdev pr-* skills evaluate whether a reviewed pull request needs a fresh AI review, how they request one at most once per head commit and its title and description, and how they judge a requested review's progress.
sources:
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-eval-review-needed/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py
- resource: .github/workflows/ai-responder.yml
- resource: .agents/plugins/agentdev/skills/pr-open/agent-code/push-branch.py
- resource: .agents/plugins/agentdev/skills/update-branch/SKILL.md
---

# AI review refresh

The [AI review gate](ai-review-gate.md) passes on any accepted AI review across
later pushes and leaves refreshing the review to the author. This spec states
how the agentdev catalog makes that call and carries it out.

## Rationale

### A responder check counts as a request unless it was skipped or cancelled

A skipped responder is the gate-only run that a push to an already-reviewed pull
request starts, so it reviewed nothing. Where a check's meaning is in doubt, the
script leans toward requesting: a duplicate costs one redundant review, while a
wrongly counted check leaves the head unreviewed. A check that completed with a
failure still counts, so a failed review is reported to a person rather than
retried on the same input.

The responder check already names the head commit it ran on, so a request posts
no per-request marker comment naming the head; the optional rationale comment is
the only comment.

### Re-review evaluation hangs off pr-open update mode

`pr-open` update mode runs `pr-eval-review-needed` on every run, whatever the
push or the body edit changed, so `pr-sync` and a direct update-mode run are
covered by one hook. `pr-feedback-resolution` applies `pr-eval-review-needed`
itself and pushes through `pr-open`'s `push-branch.py` rather than through the
`pr-open` skill, so one feedback pass never evaluates twice. The evaluation
reads review threads and review comments from the pull request, so a cold run
from `pr-sync` or `pr-merge` decides on the same footing as a feedback pass that
holds the conversation.

`update-branch` pushes a base merge without a re-review evaluation, even though
`pr-eval-review-needed` counts a judgment-call conflict merge as new scope.

Rejected:

- **Hook the evaluation into `pr-sync` alone.** `pr-open` reached directly in
  update mode would push unevaluated.
- **Evaluate only when this run's push moved the head.** A head pushed earlier
  by another path would be skipped unevaluated.

### A review covers its head together with the title and description it read

The metadata gate reads the title and description once, when a responder run
starts, so only runs started after the latest edit, and the reviews they submit,
cover a head. The rule applies to every AI review, not only to a stop at the
metadata gate, because a full review runs the gate too; it cannot loop, because
each further review needs a further edit. An edit never starts a review by
itself and no review is marked as a metadata-gate stop: requesting stays
explicit.

The edit cutoff comes from one GraphQL query: `PullRequest.lastEditedAt` for the
description and the newest `RENAMED_TITLE_EVENT` for the title. The design
assumes GitHub records no edit when the text is unchanged, and accepts one extra
review if it does.

Rejected:

- **A hash of the title and description in the gate's review body.** Precise on
  a revert, but it needs a review-body format, a computation in `pr-review`, and
  a text-normalization rule; edit timestamps change only `request-review.py` and
  cost at worst one extra review.
- **An override argument on `request-review.py`.** It moves the per-head guard
  to the caller's judgment.

### Only the AI reviewer's own change request forces a re-review

A `CHANGES_REQUESTED` verdict holds the merge until the same reviewer approves,
so it is re-requested whatever the diff holds. An AI reviewer with only
`COMMENTED` reviews is left to the scope test. A human reviewer's change request
never triggers an AI re-review: lifting it is that reviewer's call.

Rejected:

- **Re-request on every push while no AI approval exists.** It would also
  re-request after a `COMMENTED`-only review, which cannot produce an approval
  (GitHub accepts only `COMMENT` on the reviewer's own pull request), and adds a
  review per push for no gain.
