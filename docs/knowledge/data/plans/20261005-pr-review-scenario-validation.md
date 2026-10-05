---
created: 2026-10-05
type: plan
description: Ship pr-review's reachable-scenario correctness bar together with a validator that checks each scenario's trigger, path, and outcome separately, gated on a frozen-candidate validator replay and two full replays per pull request.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-05T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
---

# Ship the reachable-scenario bar with part-by-part validation in pr-review

## Context

[PR review correctness bar](../architecture/pr-review-correctness-bar.md)
records the mixed result of the
[scenario-bar spike](20260929-pr-review-scenario-bar-spike.md). The
reachable-scenario correctness passes found the out-of-diff K4 bug in both #203
runs and added no correctness noise. In one of two #199 runs, however, the
validator dropped K1. That decision leaves validator strictness as the open
question and keeps the shipped bar unchanged until a correction is shown to
hold.

The two K1 candidates differ in whether they name an outcome. The dropped one
names a trigger and a path but no wrong outcome ("operate on the same repository
and branches concurrently"); the confirmed one names what the race corrupts
("Renovate branches, PR bodies, and the dashboard"). The validator's bar — drop
anything "ambiguous, trivial, or not clearly a violation" — is written for rule
claims, where the broken rule can be quoted. This plan tests the hypothesis that
a scenario claim, never as plainly quotable, is dropped under that bar for lack
of a stated outcome; preserved validator records settle it against missing
context or run variance. The code at `7e0413d` also carries a comment presenting
the split as deliberate, while the #199 description promises "a checkbox run
never races a push or scheduled run".

## Approach

Ship the spike's reachable-scenario correctness bar and three validator changes
in one edit to `pr-review/SKILL.md`, merged only if the replays in
`## Verification` hold:

- **A — three-part scenario.** A correctness candidate states its scenario as
  **Trigger** (an input or state reachable at the head commit), **Path** (the
  `file:line` chain from the trigger to the fault), and **Outcome** (the
  concrete wrong result, failure, or security exposure). A candidate missing a
  part is discarded at Step 5 and never reaches validation.
- **B — part-by-part verdict.** A candidate carrying a scenario is validated
  part by part, returning `CONFIRM` or `DROP: trigger|path|outcome — <reason>`.
  The validator branches on the candidate's shape (a scenario is present), never
  on which pass raised it, so the existing rule that the prompt never names a
  pass still holds. Candidates without a scenario keep today's "clearly a
  violation" bar unchanged.
- **C — stated intent is evidence, not a verdict.** A comment or PR description
  presenting a behavior as deliberate does not refute a reachable wrong outcome.
  A PR description promising a guarantee that the code breaks counts toward the
  outcome. This sits in the bar, cuts both ways, and argues no candidate's case,
  so the "Never argue the verdict in the prompt" rule holds.

The validator stays on the `light` model at every effort level, as recorded in
[PR review effort tiers](../architecture/pr-review-effort-tiers.md). Validating
correctness candidates on the `large` model is parked as
[a someday idea](../someday/pr-review-large-validator.md) pending a cost/benefit
evaluation.

**Rejected: change the validator but keep the diff-only bar.** Under the shipped
bar, the #199 baseline validated K1. The drop occurred only under the
reachable-scenario bar, and A and B act on scenario-carrying candidates that
only that bar produces.

### Frozen candidate set

The validator-only replay feeds these candidates to Step 6 exactly as written,
so validation is isolated from candidate generation. Under the new arm, each
claim is split into the three parts using only what the claim itself states; a
part the claim does not state stays empty.

| ID  | Source run      | Location                                       | Claim (verbatim)                                                                                                                                                                                                                                                                       | Expected under A+B+C                  |
| --- | --------------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| F1  | #199 variant 1  | `.github/workflows/renovate.yml:52`            | The new `checkbox`/`main` concurrency-group split removes mutual exclusion between Renovate invocations. A scheduled, push, or manual run can overlap a checkbox-triggered run, allowing both write-capable Renovate jobs to operate on the same repository and branches concurrently. | Discarded at Step 5: no Outcome       |
| F2  | #199 variant 2  | `.github/workflows/renovate.yml:51`            | Splitting checkbox edits into Renovate-checkbox while schedule, push, and manual runs use Renovate-main removes serialization of the same write-capable Renovate job, allowing concurrent runs to race on Renovate branches, PR bodies, and the dashboard.                             | `CONFIRM`                             |
| F3  | #203 variant 1  | `.devcontainer/scripts/postStartCommand.sh:12` | The gh authentication check runs before the GNOME Keyring session is established or loaded, so keyring-backed authentication is missed and the Git credential helper remains unconfigured.                                                                                             | `CONFIRM`                             |
| F4  | #203 variant 1  | `.devcontainer/devcontainer-init.sh:35`        | The host-side initializeCommand unconditionally invokes sha256sum, so devcontainer startup fails on stock macOS hosts where only shasum is available.                                                                                                                                  | `CONFIRM`                             |
| F5  | #203 variant 2  | `.devcontainer/scripts/seed-agent-auth.sh:13`  | When no seed is supplied, the early return skips repairing permissions on an existing credential.                                                                                                                                                                                      | Set by the Task 1 judgment            |
| F6  | #203 baseline 1 | `.devcontainer/devcontainer-init.sh:36`        | Uses `/tmp` for the credential-transfer directory despite the repository rule requiring `./.tmp`.                                                                                                                                                                                      | No more confirms than the current arm |

F1–F5 are correctness candidates and F6 is a compliance candidate. F6 was
confirmed in the #203 baseline but judged noise by the maintainer. The
compliance bar does not change here, so F6 checks only that the stated-intent
rule does not make compliance confirms more likely. F1 runs in the current arm
alone, where it measures how often today's bar drops K1.

## Implementation Steps

### Task 1: Judge the F5 negative control

- [ ] The maintainer marks F5 real or noise against `84d4584`, setting its
  expected verdict in the frozen-candidate table. Closed by: the maintainer.

### Task 2: Ship the reachable-scenario correctness bar

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [ ] Apply the spike's correctness-bar hunks (`@@ -49`, `@@ -57`, `@@ -63`,
  `@@ -66`, `@@ -127`) from the
  [scenario-bar spike's ### Variant skill diff](20260929-pr-review-scenario-bar-spike.md),
  re-anchored to the current file.

### Task 3: Require a three-part scenario on correctness candidates

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [ ] The Correctness focus requires every candidate to carry Trigger, Path, and
  Outcome as defined in `## Approach` (A), and Step 4's pass output carries the
  three parts alongside the description and reason.
- [ ] Step 5 discards a correctness candidate with an empty part before
  validation, and deduplication keeps the scenario of the candidate it retains.

### Task 4: Validate scenarios part by part

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [ ] Step 6's single validator prompt carries a candidate's scenario parts when
  present. For such a candidate, the validator checks each part against the head
  commit and returns `CONFIRM` or `DROP: trigger|path|outcome — <reason>` (B).
  Candidates without a scenario keep the current bar and verdict form.
- [ ] Step 6's bar states the stated-intent rule (C) in a form that applies to
  both outcomes and names no candidate.
- [ ] `pre-commit run validate-agent-files --files .agents/plugins/agentdev/skills/pr-review/SKILL.md`
  passes.

### Task 5: Run the validator-only replay

**Files:** Create: `.tmp/replay/` (harness, inputs, and outputs; not committed)

- [ ] Run Step 6 alone on the frozen candidate set five times per arm with the
  matrix's `light` Codex model and per-candidate dispatch: the **current arm**
  uses `pr-review/SKILL.md` at `main`, and the **new arm** uses the Task 2–4
  edit. Keep every validator's verdict and justification. Record per-candidate
  verdict counts for each arm, plus every new-arm `DROP` with the part it names,
  under `## Verification results`.

### Task 6: Run the full replays

**Files:** Create: `.tmp/replay/` (worktrees at `7e0413d` and `84d4584`)

- [ ] Run the spike's #199 and #203 replays twice each with `codex exec`,
  `gpt-5.6-sol`, medium model reasoning, `REQUESTED REVIEW EFFORT: full`, and
  the Task 2–4 skill. The sessions are not ephemeral, so every pass and
  validator record survives. Score each run against the spike's known-bug key
  K1–K6 and record the table under `## Verification results`.
- [ ] Each unmatched correctness finding is marked real or noise. Closed by: the
  maintainer.

### Task 7: Record the decision

**Files:** Create:
`docs/knowledge/data/architecture/pr-review-scenario-validation.md` Modify:
`docs/knowledge/data/architecture.md`

- [ ] File the outcome against `## Verification` as a decision linking
  [PR review correctness bar](../architecture/pr-review-correctness-bar.md).
  When the gate holds, it records the shipped bar, A, B, and C with the rejected
  alternatives. When it fails, it records the failing part from the preserved
  verdicts, and Task 2–4's edit is not merged. Link it from
  `data/architecture.md`.

## Spec changes

None — no behavioral change to any `data/spec/` contract.
`data/spec/ai-review-gate` governs whether a review is present and whether the
responder may act; this plan changes only `pr-review`'s internal finding and
validation policy, which no `data/spec/` document specifies.

## Verification

The change ships when all of the following hold:

- **Validator-only replay, new arm:** F2, F3, and F4 are confirmed in 5/5 runs;
  F5, if Task 1 judges it noise, is dropped in 5/5, and joins the 5/5-confirm
  set if judged real; F6 is confirmed in no more runs than under the current
  arm; and F1's three-part split has an empty Outcome.
- **Full replays:** both #199 runs validate K1; both #203 runs validate K4 and
  every one of K2, K3, K5, and K6; and each run has at most one unmatched
  correctness finding the maintainer judges noise. Compliance and
  durable-knowledge noise is excluded, as it has independent owners (see
  [PR review correctness bar](../architecture/pr-review-correctness-bar.md)).
- Every new-arm and full-replay `DROP` of a correctness candidate names a part.

Mechanical checks:
`pre-commit run validate-agent-files --files .agents/plugins/agentdev/skills/pr-review/SKILL.md`
passes; the architecture doc is linked from `data/architecture.md`;
`iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Changing the validator's model; see
  [Validate correctness candidates on the large model](../someday/pr-review-large-validator.md).
- The compliance, durable-knowledge, and map-metadata noise owners named in
  [PR review correctness bar](../architecture/pr-review-correctness-bar.md).
- Changing the compliance or durable-knowledge validation bar.
- Light-effort replays, Claude replays, and a permanent replay mode in
  `pr-review`.
- Releasing a new agentdev catalog version.

## Key references

Verified anchor points (line numbers as of 2026-10-05):

- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:47` — Correctness focus
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:49` — "Scan only the diff
  itself"
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:57` — "definitely produce
  wrong results regardless of inputs"
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:63` — "Potential issues
  that depend on specific inputs or state"
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:66` — closing do-not-flag
  sentence
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:110` — validation row of
  the slot matrix
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:127` — Step 4 pass
  dispatch and output shape
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:136` — Step 5 merge and
  deduplicate
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:138` — the single
  validator prompt
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:139` — the validator
  re-derives the claim; `CONFIRM`/`DROP`
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:140` — "Never argue the
  verdict in the prompt"
- `docs/knowledge/data/architecture/pr-review-effort-tiers.md:98` — "Validation
  runs light at every effort level"
- `7e0413d:.github/workflows/renovate.yml:46` — comment presenting the
  concurrency split as deliberate (K1)
