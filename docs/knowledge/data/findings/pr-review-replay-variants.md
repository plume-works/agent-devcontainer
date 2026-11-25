---
type: finding
description: Offline replays of twelve pr-review variants and one outside baseline on six real pull request cases, three runs each — the claim-by-claim metadata check stops stale descriptions without false stops, a second large-model correctness pass finds the hardest known bug far more often, and the validator drops most ADR-rule findings as borderline; whole-review replays at three runs cannot separate the rest from run-to-run variation.
sources:
- resource: docs/research/pr-review-eval/README.md
- resource: docs/research/pr-review-eval/results.md
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .agents/plugins/agentdev/rules/review.md
---

# What pr-review variants find on replayed pull requests

## Question

Which changes to the `pr-review` skill — how a finding is rated, extra review
rules, the metadata check, and how many passes run on which model — make it post
the known defects of a pull request more reliably, without adding unstable
comments?

## Setup

The corpus, the harness and every run record are in
[docs/research/pr-review-eval](../../../research/pr-review-eval/README.md).

- **Harness.** `tools/run.sh` replays one review offline in a checkout of the
  case's head commit. The orchestrator is `claude -p --model opus`, which ran
  `claude-opus-5-5` on Claude Code 2.1.325. No effort level was set, so every
  run used the CLI default. `gh` is a stub that fails; the review writes what it
  would post to `out/review.json` and every pass candidate with its validator
  verdict to `out/candidates.json`. Nothing was posted.
- **Subagent models.** Each variant's skill decides which model each subagent
  gets. The `large` size ran `claude-opus-5-5` and the `light` size ran
  `claude-sonnet-5-5` in every run; each run record lists the model each
  subagent actually ran.
- **Runs.** Three replays per variant and case: 138 runs over 13 arms.
- **Scoring.** Each case's `case.json` lists the expected findings and a pattern
  for each; `tools/report.py` scores every run as posted, dropped by the
  validator, not raised, or stopped at the metadata check. The patterns were
  audited by hand against every posted comment they match.

### Cases

All six cases are pull requests of `plume-works/images`.

| Case          | PR  | Base       | Head       | Description                                          | Expected                                                                                                                                                         |
| ------------- | --- | ---------- | ---------- | ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `images70`    | #70 | `1247ef73` | `94d64a65` | As published                                         | The registry build cache stops apt packages from floating, against ADR 0013                                                                                      |
| `images71`    | #71 | `1247ef73` | `726ba5a9` | As published                                         | The defaults unit fails on a dangling `~/.claude/settings.json` symlink                                                                                          |
| `images75`    | #75 | `8640351b` | `a94298e0` | Stale: describes the previous commit                 | The metadata check stops the review; the answered midnight-snapshot thread is not raised again                                                                   |
| `images75fix` | #75 | `8640351b` | `a94298e0` | Corrected to match the head                          | The daily window does not limit bumps to one a day; ADR 0022 implementation details; no smoke test; plain-HTTP InRelease; ADR 0019 claim; stale ADR 0022 pointer |
| `images83`    | #83 | `8640351b` | `018feca9` | Stale: #75's later description on #75's first commit | The metadata check stops the review                                                                                                                              |
| `images83fix` | #83 | `8640351b` | `018feca9` | #75's original description, written for this commit  | The midnight snapshot pin; plus the `images75fix` findings except the daily window                                                                               |

### Variants

Each variant is the `.agents/plugins/agentdev` tree of one commit; the diff is
that tree against the variant's own base on `main`.

| Id    | Base       | Commit     | Change                                                                                                                              | Diff                                                      |
| ----- | ---------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| `p1`  | `4a3f6744` | `4a3f6744` | `main` before #966                                                                                                                  |                                                           |
| `p2`  | `4a3f6744` | `70a4623b` | #966: `Confidence: X/10` and `Severity: P1–P3` on every finding                                                                     | [p2](../../../research/pr-review-eval/variants/p2.diff)   |
| `p3`  | `a86256e5` | `457fa0b6` | Validator verdicts `HOLDS P1–P3`, `UNSETTLED` (a Question), `REFUTED`; only P1 blocks                                               | [p3](../../../research/pr-review-eval/variants/p3.diff)   |
| `p4`  | `a86256e5` | `473a2b3d` | `p3` + documented tool behaviour is settled; a broken stated guarantee holds                                                        | [p4](../../../research/pr-review-eval/variants/p4.diff)   |
| `p5`  | `a86256e5` | `ca2bb526` | `p4` + P1 means hit without misuse; passes report every believed issue; claim-by-claim metadata check                               | [p5](../../../research/pr-review-eval/variants/p5.diff)   |
| `p6`  | `445b8cfb` | `bb721232` | `main` + stated-guarantee check, claim-by-claim metadata check, validator drops a scenario only on a contradiction                  | [p6](../../../research/pr-review-eval/variants/p6.diff)   |
| `p7`  | `28b5200c` | `28b5200c` | `main` with the shared review rulebook (#997)                                                                                       |                                                           |
| `p8`  | `28b5200c` | `c96bf967` | `p7` + `p6`'s three rules                                                                                                           | [p8](../../../research/pr-review-eval/variants/p8.diff)   |
| `p9`  | `28b5200c` | `850c6d53` | `p7` + only the claim-by-claim metadata check (merged as #999)                                                                      | [p9](../../../research/pr-review-eval/variants/p9.diff)   |
| `p10` | `28b5200c` | `9f7e9b4e` | `p7` + every correctness pass on `large`, whatever size the review picks                                                            | [p10](../../../research/pr-review-eval/variants/p10.diff) |
| `p11` | `ef9c3baf` | `a0e71b8a` | `main` (with #999) + no light tier and no self-sizing: 2 compliance (`light`), 2 correctness (`large`), durable-knowledge (`large`) | [p11](../../../research/pr-review-eval/variants/p11.diff) |
| `p12` | `ef9c3baf` | `0e3cbd5e` | `p11` with one correctness pass covering obvious bugs, logic, security and tests                                                    | [p12](../../../research/pr-review-eval/variants/p12.diff) |
| `cr`  |            |            | Anthropic's `code-review` plugin 1.0.1                                                                                              |                                                           |

On `p1`–`p10`, how many passes run and on which model is the orchestrator's own
choice from the diff; `p11` and `p12` fix it.

## Measurement

Runs that post the case's main finding, or stop at the metadata check where that
is the expectation, out of three:

| Variant | #70 apt cache | #71 symlink | #75 stale stop | #83 stale stop | #75 daily window | #83 midnight pin | Cost per review |
| ------- | ------------- | ----------- | -------------- | -------------- | ---------------- | ---------------- | --------------- |
| `p1`    | 2/3           | 2/3         | 2/3            | —              | —                | —                | $0.42–2.32      |
| `p2`    | 3/3           | 3/3         | 0/3            | —              | —                | —                | $1.33–3.90      |
| `p3`    | 2/3           | 3/3         | 1/3            | —              | —                | —                | $0.43–2.22      |
| `p4`    | 1/3           | 2/3         | 0/3            | —              | 3/3              | —                | $0.69–2.67      |
| `p5`    | 3/3           | 3/3         | 3/3            | —              | —                | —                | $0.36–1.82      |
| `p6`    | 2/3           | 2/3         | 3/3            | —              | 3/3              | —                | $0.36–2.47      |
| `p7`    | 3/3           | 3/3         | —              | 1/3            | 3/3              | 3/3              | $0.46–3.06      |
| `p8`    | 2/3           | 3/3         | —              | 3/3            | 3/3              | 3/3              | $0.37–3.14      |
| `p9`    | 1/3           | 2/3         | —              | 3/3            | —                | —                | $0.41–2.09      |
| `p10`   | 2/3           | 3/3         | —              | —              | 2/3              | 3/3              | $1.08–2.87      |
| `p11`   | 3/3           | 3/3         | —              | —              | 2/3              | —                | $1.79–2.82      |
| `p12`   | 2/3           | 3/3         | —              | —              | 1/3              | —                | $1.30–2.69      |
| `cr`    | 0/3           | 0/3         | 0/3            | —              | —                | —                | $0.98–1.44      |

A stop costs about $0.40, so a variant's low end is its gate stops.

The main finding against the correctness passes a run dispatched, pooled over
`p1`–`p12` (runs stopped at the metadata check excluded):

| Case             | 1 pass, `light` | 1 pass, `large` | 2 passes, `large` |
| ---------------- | --------------- | --------------- | ----------------- |
| #70 apt cache    | 2/6             | 14/18           | 10/12             |
| #71 symlink      | 5/9             | 21/21           | 6/6               |
| #75 daily window | —               | 2/5             | 15/16             |
| #83 midnight pin | 1/1             | 1/1             | 7/7               |

In the 17 runs with two correctness passes, both passes raised the main bug in
15; in the other 2, both on #75, only one pass did. The plain-HTTP InRelease
finding came only from the security and logic pass.

What happened to each secondary finding of #75 and #83, pooled over the runs
that dispatched passes:

| Finding                         | Posted | Dropped by the validator | Not raised |
| ------------------------------- | ------ | ------------------------ | ---------- |
| ADR 0022 implementation details | 5      | 24                       | 1          |
| Stale ADR 0022 pointer          | 3      | 14                       | 13         |
| No smoke test                   | 14     | 8                        | 8          |
| ADR 0019 claim                  | 13     | 7                        | 10         |
| Plain-HTTP InRelease            | 9      | 0                        | 21         |

The validators' reasons for the ADR drops are the same in every run: the text is
"borderline" or "not clearly a violation", the bar for a candidate with no
scenario. The smoke-test drops call it a hardening suggestion with no wrong
outcome today.

No variant stopped #70 or #71 at the metadata check in any of 78 runs.

## What is known

- **The claim-by-claim metadata check stops a stale description and nothing
  else.** Every variant with it (`p5`, `p6`, `p8`, `p9`) stopped #75 or #83 in 3
  of 3 runs, against 2 of 3 for `p1` on #75 and 1 of 3 for `p7` on #83, with no
  false stop on #70 or #71.
- **A single `light` correctness pass misses the main bug.** It found the #70
  and #71 bugs in 7 of 15 runs; a single `large` pass found them in 35 of 39.
- **Two `large` correctness passes find the #75 daily window; one does not.** 15
  of 16 runs against 2 of 5. It is the only known finding whose detection
  depends on the pass count in this data.
- **The validator drops findings that rest on a rule's wording.** The ADR rule
  findings are raised by most runs and posted by few.
- **Rating schemes move labels, not detection.** `p2`–`p5` posted the #70 and
  #71 bugs about as often as `p1`; they differ in whether the finding is P1, P2,
  a Question or blocking.
- **The outside baseline posts nothing.** `cr` reported no issue in any of its
  nine runs; on #71 one of its passes raised the symlink and dismissed it
  itself.

## Eliminated

- **A run misses the main bug only because it put the correctness pass on
  `light`.** Eliminated for #75: `p10` forced `large` and still missed the daily
  window in 1 of 3 runs, the one run that dispatched a single correctness pass.
- **The second correctness pass only repeats the first.** Eliminated: on #75 it
  caught the daily window when the other pass missed it, and it alone raised the
  plain-HTTP finding.

## Limits

- **Every run replayed the whole review.** A variant that changed one stage
  still ran every other stage, so the compliance passes, the durable-knowledge
  pass and the validator added their own run-to-run variation to the effect
  under test.
- **Arms sit on different `main` bases.** `p1`–`p6` and `p7`–`p10` and
  `p11`–`p12` each sit on a different `main`; only arms in one round share a
  base, except `p6` against `p4`.
- **Three runs per cell.** A 1-of-3 difference is within the spread between runs
  of the same arm.
- **Expected findings were fixed after the runs** and scored by pattern.
- **The effort level was not pinned.**
- **Pass sizing was the orchestrator's choice in `p1`–`p10`**, so the pooled
  pass-count table mixes rule variants.

## Closing

The question settles with replays that isolate one stage, per [the corpus
README](../../../research/pr-review-eval/README.md#measuring-a-change):
correctness-pass candidates before validation, one versus two `large` passes, at
least ten runs per arm on #70, #71, `images75fix` and `images83fix`, on one
`main`, with the effort level pinned; and the validator alone on a fixed set of
the ADR-rule candidates. The finding closes when those decide the correctness
pass count and whether the validator's bar for rule findings changes, each
recorded as a change to `pr-review`. If ten-run replays show no difference
beyond the spread, the closing is that the full pass set stays and the pass
count is not worth more measurement.
