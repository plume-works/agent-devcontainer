---
type: plan
created: 2026-09-29
description: A two-PR Codex spike that tests whether letting pr-review's correctness passes read beyond the diff and flag reachable input- or state-dependent failures finds known bugs without adding noise.
generated:
  by: codex/gpt-6
  at: 2026-10-03T18:07:42Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/199
  title: Run Renovate when a person ticks a dashboard or PR checkbox
- resource: https://github.com/plume-works/agent-devcontainer/pull/203
  title: Seed agent auth, Git identity, and gh credentials into Coder devcontainers
---

# Spike: does a reachable-scenario bar let pr-review find Greptile-class bugs

## Context

Across the twelve most recent human-authored pull requests (#185–#222), Greptile
raised eleven correctness or security findings and the Claude responder five,
with almost no overlap. Every correctness bug Greptile found and the responder
missed depends on an input, a state, or code outside the changed lines: a
concurrency overlap between two triggers, a hook ordering in an unchanged
script, a staged-only change, a custom default branch, a shared checksum.

`pr-review`'s Correctness focus rules exactly those out. It scans "only the diff
itself", flags code that is wrong "regardless of inputs", and does not flag
"issues that depend on specific inputs or state". On #199 the responder approved
and called the concurrency change safe while Greptile reported the overlap as
P1.

**Hypothesis:** those three rules suppress Greptile-class bugs when Codex
follows the skill. Replacing them with a reachable-scenario bar and letting the
correctness passes read the code around the diff finds those bugs without losing
the baseline arm's findings or adding noise.

## Approach

Replay two pull requests at the head each bot first reviewed, once with the
current skill and twice with a variant, and score the validated findings against
a key of known bugs. Every measured run uses `codex exec` with `gpt-5.6-sol`,
medium model reasoning, and `REQUESTED REVIEW EFFORT: full`; the skill's Codex
effort matrix still assigns each review pass its specified model. The spike
ships nothing: runs happen in throwaway worktrees under `.tmp/spike/`, the
variant is an edited copy of `SKILL.md`, and the result is a recorded decision.

Both arms get their instructions the same way — a prompt naming a `SKILL.md`
path to follow — so plugin loading cannot differ between them. The prompt
overrides the parts of the skill that cannot run against a merged pull request:
Step 1's open-PR gate and Step 3's metadata gate are skipped, the diff comes
from a file, and Steps 7–9 write the validated findings to a JSON file instead
of publishing a review.

The pull requests are #199 (one changed workflow file; one known P1 a previous
responder approved past) and #203 (twelve changed code files; exercises both the
scenario bar and reading beyond the diff, and contains five other known
findings, so the baseline arm establishes which of them this Codex runner
finds). #210 is excluded: its diff, more than twice the size of #203's, costs
the most per run and its many findings dilute the signal.

### Known-bug key

| ID  | PR   | Head      | Location                                                 | Bug                                                                                                     | Found by |
| --- | ---- | --------- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | -------- |
| K1  | #199 | `7e0413d` | `.github/workflows/renovate.yml:48`                      | Split concurrency groups let a checkbox run and a push or scheduled run write the same branches at once | Greptile |
| K2  | #203 | `84d4584` | `.devcontainer/docker-compose.yml:70`                    | Unset `GIT_*` host variables are injected as empty strings, and Git refuses the empty identity          | Both     |
| K3  | #203 | `84d4584` | `.devcontainer/devcontainer-init.sh:36`                  | Every restart rewrites the credential transfer files, and only post-create removes them                 | Both     |
| K4  | #203 | `84d4584` | `.devcontainer/scripts/postStartCommand.sh:12`           | The `gh` credential helper checks login before `setup-keyring.sh` starts the keyring                    | Greptile |
| K5  | #203 | `84d4584` | `docs/knowledge/data/spec/devcontainer-agent-auth.md:32` | The spec says the token is not a substitute; the launcher falls back to it                              | Claude   |
| K6  | #203 | `84d4584` | `docs/knowledge/data/spec/devcontainer-agent-auth.md:71` | A start-time seeding scenario the code performs only at create                                          | Claude   |

`84d4584` is a formatter-only commit on top of `79d848a`, the head Greptile
reviewed, so every #203 bug is present at it.

## Implementation Steps

### Task 1: Prepare the replay inputs

**Files:** Create: `.tmp/spike/pr199/`, `.tmp/spike/pr203/` (worktrees),
`.tmp/spike/pr199.diff`, `.tmp/spike/pr203.diff`

- [x] Add detached worktrees at `7e0413d` and `84d4584`.
  - **Evidence:** `git worktree add --detach` at both heads succeeded; the heads
    are reachable commits in this repository.
- [x] Write each diff from the merge-base with `origin/main`: `77ec374..7e0413d`
  and `3a3201e..84d4584`.
  - **Evidence:** `git merge-base` with `origin/main` returns `77ec374` and
    `3a3201e`; the diffs cover 4 files (+55/−22) and 14 files (+801/−3).

### Task 2: Write the variant skill

**Files:** Create: `.tmp/spike/variant/SKILL.md` (a copy of the current
`pr-review/SKILL.md`)

- [x] Replace the "Scan only the diff itself" bullet: the correctness passes may
  read, at the head commit, the code the changed lines call, are called by, and
  run beside in the same lifecycle or workflow.
  - **Evidence:** the `@@ -49` and `@@ -127` hunks of the variant diff under
    `## Verification results`.
- [x] Replace "definitely produce wrong results regardless of inputs" with a
  reachable-scenario condition: a concrete input or state the code can actually
  receive, and the wrong outcome it produces. Drop "Potential issues that depend
  on specific inputs or state" from the do-not-flag list.
  - **Evidence:** the `@@ -57` and `@@ -63` hunks of the variant diff under
    `## Verification results`.
- [x] Each correctness candidate carries its scenario, and the validator
  confirms the scenario is reachable at the head commit before it confirms the
  finding.
  - **Evidence:** the `@@ -66` and `@@ -138` hunks of the variant diff under
    `## Verification results`.
- [x] Record the variant's diff against the current skill under
  `## Verification results`.
  - **Evidence:** the `### Variant skill` diff under `## Verification results`.

### Task 3: Run the baseline arm

**Files:** Create: `.tmp/spike/results/pr199-baseline-1.json`,
`.tmp/spike/results/pr203-baseline-1.json`

- [x] Overwrite any result produced by a different runner, then run one review
  per pull request from inside that pull request's worktree with `codex exec`,
  `gpt-5.6-sol`, medium model reasoning, `REQUESTED REVIEW EFFORT: full`, and
  the current `pr-review/SKILL.md`.
  - **Evidence:** both baseline outputs passed the runner's JSON shape and
    pinned Codex metadata gate after their serial full-effort runs.

### Task 4: Run the variant arm

**Files:** Create: `.tmp/spike/results/pr199-variant-{1,2}.json`,
`.tmp/spike/results/pr203-variant-{1,2}.json`

- [ ] Run two reviews per pull request with `codex exec`, `gpt-5.6-sol`, medium
  model reasoning, `REQUESTED REVIEW EFFORT: full`, and
  `.tmp/spike/variant/SKILL.md`, with the same prompt as the baseline arm apart
  from the skill path.

### Task 5: Score the runs against the key

- [ ] For each run, record which of K1–K6 its validated findings match, and list
  every finding that matches no key entry, in a table under
  `## Verification results`.

### Task 6: Judge the unmatched findings

- [ ] Each unmatched finding is marked real or noise. Closed by: the maintainer,
  who reviews the unmatched-findings table.

### Task 7: Record the decision

**Files:** Create:
`docs/knowledge/data/architecture/pr-review-correctness-bar.md` Modify:
`docs/knowledge/data/architecture.md`

- [ ] File the outcome against the criteria in `## Verification` as a decision:
  the bar changes (and a follow-up plan changes the shipped skill), the bar
  stays (the rules are not the cause), or validator strictness is the open
  question. Link it from `data/architecture.md`.

## Spec changes

None — no behavioral change. The spike runs a copy of the skill in throwaway
worktrees; the shipped `pr-review` is unchanged.

## Verification

The hypothesis **holds** when, in both variant runs:

- the #199 run's validated findings include K1 and the #203 run's include K4;
- every key entry the #203 baseline run found is still found;
- the maintainer judges at most one unmatched finding per pull request as noise.

It **fails** when neither K1 nor K4 appears in either variant run: the three
rules are not why the responder misses these bugs. A **mixed** result — K1 or K4
found, but with more noise or lost baseline findings — makes validator
strictness the next question, and the shipped skill stays unchanged.

Mechanical checks: all six result files exist and parse as JSON; the scoring
table covers six Codex runs and records `gpt-5.6-sol` with medium model
reasoning for each; the architecture doc is linked from `data/architecture.md`;
`iwe normalize` and `iwe schema validate` pass.

## Verification results

### Variant skill

The variant rewrites three rules the plan names, plus two sentences that restate
the first: the closing "do not flag issues that you cannot validate without
looking at context outside of the git diff" and Step 4's "each pass sees only
the diff". Left in, they would contradict the replacement rule. Diff against
`pr-review/SKILL.md` at `1220f5c`:

``` diff
@@ -49 +49 @@
-- Scan only the diff itself, without pulling in extra context beyond the diff and the PR title/description — do not flag anything you cannot validate from the diff alone
+- Start from the diff, then read at the head commit the code the changed lines call, the code that calls them, and the code that runs beside them in the same lifecycle or workflow (sibling steps, hooks, jobs, and scripts run in the same sequence) — a bug may live in how the changed lines meet that code
@@ -57 +57 @@
-- The code will definitely produce wrong results regardless of inputs (clear, unambiguous logic errors)
+- A reachable scenario produces a wrong outcome: you can name a concrete input or state the code can actually receive at the head commit (an event, an environment value, a run order, a prior state, a concurrent run) and the wrong result, failure, or security exposure it produces
@@ -63 +62,0 @@
-- Potential issues that depend on specific inputs or state
@@ -66 +65 @@
-Flag only significant bugs; ignore nitpicks and likely false positives. Do not flag issues that you cannot validate without looking at context outside of the git diff.
+Flag only significant bugs; ignore nitpicks and likely false positives. Every correctness candidate carries its scenario: the input or state, how the code reaches it, and the wrong outcome. A candidate without a concrete scenario is speculation — do not flag it.
@@ -127 +126 @@
-4. **Run the independent initial-review passes the effort matrix names, in parallel when the environment supports it** — each pass sees only the diff, the PR title, the PR description, and its own focus list; none sees another pass's output. Each pass returns a list of issues, where each issue has a description and the reason it was flagged (for example, "AGENTS.md adherence", "bug", or "security"):
+4. **Run the independent initial-review passes the effort matrix names, in parallel when the environment supports it** — each pass sees the diff, the PR title, the PR description, and its own focus list, and the correctness passes may also read the head commit as their focus list allows; none sees another pass's output. Each pass returns a list of issues, where each issue has a description and the reason it was flagged (for example, "AGENTS.md adherence", "bug", or "security"):
@@ -138,2 +137,2 @@
-   - **One validator prompt, the same at every effort level.** It carries the candidate's file and line, the added text quoted, the claim made against it, the full text of any rule that claim invokes, where to read the diff, and that the working tree is already at the head commit so files can be read for ground truth. It never names which pass raised a candidate.
-   - **Make the validator re-derive the claim** from the files rather than trust the candidate's assertion of it, and tell it to drop anything ambiguous, trivial, or not clearly a violation. Ask for `CONFIRM` or `DROP` per candidate with a one-sentence justification.
+   - **One validator prompt, the same at every effort level.** It carries the candidate's file and line, the added text quoted, the claim made against it, the scenario a correctness candidate names, the full text of any rule that claim invokes, where to read the diff, and that the working tree is already at the head commit so files can be read for ground truth. It never names which pass raised a candidate.
+   - **Make the validator re-derive the claim** from the files rather than trust the candidate's assertion of it, and tell it to drop anything ambiguous, trivial, or not clearly a violation. For a correctness candidate, the validator confirms that its scenario is reachable at the head commit — the input or state can actually occur and the code path actually leads to the wrong outcome — before it confirms the finding; an unreachable scenario is a `DROP`. Ask for `CONFIRM` or `DROP` per candidate with a one-sentence justification.
```

## Out of scope

- Changing the shipped `pr-review` skill; a holding result gets its own plan.
- Replaying #210 or the other pull requests in the analysis.
- Light-effort runs.
- A permanent replay mode in `pr-review`.
- Configuring Greptile.
- Comparing Claude and Codex, or using a Claude-generated result in the scoring
  table.

## Key references

Verified anchor points (line numbers as of 2026-10-03):

- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:49` — "Scan only the diff
  itself" correctness rule
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:57` — "definitely produce
  wrong results regardless of inputs"
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:63` — "Potential issues
  that depend on specific inputs or state"
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:129` — correctness pass
  dispatch
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:138` — the single
  validator prompt
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:139` — the validator
  re-derives the claim
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:96` — Codex model mapping
  for large and light review slots
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:103` — full-effort slot
  matrix
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:133` — Codex pass dispatch
  behavior
- `7e0413d:.github/workflows/renovate.yml:48` — `concurrency:` split by event
  (K1)
- `84d4584:.devcontainer/docker-compose.yml:70` —
  `GIT_AUTHOR_NAME: ${GIT_AUTHOR_NAME:-}` (K2)
- `84d4584:.devcontainer/devcontainer-init.sh:36` — `AGENTDEV_AUTH_SEED_DIR`
  transfer directory (K3)
- `84d4584:.devcontainer/scripts/postStartCommand.sh:12` —
  `setup-gh-credential-helper.sh` before `setup-keyring.sh` at `:14` (K4)
- `84d4584:docs/knowledge/data/spec/devcontainer-agent-auth.md:32` —
  "`CLAUDE_CODE_OAUTH_TOKEN` is not a substitute" (K5)
- `84d4584:.devcontainer/scripts/claude-remote-control-start.sh:12` — token
  fallback branch (K5)
- `84d4584:docs/knowledge/data/spec/devcontainer-agent-auth.md:71` —
  later-container-start scenario (K6)
