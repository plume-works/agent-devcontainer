---
type: spec
description: How the agentdev pr-review skill reviews a pull request — which diffs it fast-approves, how docs and skills get a durable-knowledge pass, how each review sizes itself, and how a correctness finding is stated and validated.
sources:
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-audit/SKILL.md
- resource: .github/actions/run-claude-responder/action.yml
- resource: .claude/settings.json
---

# PR review

## Purpose

Defines how the `agentdev:pr-review` skill turns a pull request's diff into
validated findings. When the review runs, which identity posts it, and how its
verdict follows its findings belong to `ai-review-gate`.

## Requirements

### Requirement: only mechanical diffs are fast-approved

`pr-review` SHALL publish an `APPROVE` review without running the review passes
only for a diff that changes versions alone or generated files alone. Every
other diff, a documentation-only diff included, SHALL run the review passes.

#### Scenario: a documentation-only diff

- **WHEN** a pull request changes only documentation
- **THEN** it is not fast-approved, and the review runs the durable-knowledge
  pass on it.

### Requirement: docs and skills get a durable-knowledge pass

When the diff contains docs or skills files — documents under `data/`,
`README.md`, `AGENTS.md`, `SKILL.md` and `*.agent.md` definitions, or docstrings
— `pr-review` SHALL add one durable-knowledge pass to the compliance and
correctness passes, and SHALL NOT run it on a code-only diff. The pass SHALL run
`/agentdev:iwe-audit` in diff mode over the changed docs and skills files, where
the audit's candidates are the diff's added lines and the audit reports its
table without editing them. Each audit finding SHALL become an inline review
comment on the diff line holding its quoted text, kept only when the added line
can be quoted and the rule it breaks named. A durable-knowledge finding SHALL be
blocking. Correctness passes SHALL scan only code files and the
durable-knowledge pass only docs and skills files, so a mixed diff gets both in
one review.

#### Scenario: a mixed docs and code diff

- **WHEN** a pull request changes both code and a skill definition
- **THEN** the correctness passes review the code, the durable-knowledge pass
  reviews the skill, and both report in the same review.

#### Scenario: a code-only diff

- **WHEN** a pull request changes no docs or skills file
- **THEN** no durable-knowledge pass runs, and the compliance and correctness
  passes run unchanged.

### Requirement: every AI review sizes itself

The `pr-review` skill SHALL size each review from the diff it holds, at the
`light` or `full` effort tier, and nothing SHALL request a tier: no pull request
body marker, label, or prompt line selects one, and `run-claude-responder` SHALL
pass Claude no model, so the orchestrator runs on the model the repository's
`.claude/settings.json` pins. At `full` effort every slot SHALL run on the
`large` model except compliance and validation; at `light` effort every slot
SHALL run on the `light` model. Each dispatch SHALL carry the model its slot
gets. Validation SHALL run on the `light` model at every effort level. Both
tiers SHALL run the metadata gate and, when the diff holds docs or skills files,
the durable-knowledge pass. Only the `light` tier SHALL validate its candidates
in one batched dispatch; a `full` or self-sized review SHALL validate each
candidate in its own dispatch.

#### Scenario: a large documentation rewrite

- **WHEN** a pull request rewrites documentation only
- **THEN** the review still runs the metadata gate and the durable-knowledge
  pass at whatever tier it sizes itself to.

#### Scenario: a review at full effort

- **WHEN** the review sizes itself to `full`
- **THEN** it runs two compliance passes on the `light` model, two correctness
  passes on the `large` model, and one validation dispatch per surviving
  candidate on the `light` model.

### Requirement: a correctness finding names a reachable scenario

A correctness pass SHALL read, at the head commit, the code the changed lines
call, the code that calls them, and the code that runs beside them in the same
lifecycle or workflow. Every correctness candidate SHALL state a **Trigger**, an
input or state the code can receive at the head commit; a **Path**, an anchor
chain from the trigger to the fault; and an **Outcome**, the wrong result it
produces. A candidate with an empty part SHALL be discarded before validation.

The validator SHALL receive a scenario candidate's three parts in place of its
claim, SHALL judge them as written in trigger, path, outcome order, and SHALL
return `CONFIRM` only when every part holds, or `DROP` naming the first part
that does not. A candidate without a scenario SHALL be judged on its claim and
dropped unless it is clearly a violation. A comment or pull request description
presenting a behavior as deliberate SHALL NOT by itself refute a reachable wrong
outcome, and a guarantee the description promises that the code breaks SHALL
count toward the outcome. The validator SHALL NOT be told which pass raised a
candidate.

#### Scenario: a candidate with no outcome

- **WHEN** a correctness pass reports a candidate with a Trigger and a Path but
  no Outcome
- **THEN** the candidate is discarded before validation and never posted.

#### Scenario: a false path

- **WHEN** a candidate's Trigger can occur but its Path does not lead to the
  fault as written
- **THEN** the validator returns `DROP: path` and the finding is not posted.

## Rationale

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
