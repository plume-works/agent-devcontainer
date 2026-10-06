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
- **B — scenario judged as written.** For a candidate carrying a scenario, the
  validator prompt carries its Trigger, Path, and Outcome in place of the
  free-text claim. The validator judges the parts in order — trigger, then path,
  then outcome — each as written against the head commit, stops at the first
  that does not hold, and returns `CONFIRM` or
  `DROP: trigger|path|outcome — <reason>`. A part false as written is a drop
  naming that part, even when another scenario would reach the same fault. The
  validator branches on the candidate's shape (a scenario is present), never on
  which pass raised it, so the existing rule that the prompt never names a pass
  still holds. Candidates without a scenario keep their claim and the existing
  "clearly a violation" bar unchanged.
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

**Rejected: carry the claim alongside the scenario parts.** Given both, the
validator re-derives the claim and confirms a candidate whose stated part is
false; see `### Validator-only replay` under `## Verification results`.

### Frozen candidate set

The validator-only replay feeds these candidates to Step 6 exactly as written,
so validation is isolated from candidate generation. Under the new arm, each
claim is split into the three parts using only what the claim itself states; a
part the claim does not state stays empty, and the prompt carries the parts in
place of the claim.

| ID  | Source run      | Location                                       | Claim (verbatim)                                                                                                                                                                                                                                                                       | Expected under A+B+C                  |
| --- | --------------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------- |
| F1  | #199 variant 1  | `.github/workflows/renovate.yml:52`            | The new `checkbox`/`main` concurrency-group split removes mutual exclusion between Renovate invocations. A scheduled, push, or manual run can overlap a checkbox-triggered run, allowing both write-capable Renovate jobs to operate on the same repository and branches concurrently. | Discarded at Step 5: no Outcome       |
| F2  | #199 variant 2  | `.github/workflows/renovate.yml:51`            | Splitting checkbox edits into Renovate-checkbox while schedule, push, and manual runs use Renovate-main removes serialization of the same write-capable Renovate job, allowing concurrent runs to race on Renovate branches, PR bodies, and the dashboard.                             | `CONFIRM`                             |
| F3  | #203 variant 1  | `.devcontainer/scripts/postStartCommand.sh:12` | The gh authentication check runs before the GNOME Keyring session is established or loaded, so keyring-backed authentication is missed and the Git credential helper remains unconfigured.                                                                                             | `CONFIRM`                             |
| F4  | #203 variant 1  | `.devcontainer/devcontainer-init.sh:35`        | The host-side initializeCommand unconditionally invokes sha256sum, so devcontainer startup fails on stock macOS hosts where only shasum is available.                                                                                                                                  | `CONFIRM`                             |
| F5  | #203 variant 2  | `.devcontainer/scripts/seed-agent-auth.sh:13`  | When no seed is supplied, the early return skips repairing permissions on an existing credential.                                                                                                                                                                                      | Discarded at Step 5: no Outcome       |
| F6  | #203 baseline 1 | `.devcontainer/devcontainer-init.sh:36`        | Uses `/tmp` for the credential-transfer directory despite the repository rule requiring `./.tmp`.                                                                                                                                                                                      | No more confirms than the current arm |

F1–F5 are correctness candidates and F6 is a compliance candidate. F6 was
confirmed in the #203 baseline but judged noise by the maintainer. The
compliance bar does not change here, so F6 checks only that the stated-intent
rule does not make compliance confirms more likely. F1 and F5 run in the current
arm alone, where they measure how often the current arm's bar drops a real
finding.

F1 and F5 name a fault but not the harm it causes, so A discards them. Their
counterparts with every part stated run in the new arm: F2 for F1, and F5′ for
F5:

- **Trigger:** `postCreateCommand.sh` runs `seed-agent-auth.sh` with no seed
  file while an agent credential already exists at the target path with a mode
  looser than `0600`.
- **Path:** `.devcontainer/scripts/seed-agent-auth.sh:13-16` returns before the
  `chmod 600 "$target"` at `:25`.
- **Outcome:** the existing credential stays readable beyond its owner.

F5′'s Outcome is false as written, so it is expected to drop naming `outcome`:
at `84d4584`, `postCreateCommand.sh:71` sets both credential parent directories
to `0700` before `:72` runs `seed-agent-auth.sh`, so a loose-mode credential is
not readable beyond its owner. F5′ is therefore a natural negative control, and
F2 is the only confirmed counterpart of a discarded candidate. The maintainer
excludes F5′ from evaluation; see `## Verification`.

A finding is **real** when the pull request as merged contains a fix that
matches it; a finding with no matching merged fix is judged by the maintainer.

### Correctness negative controls

The spike produced no correctness candidate judged noise, so the new arm's
negative controls are real findings with exactly one part broken. Each must be
dropped, and the drop must name the broken part:

| ID  | Built from | Broken part | Replaced with                                                                                                   |
| --- | ---------- | ----------- | --------------------------------------------------------------------------------------------------------------- |
| M1  | F4         | Trigger     | `initializeCommand` runs on a Linux host with GNU coreutils installed.                                          |
| M2  | F3         | Path        | `postStartCommand.sh:14` runs `setup-gh-credential-helper.sh` after `setup-keyring.sh` has started the keyring. |
| M3  | F2         | Outcome     | The checkbox and main runs appear under separate concurrency-group names in the Actions run list.               |

At `84d4584`, GNU `sha256sum` is present on such a host, the helper runs at
`postStartCommand.sh:12` and the keyring at `:14`, and separate group names are
harmless, so each mutant fails only in its broken part.

## Implementation Steps

### Task 1: Judge F5

- [x] The maintainer marks F5 real or noise against `84d4584`, setting its
  expected verdict in the frozen-candidate table. Closed by: the maintainer.
  - **Evidence:** F5 is real under the merged-fix rule in `## Approach`: the
    #203 squash merge `a5bf422` adds the `chmod 600` repair to the early return
    at `.devcontainer/scripts/seed-agent-auth.sh:13`.

### Task 2: Ship the reachable-scenario correctness bar

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [x] Apply the spike's correctness-bar hunks (`@@ -49`, `@@ -57`, `@@ -63`,
  `@@ -66`, `@@ -127`) from the
  [scenario-bar spike's ### Variant skill diff](20260929-pr-review-scenario-bar-spike.md),
  re-anchored to the current file.
  - **Evidence:** the
    `feat(pr-review): ship the reachable-scenario correctness bar` commit
    applies the five hunks verbatim at unchanged line numbers;
    `pre-commit run validate-agent-files` and
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    pass.

### Task 3: Require a three-part scenario on correctness candidates

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [x] The Correctness focus requires every candidate to carry Trigger, Path, and
  Outcome as defined in `## Approach` (A), and Step 4's pass output carries the
  three parts alongside the description and reason.
  - **Evidence:** the
    `feat(pr-review): require a three-part correctness scenario` commit defines
    the three parts in the Correctness focus's closing paragraph and adds them
    to Step 4's issue shape; `pre-commit run validate-agent-files` passes.
- [x] Step 5 discards a correctness candidate with an empty part before
  validation, and deduplication keeps the scenario of the candidate it retains.
  - **Evidence:** the same commit's Step 5 discards a correctness candidate with
    an empty Trigger, Path, or Outcome before collapsing, and a collapse retains
    one candidate whole, scenario included.

### Task 4: Validate scenarios part by part

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [x] Step 6's single validator prompt carries a candidate's scenario parts when
  present. For such a candidate, the validator checks each part against the head
  commit and returns `CONFIRM` or `DROP: trigger|path|outcome — <reason>` (B).
  Candidates without a scenario keep the current bar and verdict form.
  - **Evidence:** the
    `feat(pr-review): validate correctness scenarios part by part` commit adds
    the scenario parts to Step 6's prompt and splits the re-derive bullet by
    candidate shape, keeping the original bar and verdict for candidates without
    a scenario.
- [x] Step 6's bar states the stated-intent rule (C) in a form that applies to
  both outcomes and names no candidate.
  - **Evidence:** the same commit adds Step 6's "Stated intent is evidence, not
    a verdict" bullet, which names no candidate or pass.
- [x] `pre-commit run validate-agent-files --files .agents/plugins/agentdev/skills/pr-review/SKILL.md`
  passes.
  - **Evidence:** the hook passes on the same commit's `SKILL.md`, as does
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`.

### Task 5: Run the validator-only replay

**Files:** Create: `.tmp/replay/` (harness, inputs, and outputs; not committed)

- [x] Run Step 6 alone on the frozen candidate set, F5′, and M1–M3 five times
  per arm with the matrix's `light` Codex model and per-candidate dispatch: the
  **current arm** uses `pr-review/SKILL.md` at `main`, and the **new arm** uses
  the Task 2–4 edit. Keep every validator's verdict and justification. Record
  per-candidate verdict counts for each arm, plus every new-arm `DROP` with the
  part it names, under `## Verification results`.
  - **Evidence:** the `docs(plan): record the validator-only replay` commit
    records all 70 runs under `### Validator-only replay`; the new arm fails the
    gate on F5′, M1, M2, and M3.

### Task 6: Judge scenario parts as written

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [x] Step 6's validator prompt carries a scenario candidate's Trigger, Path,
  and Outcome in place of its claim; a candidate without a scenario still
  carries its claim.
  - **Evidence:** the `feat(pr-review): judge scenario parts as written` commit
    rewrites Step 6's "One validator prompt" bullet to carry the parts in place
    of the claim and the claim only for any other candidate.
- [x] Step 6's scenario bar judges the parts as written in trigger → path →
  outcome order, stops at the first that does not hold, and drops a candidate
  whose stated part is false even when another scenario would reach the same
  fault (B).
  - **Evidence:** the same commit's scenario bullet judges the parts as written
    in that order, stops at the first failing part, and confirms only when every
    part holds as written.
- [x] `pre-commit run validate-agent-files --files .agents/plugins/agentdev/skills/pr-review/SKILL.md`
  passes.
  - **Evidence:** the hook passes on the same commit's `SKILL.md`, as does
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`.

### Task 7: Rerun the validator-only replay

**Files:** Create: `.tmp/replay/` (harness, inputs, and outputs; not committed)

- [x] Rerun Task 5's new arm on F2, F3, F4, F5′, F6, and M1–M3 five times with
  the Task 2–4 and Task 6 edit, the same model, and per-candidate dispatch; Task
  5's current-arm runs stand. Keep every validator's verdict and justification,
  and record per-candidate verdict counts plus every `DROP` with the part it
  names under `## Verification results`.
  - **Evidence:** the `docs(plan): record the parts-as-written replay` commit
    records all 40 runs under `### Validator-only replay, parts as written`; the
    gate fails on F5′, M1, M2, and M3.

### Task 8: Run the full replays

**Files:** Create: `.tmp/replay/` (worktrees at `7e0413d` and `84d4584`)

- [x] \\1 with `codex exec`, `gpt-5.6-sol`, medium model reasoning,
  `REQUESTED REVIEW EFFORT: full`, and the Task 2–4 and Task 6 skill. Keep
  sessions (omit `--ephemeral`) so every pass and validator record survives; see
  [Headless Codex runs](../architecture/codex-headless-runs.md). Score each run
  against the spike's known-bug key K1–K6 and record the table under
  `## Verification results`.
  - **Evidence:** the `docs(plan): record the full replays` commit scores all
    four runs under `### Full replays`: both #199 runs validate K1 and both #203
    runs validate K2–K6.
- [x] Each unmatched correctness finding is marked real or noise by the
  merged-fix rule in `## Approach`, and by the maintainer where no merged fix
  matches. Closed by: the maintainer.
  - **Evidence:** the maintainer judged both `devcontainer-init.sh:35` findings
    real and the `seed-agent-auth.sh:13` finding the F5 fault with an overstated
    outcome, recorded under `### Full replays` in the
    `docs(plan): record the maintainer's full-replay judgments` commit.

### Task 9: Record the decision

**Files:** Create:
`docs/knowledge/data/architecture/pr-review-scenario-validation.md` Modify:
`docs/knowledge/data/architecture.md`

- [ ] File the outcome against `## Verification` as a decision linking
  [PR review correctness bar](../architecture/pr-review-correctness-bar.md). It
  records the shipped bar, A, B, and C with the rejected alternatives; the
  maintainer's decision to ship with the M1–M3 controls failing, because the
  validator judges the fault rather than each stated part; the exclusion of
  permission findings from evaluation; and that the current arm's bar
  (`pr-review/SKILL.md` at `main`) confirmed F1 and F5 in every validator-only
  run. Link it from `data/architecture.md`.

## Spec changes

None — no behavioral change to any `data/spec/` contract.
`data/spec/ai-review-gate` governs whether a review is present and whether the
responder may act; this plan changes only `pr-review`'s internal finding and
validation policy, which no `data/spec/` document specifies.

## Verification

The change ships when all of the following hold:

- **Validator-only replay, new arm (Task 7):** F2, F3, and F4 are confirmed in
  5/5 runs; F6 is confirmed in no more runs than under the current arm; and the
  three-part splits of F1 and F5 each have an empty Outcome.
- **Full replays:** both #199 runs validate K1; both #203 runs validate K4 and
  every one of K2, K3, K5, and K6; and each run has at most one unmatched
  correctness finding the maintainer judges noise. Compliance and
  durable-knowledge noise is excluded, as it has independent owners (see
  [PR review correctness bar](../architecture/pr-review-correctness-bar.md)).
- Every new-arm and full-replay `DROP` of a correctness candidate names a part.

By the maintainer's decision, two checks do not gate shipping:

- **Permission findings are excluded from evaluation:** F5′ and the
  `seed-agent-auth.sh:13` full-replay finding. Whether a loose-mode credential
  is exposed depends on directory modes set by another script, and validators do
  not resolve that consistently.
- **The M1–M3 negative controls are recorded, not gating:** validators judge
  whether the fault is real rather than whether each stated part holds (see
  `### Validator-only replay, parts as written`).

Mechanical checks:
`pre-commit run validate-agent-files --files .agents/plugins/agentdev/skills/pr-review/SKILL.md`
passes; the architecture doc is linked from `data/architecture.md`;
`iwe normalize` and `iwe schema validate` pass.

## Verification results

### Validator-only replay

Each validator ran as one `codex exec` with `gpt-5.6-terra`, medium model
reasoning, and a read-only sandbox, at the candidate's head commit. Its prompt
carries exactly the fields and bar the arm's Step 6 lists; the new arm's prompt
also says where to read the PR title and description, as the `eb3bc12` Step 6
edit requires. The three-part splits of F1 and F5 each have an empty Outcome, so
both are discarded at Step 5 and do not run in the new arm.

| ID  | Current arm `CONFIRM` | New arm `CONFIRM` | New arm `DROP`            | Gate                    |
| --- | --------------------- | ----------------- | ------------------------- | ----------------------- |
| F1  | 5/5                   | —                 | —                         | Discarded at Step 5     |
| F2  | 5/5                   | 5/5               | 0                         | Holds                   |
| F3  | 5/5                   | 5/5               | 0                         | Holds                   |
| F4  | 5/5                   | 5/5               | 0                         | Holds                   |
| F5  | 5/5                   | —                 | —                         | Discarded at Step 5     |
| F5′ | —                     | 3/5               | 2 (`outcome`)             | Fails                   |
| F6  | 5/5                   | 5/5               | 0                         | Holds                   |
| M1  | —                     | 0/5               | 5 (4 `path`, 1 `trigger`) | Fails: wrong part named |
| M2  | —                     | 5/5               | 0                         | Fails                   |
| M3  | —                     | 5/5               | 0                         | Fails                   |

New-arm drops:

- **F5′ (2):** `outcome` — `postCreateCommand.sh` sets the credential parent
  directories to `0700` before seeding, so a loose-mode credential is not
  readable beyond its owner.
- **M1 (5):** four name `path` and one names `trigger`, all on the ground that
  `sha256sum` exists on a GNU coreutils host.

The current arm confirms F1 and F5 in 5/5 runs each. Validated in isolation,
today's bar does not drop a real finding for lack of an outcome, so this replay
does not support the hypothesis in `## Context`. Every M2 and M3 justification
re-derives the candidate's unchanged claim and never tests the broken part: the
validator judges the claim, not the scenario it is handed.

### Validator-only replay, parts as written

Task 7 reran the new arm under the Task 6 bar with the same model, reasoning,
sandbox, and dispatch; a scenario candidate's prompt carries its three parts and
no claim. F6's prompt is unchanged from Task 5.

| ID  | `CONFIRM` | `DROP`                                 | Expected                 | Gate                    |
| --- | --------- | -------------------------------------- | ------------------------ | ----------------------- |
| F2  | 5/5       | 0                                      | `CONFIRM` 5/5            | Holds                   |
| F3  | 5/5       | 0                                      | `CONFIRM` 5/5            | Holds                   |
| F4  | 5/5       | 0                                      | `CONFIRM` 5/5            | Holds                   |
| F5′ | 3/5       | 2 (`outcome`)                          | `DROP: outcome` 5/5      | Fails                   |
| F6  | 5/5       | 0                                      | No more than current 5/5 | Holds                   |
| M1  | 0/5       | 5 (3 `path`, 1 `trigger`, 1 `outcome`) | `DROP: trigger` 5/5      | Fails: wrong part named |
| M2  | 1/5       | 4 (`path`)                             | `DROP: path` 5/5         | Fails                   |
| M3  | 5/5       | 0                                      | `DROP: outcome` 5/5      | Fails                   |

Every drop names a part. Without the claim, M2 drops on its path in four of five
runs. The confirms that remain re-derive the fault from the other parts: each M3
confirm reads the race and the PR description's broken serialization promise
from the Trigger and Path and never tests the stated Outcome, and the M2 and F5′
confirms reach the fault through the actual line order and file mode. M1's drops
agree that `sha256sum` exists on the stated host but split on which part that
falsifies.

### Full replays

Each run used `codex exec` with `gpt-5.6-sol`, medium model reasoning,
`REQUESTED REVIEW EFFORT: full`, full Codex access, and the Task 2–4 and Task 6
skill; a run interrupted by a usage limit resumed in its own session. Session
records keep every pass and validator, with validators on `gpt-5.6-terra`.

| Run    | Candidates | Validated | Known-key matches  | Unmatched correctness                              |
| ------ | ---------- | --------- | ------------------ | -------------------------------------------------- |
| #199 1 | 19         | 9         | K1                 | None                                               |
| #199 2 | 8          | 5         | K1                 | None                                               |
| #203 1 | 23         | 11        | K2, K3, K4, K5, K6 | `devcontainer-init.sh:35`; `seed-agent-auth.sh:13` |
| #203 2 | 42         | 34        | K2, K3, K4, K5, K6 | `devcontainer-init.sh:35`                          |

As in the spike's scoring, a K3 finding naming the missing per-start consumer
also covers K6, and K5 is matched by its launcher fallback at
`claude-remote-control-start.sh:12`. No correctness candidate was dropped. The
maintainer judged the unmatched findings:

- **`devcontainer-init.sh:35` (#203 1 and 2): real.** `a5bf422` adds the
  `shasum` fallback in `workspace-seed-key.sh:5-8`.
- **`seed-agent-auth.sh:13` (#203 1): real, with an overstated outcome.** It is
  the F5 fault, which `a5bf422` repairs, but its stated outcome — the credential
  readable by other users — is F5′'s, and `postCreateCommand.sh:71` prevents it.
  The validator confirmed an Outcome that is false as written.

None is noise, so the full-replay criteria in `## Verification` hold.

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
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:49` — read beyond the diff
  at the head commit
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:57` — reachable-scenario
  condition
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:65` — three-part scenario:
  Trigger, Path, Outcome
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:109` — validation row of
  the slot matrix
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:126` — Step 4 pass
  dispatch and output shape
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:135` — Step 5 discard of
  incomplete scenarios, merge, and deduplicate
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:137` — the single
  validator prompt
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:138` — the validator
  re-derives the claim; bar by candidate shape
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:139` — part-by-part
  scenario bar
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:141` — stated intent is
  evidence, not a verdict
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:142` — "Never argue the
  verdict in the prompt"
- `docs/knowledge/data/architecture/pr-review-effort-tiers.md:98` — "Validation
  runs light at every effort level"
- `7e0413d:.github/workflows/renovate.yml:46` — comment presenting the
  concurrency split as deliberate (K1)
- `84d4584:.devcontainer/scripts/postCreateCommand.sh:71` — `chmod 700` on both
  credential parent directories, before `:72` runs `seed-agent-auth.sh` (F5′)
- `84d4584:.devcontainer/scripts/seed-agent-auth.sh:13` — early return with no
  seed, before the `chmod 600 "$target"` at `:25` (F5, F5′)
