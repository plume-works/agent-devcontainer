---
type: someday
description: An opt-in trace inside the plugin recording what each hook decided and why, keeping the evidence bundle as a keyed shape rather than its content.
generated:
  by: claude-code/opus-5
  at: 2026-09-09T00:00:00Z
sources:
- resource: https://github.com/plume-works/agent-self-improvement
  title: agent-self-improvement at e94031a, spec 0004
---

# Self-improve execution tracing

An opt-in facility inside the plugin recording what each hook decided and why,
so a live run can be analysed afterwards. Off by default; its acceptance gate is
that the default path stores nothing the
[privacy rules](../spec/self-improve-learning-loop.md) forbid.

The plugin currently keeps almost nothing about a review that worked as
designed. After a decline the state directory holds a counter and a journalled
outcome class — enough to know a decline happened, not enough to ask why. That
is a diagnosis problem for anything that behaves differently live than offline,
and it is the reason
[Reviewer decline asymmetry](../bugs/self-improve-reviewer-decline-asymmetry.md)
cannot currently be explained.

## Shape without content

Comparing two runs mechanically needs the evidence bundle; the privacy rules
forbid storing it. The resolution is to record its **shape**: enough structure
to compare two bundles for equality and see where they differ, with nothing
recoverable of what they contain.

Per key: the JSON type (a key present with a `null` value and a key absent stay
different facts), element counts, string lengths, a histogram over the closed
`kind` vocabulary for the events list, and a keyed digest for free text. The
rule for what gets a digest is the rule for what gets a bare count — values from
closed vocabularies are recorded as themselves, free text only as a length and a
digest.

The digest must be keyed, and the key local: a plain `sha256` of a short
free-text string is not a redaction, because the candidate space in a scripted
harness run is small enough to enumerate and anyone holding the trace could
confirm a guess.

`candidate_owners` earns a per-entry descriptor rather than a bare count: **a
shape that cannot represent a difference cannot be used to look for one**, so
the fields most likely to carry a systematic difference are the ones that must
not be flattened. `scope`, `kind`, and `exists` are closed vocabularies and
`bytes` and `headings_n` are counts; the paths themselves stay out at every
level.

## Slices

T1 through T3 are worth building for their own sake, not as scaffolding for the
investigation:

- **T1, the writer** — levels, identifiers, record schema, size cap, the
  swallow-everything contract, rotation, instrumenting hook invocation only.
- **T2, decisions** — capture, gate, orchestration, and the wake signal.
  Justified independently: it reduces a `Stop`-hook diagnosis from a live run
  and a pty transcript to a single trace line.
- **T3, the reviewer** — invocation timing, envelope usage metadata, and
  decision records, which adds cost reporting no target has today.
- **T4, shape** — the descriptor, the per-entry form, the keyed digest.
- **T5, the reader** — `si trace show|turns|tabulate|diff|verify`.
- **T6, harness** — Makefile variables and a shared clock in the pty harness.
- **T7, content mode** — last on purpose: the only part that can store a prompt,
  and it should land against a suite that already proves the default path does
  not.

## Why T4 onward stays behind a named question

T4 answers nothing on its own — it records a shape no tool can yet read, so the
smallest configuration producing an answer about the asymmetry is T1 + T4 + T5 +
T6, and that answer may still be "the shapes are identical".

It should be scheduled against a *named* hypothesis that a shape difference
would confirm or kill. The two hypotheses that were available are spent, and a
third has not been proposed. Inventing structure in the hope a question forms
around it is how a tracing facility turns into a second product.

## What this would not answer

It makes the asymmetry measurable; it does not explain it. If the two bundles
turn out identical in shape, the difference is in content the trace deliberately
does not keep — and the obvious next step, content mode on a synthetic run, is
one the replay evidence already argues against: a reconstructed bundle declined
3 times in 101 against 5 in 20 live, so a facility capturing the bundle more
faithfully may capture the same non-event more faithfully.

It also does not address the reviewer's own nondeterminism. Two identical
bundles may receive different decisions; the honest response to that is a
decline rate measured over repeated runs, not a trace.
