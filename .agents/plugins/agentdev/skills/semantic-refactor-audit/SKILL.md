---
name: semantic-refactor-audit
description: Prove that a behavior-preserving change actually preserved behavior, by capturing a ground-truth baseline before editing and comparing it afterwards. Use when a rewrite must not change meaning and no test covers it — rewording instructions or documentation, replacing links with prose, migrating configuration, renaming across a tree, or any mechanical refactor claimed to be semantics-free. Use it especially when a change looks correct in the environment you are running in but could behave differently in another checkout, container, or downstream consumer. Not for reviewing newly written logic, which belongs to /agentdev:pr-review, and not for formatting or lint fixes, which belong to /agentdev:local-reformat.
---

# Semantic Refactor Audit

A refactor that changes wording rather than code has no failing test to catch a
mistake. Reviewing the diff proves the text changed; it does not prove the
meaning survived. This skill produces evidence instead: a baseline captured
before the edit, an identical capture afterwards, and a comparison against
criteria fixed in advance.

Two failure modes motivate the procedure. A rewrite can silently **drop a rule**
that no longer has a home. And a baseline captured in the wrong environment can
**prove nothing** — if the current environment already masks the defect, the
before and after captures look identical and the audit is theater.

## Workflow

### 1. State the invariant and the permitted deltas

Write down, before editing:

- **The invariant** — exactly what must hold identically after the change.
- **The permitted deltas** — every intended semantic change, enumerated. Anything
  else that moves is a defect, not an accepted difference.

Enumerating deltas in advance is what makes the comparison decidable. Without it
every difference gets rationalized after the fact.

### 2. Choose contexts that can expose the failure

This is the step most often skipped, and skipping it invalidates everything
downstream. Ask: _in which environment does the suspected defect actually
appear?_ If the answer is not the one you are sitting in, a single-context audit
cannot detect it.

Construct the second context so the failure is reachable — a copy of the subtree
in isolation, a different working directory, a checkout without the surrounding
repository, a consumer's layout. Verify the isolation is real before trusting it
(confirm the file you expect to be absent is actually absent).

### 3. Capture the baseline — before any edit

A baseline captured after editing proves nothing. Capture along two independent
axes and keep them separate:

| Axis                   | Produced by                                   | Answers                                                                                       |
| ---------------------- | --------------------------------------------- | --------------------------------------------------------------------------------------------- |
| **Ground truth**       | A script or command with no model in the loop | What is objectively true — does this path resolve, what does this command output, what exists |
| **Semantic read-back** | A cheap subagent reading the artifact         | What the text tells a reader to do                                                            |

Never let the semantic axis establish a fact the deterministic axis could
establish. See [Running the probes](#running-the-probes).

Write every capture to a file under `./.tmp/<audit-name>/before/`. The
comparison must be a real diff of stored artifacts, never a recollection of what
an earlier step reported.

### 4. Check the control before proceeding

The `before` capture **must exhibit the failure** you are fixing. If it comes
back clean, one of two things is true: the exposing context is wrong, or the
premise is wrong and there is nothing to fix.

Stop and resolve that. Do not edit on the assumption that the defect is there.

### 5. Make the change

### 6. Re-capture and compare

Re-run both axes into `./.tmp/<audit-name>/after/` using **identical** probe
prompts and commands — vary only paths. Then judge:

- **Invariant held** — the semantic read-back for the unchanged context matches,
  modulo the wording you deliberately changed.
- **Defect fixed** — the deterministic axis no longer shows the failure in the
  exposing context.
- **Only permitted deltas** — every difference appears on the list from step 1.

For "no rule was lost", compare against the **real diff**, not the subagent
summaries. The diff is ground truth about what changed; the probes only tell you
how a reader interprets it.

## Running the probes

Use a cheap model. The semantic read-back is a reading-comprehension task, not a
reasoning task, and you will run it once per artifact per phase.

Give every probe the same prompt, and demand reported text rather than inferred
intent:

- Ask what the document _says_, explicitly forbidding what the model thinks it
  intends.
- Ask for concrete imposed actions and rules as a bounded list, so two phases
  produce comparable output.
- Forbid following references out of the artifact, which otherwise pulls in
  context that differs between phases and pollutes the comparison.
- Constrain writes to one report path, and state that nothing else may be
  created, edited, or deleted.

### Do not trust a probe's factual claims

Subagents misreport deterministic facts at a rate that will corrupt an audit —
in the worked example, 3 of 14 reports asserted path resolutions that were
false, in both directions (claiming a missing file resolved, and claiming a
present file dangled). Any claim of the form "this exists", "this resolves to
X", or "this command outputs Y" must come from the deterministic axis.

When a probe contradicts another probe, or contradicts your expectation, resolve
it with a command rather than a third probe.

## Definition of done

- The invariant and permitted deltas were written down before the first edit.
- The `before` capture demonstrably exhibited the failure.
- Both phases used identical probes and commands, stored as files.
- Every difference between phases is either the invariant holding or a delta
  from the list; none was rationalized after the fact.
- Every factual claim in the conclusion traces to a deterministic check.

For a complete worked audit — including the context design and the probe
prompt — read [worked-example.md](references/worked-example.md).
