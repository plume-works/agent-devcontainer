---
type: spec
description: This spec defines how the agentdev pr-review skill reviews a pull request. It covers the diffs that the skill fast-approves, the durable-knowledge pass, the review size, and the rules for a correctness finding.
sources:
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-audit/SKILL.md
- resource: .github/actions/run-claude-responder/action.yml
- resource: .claude/settings.json
- resource: .github/workflows/ai-responder.yml
---

# PR review

## Purpose

Defines how the `agentdev:pr-review` skill turns a pull request's diff into
validated findings. When the review runs, which identity posts it, and how its
verdict follows its findings belong to `ai-review-gate`.

## Rationale

### Passes are collected through foreground calls

A headless `claude -p` run ends with its turn, so a pass dispatched in the
background is abandoned with the session. Foreground calls cannot be cancelled
one at a time, so the Claude Code path has no per-pass ceiling and no
drop-a-hung-pass fallback: the `claude-respond` job's `timeout-minutes` is the
review's only ceiling.

Rejected:

- **Running every pass sequentially.** It gives up parallelism and each pass's
  clean context, which foreground calls keep.
- **Keeping background dispatch and waiting through another primitive.** It
  binds the skill to a wait tool a Claude Code version bump can remove.

### Every review sizes itself

The review holds the diff, so it judges its own pass count and models; no caller
requests a tier. Validation stays on the `light` model because its bar,
confirming only what the validator re-derives from the files, lives in the
prompt: a stronger model argues more persuasively for dropping rather than
judging more accurately, and validation is the only slot whose dispatch count
scales with findings. Compliance stays `light` because quoting a rule and
checking the diff against it is instruction-following.

Rejected:

- **A requested tier from a body marker, a comment, or a label.** A tier request
  has to be resolved before the session starts, since a session cannot change
  its own model, and the review is better placed to size itself than a setting
  chosen ahead of the diff.
- **Escalating a `light` review to `full` on a large documentation diff.** It
  overrules a stated tier and returns the cheap documentation case to full cost.
- **Failing a `light` review above a documentation-line threshold.** The
  threshold is a number nobody can source and drifts as the corpus changes.
- **Dropping the metadata gate and the durable-knowledge pass at `light`.** It
  makes `light` a weaker review rather than a cheaper one.
- **Batching validation at `full` effort.** Per-candidate isolation stops a weak
  finding reading as strong beside strong ones.

### Correctness findings are validated part by part

A correctness finding needs a reachable scenario, and the validator judges its
three parts as written rather than the claim they support.

Rejected:

- **Give the validator the claim alongside the parts.** It re-derives the claim
  and confirms candidates whose stated part is false.
- **Keep the diff-only correctness bar with the part-by-part validator.** The
  validator acts only on the scenario candidates the reachable-scenario bar
  produces.

### Docs and skills are reviewed for durable knowledge

The durable-knowledge discipline of the repository `AGENTS.md` is enforced at
review time by a pass of its own. `iwe-audit` owns the criteria and knows
nothing of GitHub; `pr-review` owns the translation of its table into inline
comments and the high-signal filter. Its findings are blocking so they win a
deduplication collision with a non-blocking compliance finding on the same line.

Rejected:

- **Fast-approving documentation-only diffs.** Documentation and skills would
  ship without the durable-knowledge check.
- **Turning a correctness pass into the durable-knowledge pass.** It takes code
  correctness coverage away from mixed diffs.
- **Restating the audit's criteria in `pr-review`.** Two copies of one rule set
  drift apart.
- **An `iwe-audit` mode that emits GitHub review comments.** It puts review
  mechanics inside the auditor.
