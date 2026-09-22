---
type: architecture
description: Why the AI pull request review has two named effort tiers, why an explicitly requested tier is absolute, and why the responder's preflight job rather than the review skill resolves it.
generated:
  by: claude-code/opus-5
  at: 2026-09-18T00:00:00Z
sources:
- resource: .github/workflows/ai-responder.yml
- resource: .github/actions/run-claude-responder/action.yml
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .claude/settings.json
- resource: data/plans/20260917-pr-review-effort-tiers.md
- resource: https://code.claude.com/docs/en/sub-agents
---

# PR review effort tiers

## Decision

The AI pull request review runs at one of two named effort tiers, `light` or
`full`, which fix both axes the review's cost scales on: how many initial passes
fan out, and how many validation dispatches the surviving findings cost.

`full` is the review at full strength — two compliance passes, two correctness
passes, the durable-knowledge pass, and one isolated validation dispatch per
surviving candidate, everything on the large model except compliance and
validation. `light` runs one compliance pass, one correctness pass, and the
durable-knowledge pass, all on the light model, and validates every surviving
candidate in a single batched dispatch.

Neither tier changes whether a review is required. `ai-review-present` is
untouched by the tier: this is a lever over what a review costs, never over
whether one happened.

The tiers are several times apart in cost on the same diff, and the model matrix
is what produces the gap: a light review spends nothing on the large model,
while a full review spends the bulk of its budget on its two correctness passes
and the durable-knowledge pass. Wall clock does not show the difference, because
both tiers are dominated by passes running in parallel — a light review can take
longer than a full one and still cost a fraction as much.

## An explicitly requested tier is absolute

A requested tier is obeyed exactly — no escalation to the other tier, no
refusal, and no failing the review, whatever the tier's fit for the diff.

A lever that the thing it controls may overrule is not a lever. If the reviewer
could promote a `light` request to `full` on a diff it judged too large, the
request would be a suggestion, and the one case the tiers exist for — a large
documentation rewrite the author knows needs only a cheap pass — would be
exactly the case that ignored it.

## No tier means judgment, not a default

When no tier is requested, the responder passes no `--model`, the session keeps
the model `.claude/settings.json` pins, and the review sizes itself from the
diff it already holds: pass count, the model for each slot, and the
durable-knowledge pass's model and depth.

This is deliberately judgment rather than a configured default tier. The review
skill already makes this class of call at Step 1, where it fast-approves a
mechanical diff without launching any passes. A configured default would have to
be right for every diff in advance; the orchestrator is holding the diff.

## Why preflight resolves the tier

**A session cannot change its own model.** Only a workflow-level
`claude_args --model` can size the orchestrator, so the tier has to be known
before the session starts — which puts resolution in the responder's preflight
job, where both request channels are already parsed, and rules out resolving it
inside the review skill.

A tier reaches preflight from an `@claude review <label>` comment or a
`[ci:review-effort=<label>]` marker alone on a line of the pull request body,
the comment outranking the marker. That precedence and the own-line anchoring
are the ones `[ci:skip-ai-review]` already established, so the effort label
joins an existing vocabulary instead of starting a second one with its own
rules. The requirements live in the [AI review gate](../spec/ai-review-gate.md)
spec.

## Per-dispatch models are what put the matrix in force

A per-dispatch model argument is the highest-priority term in Claude Code's
[subagent model order](https://code.claude.com/docs/en/sub-agents), above a
definition's frontmatter, the `CLAUDE_CODE_SUBAGENT_MODEL` environment variable,
and the main conversation's model. A dispatch that passes no model argument
therefore runs at the session model, so the per-dispatch argument is what puts
the effort matrix in force.

## Compliance runs light at both tiers

Compliance is the one slot that does not move between tiers: it runs on the
light model at `full` as well as at `light`. Compliance work is quoting a rule
and checking a diff against it — instruction-following, not reasoning — and the
review's high-signal bar already requires a compliance finding to quote the
exact rule text it breaks. The large model buys nothing against that bar.

## Validation runs light at every effort level

Validation is the last gate before publication, and what makes it work is the
bar it applies — confirm only what the validator re-derives from the files
itself — not the size of the model applying it. That bar lives in the prompt,
which is why the validator prompt is the same everywhere and the model is not
among the things a tier changes. It is fixed at the light model even where no
tier was requested and the review sizes the rest of itself.

Raising the model here cuts against the gate. A stronger reasoner asked to
confirm only at high confidence is also the better advocate for dropping, so
size buys more persuasive refusals rather than more accurate verdicts. Depth
belongs in the passes that find candidates; the gate that judges them wants a
constant bar.

Validation is also the only slot whose dispatch count scales with the number of
findings, so at full effort it is the one term with no ceiling. Holding it at
the light model bounds what an unusually productive review can cost.

Batching is the separate axis, and it is the light tier's trade alone. A review
that was handed no tier keeps per-candidate isolation: judgment sizes how much
work the review does, never whether a finding is judged on its own.

## Rejected alternatives

**Whole-tier auto-escalation on a large documentation diff.** Upgrade a `light`
review to `full` when the diff carries a lot of documentation. Rejected on two
counts: it lets the reviewer overrule a human's stated tier, which is the one
thing a hard override must not permit, and it returns the motivating case — a
README rewrite — to costing exactly what it cost before the tiers existed.

**A documentation-line threshold that fails the review.** Refuse a `light`
review above some count of added documentation lines and demand `full`. Rejected
because the threshold is a number nobody can source, needs tuning against real
pull requests, and drifts as the corpus changes.

**Dropping the metadata gate and the durable-knowledge pass at light effort.**
Rejected because it makes `light` a weaker review rather than a cheaper one.
Model tiering and pass count deliver the saving with no coverage traded away, so
both checks run at both tiers.

**Batching full-effort validation.** Rejected because per-candidate isolation is
what stops a weak finding reading as strong beside three strong ones. The light
tier accepts that risk for the saving; the full tier is the one that must not.
The consequence is accepted: full-effort cost still scales with finding count.

**Resolving the tier inside the skill.** Rejected because a session cannot
change its own model; see "Why preflight resolves the tier" above.

**Making the light model an alias rather than a full identifier.** Rejected
because `claude_args` examples resolve full model identifiers; an alias is not a
documented input there. The identifiers stay unversioned, so each tracks its
latest release.
