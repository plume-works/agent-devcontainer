---
type: bug
description: The reviewer declines a stated user directive far more often on the wake harness's negative control than on the wake check itself, on an identically scripted exchange, with no mechanism identified.
generated:
  by: claude-code/opus-5
  at: 2026-09-09T00:00:00Z
sources:
- resource: https://github.com/plume-works/agent-self-improvement
  title: agent-self-improvement at e94031a, spec 0005
- resource: .agents/plugins/self-improve/tests/smoke/test_wake_pty.py
---

# Reviewer decline asymmetry

## Symptom

The reviewer refuses a stated, unambiguous user directive — "always use
`make test` in this repo, not pytest directly" — which is the single clearest
case the plugin exists to catch. It does so far more often on the wake harness's
negative control than on the wake check, though only the wake mechanism differs
between them, and it differs *after* the review.

Nothing is broken by it. A review that stores no candidate leaves the harness
nothing to watch for, so the check skips with its journalled reason rather than
failing. The cost is observations, and confidence in any decline-rate number: a
claim about the reviewer's decline rate has to say which check produced it.

## Reproduction

`make wake` drives two live checks from an identical script. The ten-run loop of
2026-08-02, twenty reviews:

|                      | proposed | declined |
| -------------------- | -------- | -------- |
| the wake check       | 9        | 1        |
| the negative control | 6        | 4        |

Four of the five declines were `transient_state`, the fifth
`one_off_instruction`. With the three earlier live runs, the control has
declined seven times against the wake check's once.

Offline replay does not reproduce it: a reconstructed bundle replayed through
the real reviewer declined 3 times in 101, against 5 in 20 live.

## Root cause

Unresolved; no mechanism identified. Two hypotheses are eliminated:

- **The gate is not the discriminator.** All twenty reviews journalled
  `signal: explicit_retention` — both checks, declines and proposals alike. The
  gate reached the same conclusion by the same route every time.
- **The check's own name, which the bundle carries, is not the discriminator.**
  `candidate_owners` entries hold absolute paths containing the check name, so
  every control bundle tells the reviewer *fails*, *does not arrive*. Tested
  with two bundles identical in every other byte, fifteen reviews each: no
  declines either way.

Not eliminated: the bundle may differ in a way not yet reconstructed
(`last_assistant_message` is fresh model prose each run, and `events` may differ
if the sessions do different work — neither is compared between checks, because
the bundle is assembled in memory and never stored); ordering or environment,
the control running second in the same pytest process; or chance, seven against
one being suggestive rather than conclusive over thirteen paired runs.

The offline-replay result is the most consequential, because it invalidates the
cheap instrument: any prompt change measured by replay has not been measured
against the case that actually declines.

## Fix

Not fixed, and not scheduled. Closing it means one of:

1. a mechanism identified and demonstrated — a named difference between the two
   checks' bundles or environments, shown to change the decline rate when
   removed;
2. a measurement large enough to attribute the split to the reviewer's own
   nondeterminism, with the per-check rates stated; or
3. a recorded decision that the question is not worth the model usage, leaving
   the harness's skip behavior as the standing mitigation.

Option 3 is legitimate and should not be reached for last.

Settling it by diffing two runs will not work: the question is a difference in
*rates*, and the fields varying run-to-run within one check — model prose above
all — differ between checks too, for reasons that mean nothing. It needs shape
descriptors aggregated across many runs, grouped by check and outcome, which is
[Plugin execution tracing](../someday/self-improve-execution-tracing.md). That
proposal deliberately does not schedule the slices aimed at this question: the
two available hypotheses are spent and a third has not been proposed, and
building the instrument before naming the question is what these two documents
exist to avoid.

The cheaper alternative, if the answer stops mattering, is to measure the rate
honestly per check over enough runs to call it chance or not — roughly forty
minutes of model usage.

## Key references

Verified anchor points (line numbers as of 2026-09-09):

- `.agents/plugins/self-improve/tests/smoke/test_wake_pty.py:407` — the wake
  check
- `.agents/plugins/self-improve/tests/smoke/test_wake_pty.py:512` — the negative
  control, which discards the hook's exit code
- `.agents/plugins/self-improve/selfimprove/gate.py` — the gate that journalled
  `explicit_retention` identically for both
