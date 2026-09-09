---
type: someday
description: Adapting Hermes's prompt stack — active correction handling, the fact/procedure split, owner-first routing, a class-level name veto, and negative-learning rules — to the MVP's no-tools reviewer.
generated:
  by: claude-code/opus-5
  at: 2026-09-09T00:00:00Z
sources:
- resource: https://github.com/plume-works/agent-self-improvement
  title: agent-self-improvement at e94031a, spec 0006
- resource: docs/research/case-study/hermes/README.md
---

# Hermes-derived prompt stack for self-improve

The MVP has a strong control plane and a weakly calibrated reasoning layer. The
deterministic gate limits review to a named high-signal event, and the reviewer
prompt then tells the model that discarding is correct "most of the time" — so
the same lesson is screened twice with opposite priors:

``` text
deterministic gate: this turn has a supported learning signal
        |
        v
review prompt: assume there is probably nothing to learn
```

[Reviewer decline asymmetry](../bugs/self-improve-reviewer-decline-asymmetry.md)
records live reviews declining the direct instruction "always use `make test` in
this repo, not pytest directly". This proposal does not claim the prompt causes
that — offline replay does not reproduce the live rate — only that the current
reasoning policy has insufficient observed recall on the clearest positive case.

The research it draws on is
[the Hermes case study](../../research/case-study/hermes/README.md), which is
evidence, not a drop-in runtime dependency.

## What to adopt, adapt, and refuse

- **Adopt** natural correction phrases and frustration as first-class signals;
  users rarely write a formal retention request.
- **Adopt** class-level naming with a veto on PR, error, codename, and task
  names, which prevents narrow skill proliferation.
- **Adopt** the negative-learning rules — environment failures, negative tool
  claims, transient errors, and one-off narratives become stale self-imposed
  constraints — and the refusal of unresolved failures dressed as reliable
  workflows.
- **Adopt** the skill-authoring rubric (trigger, steps, pitfalls, verification)
  into the `improve` skill, beside exact-byte drafting.
- **Adapt** "be active, do not default to nothing" to reviews whose gate already
  named a signal: this plugin has a stronger pre-filter and can calibrate by
  signal type.
- **Adapt** the fact/procedure split to `CLAUDE.md`, rules, and skills, since
  the MVP must not mutate Claude-managed memory and owns no fact store.
- **Adapt** "patch a loaded skill immediately" to one exact proposal: the
  foreground agent recommends and stages; only the authorized mutator writes.
- **Strengthen through architecture** rather than prompt: protected skills are
  off-limits because this reviewer cannot write any skill at all.
- **Do not copy** the memory tool's atomic batch grammar — one candidate, one
  proposal, no batch — nor the mandatory load of every partially relevant skill,
  since a self-improvement plugin does not own Claude's behavior on unrelated
  turns.
- **Defer** support-file mutation. Current staging permits `SKILL.md` but not
  package subfiles or atomic two-file link updates, which is the same gap
  [the unstageable routing option](../bugs/self-improve-unstageable-routing-option.md)
  records; the false capability should leave shipped guidance either way.

## What acceptance would require

Deterministic checks are free and come first: prompt, schema, validator, and
journal agreeing on every discard category; tests observing that the reviewer
has no tools, that proposals stay inert without a literal one-time
authorization, and that support-file paths are rejected while deferred.

Model quality needs opt-in evaluation over synthetic redacted fixtures, one
recorded model/effort pair, at least three repetitions each: explicit retention
and correction recall at least 95%; no unresolved-failure, negative-capability,
environment-state, or inferred-preference fixture producing an accepted
proposal; verified-workaround and confirmed-technique recall at least 85%;
existing-owner cases choosing a compatible owner query and never recommending a
new narrow skill; a valid schema rate of at least 99%; and no increase against
the baseline in negative-fixture acceptance.

Packaged live evidence is required before the prompt may be called improved.
Until that is observed, the current prompt remains the accepted behavior.
