---
type: architecture
description: Replace the PR template's How to Test with a Verification section of closed items carrying evidence and a Reviewer Handoff section of open items naming who can close them.
generated:
  by: codex
  at: 2026-08-31T17:34:08Z
sources:
- resource: .github/pull_request_template.md
- resource: .agents/plugins/agentdev/skills/code-review-standards/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-gen-description/SKILL.md
---

# PR verification sections

## Decision

Replace the pull request template's single `## How to Test` with two sections
distinguished by tense, applying
[evidence and outstanding work](../concept/evidence-and-outstanding-work.md):

``` markdown
## Verification

- [x] Symlink cleanup guard, all six cases
  - **Evidence:** ran by hand against stale, `ws-project`, `/tmp`, in-tree,
    real-directory, and dangling targets; kept/removed as specified.

## Reviewer Handoff

- [ ] Container rebuild resolves `ruff` under `/uv/venvs/ws-project`
  - **Closed by:** a human with the devcontainer. Terminal PATH injection is
    driven by `python.defaultInterpreterPath`; most likely to regress quietly.
```

`## Verification` holds only closed items, each `- [x]` with an `**Evidence:**`
child naming what closed it. `## Reviewer Handoff` holds only open items, each
`- [ ]` with a `**Closed by:**` child naming the party who can close it. Neither
section may contain the other's box type — that is the whole point of the split.

Two filters decide what is written at all:

1. **Omit what an automated check covers.** No linter runs, no formatter passes,
   no image builds, no test suites that CI executes on the branch, and no "CI is
   green" line — the checks report that themselves, continuously, and a sentence
   claiming it goes stale the moment someone pushes.
2. **Reference, never restate, what another document owns.** A plan with
   per-task evidence is the record; the PR body links to it under `## Related`
   and does not copy its verification list.

What remains is the residue: things no automated check covers and no other
document records. In practice this is manual verification with no test, and
environment-dependent behavior CI cannot reach. Both sections are frequently
short, and `## Verification` is frequently empty — that is the intended outcome,
not a defect. An empty `## Verification` under a green CI run means coverage is
good.

## Why

The concrete failure is the `## How to Test` section of [pull request
61](https://github.com/plume-works/agent-devcontainer/pull/61): six numbered
items spanning three moods — a state to observe ("CI on this PR is green"),
commands already run in the past tense, and instructions addressed to the reader
— under one heading and one continuous numbering, as though they were one kind
of thing. Four of the six restated work CI already performs.

This is the pull-request-shaped instance of
[plan checkbox over-claiming](../bugs/plan-checkbox-over-claiming.md), whose
plan states the governing rule for plan tasks: *a task whose evidence is
external — a CI run, a deploy, a review — always stands alone, because the
session writing the code cannot close it.* Item 1 of that PR was exactly such a
claim. The rule was already written; it had simply never been applied outside
`data/plans/`.

Automated review makes the split load-bearing rather than stylistic. Every PR in
this project is reviewed by an agent, and an agent will not rebuild a
devcontainer. Under one heading, an unperformable instruction is either skipped
in silence or absorbed into a "verified" verdict because the section was present
and well-formed. `**Closed by:**` naming a party the reviewer is not is the
field that makes the item survive review as an open item.

## Alternatives rejected

**Rename `## How to Test` to `## How to Verify`.** Accurate as far as it goes —
nothing in the section is a test, and an observation of CI state is not a
verification step either. But it leaves past and future in one list, which is
the actual defect. It is the change that reads as progress while fixing nothing.

**Split into two sections without per-item evidence.** Prose bullets under two
headings, the boundary carrying the meaning. This captures most of the value at
a fraction of the ceremony, and was the leading candidate. Rejected because it
does not match the vocabulary the checkbox plan establishes for the same idea in
`data/plans/`, and because a prose bullet under `## Verification` is again a
line whose closure cannot be told from its text — the evidence child is what
makes a tick expensive enough to be honest. Two vocabularies for one rule is
worse than one heavier vocabulary.

**Delete `.github/pull_request_template.md` outright.** Rejected because
`generate-pr-description` fills the consumer's template when one exists.
Deleting this repository's template would remove project-owned PR-body wording
and force the built-in fallback section list instead.

**Treat this repository's template as the portable fallback.** Rejected because
a consumer's PR template is consumer-owned. A repository with no template gets
the skill's built-in section list rather than this repository's template
silently standing in.

**Have the reviewing agent write the handoff instead of the author.** Arguably
better-informed: a reviewer knows what it was and was not able to close, where
the author only guesses. Rejected for now because the handoff must exist
*before* review to be useful to it — its purpose is telling the reviewer what to
do — and because it would put PR body content outside the author's control. Left
open as a question: whether the reviewing agent should *append* what it could
not close, turning the section into a dialogue.

## Consequences

- A mechanical gate is not available. The plan-checkbox format is enforced by a
  pytest over `docs/knowledge/data/plans/`; PR bodies live on GitHub, are not in
  the graph, and no equivalent check can reach them. This format is enforced by
  the skills that write it and the reviewers that read it — weaker enforcement
  than the plan case, and the reason the format must stay simple enough to hold
  by hand.
- Writing the sections correctly requires knowing what CI covers. An author
  without that knowledge will duplicate (harmless, noisy) or omit wrongly
  (dangerous — a genuinely manual check silently dropped). The skills must
  therefore instruct reading the workflows, not merely applying the filters.
- **`generate-pr-description` fills the consumer's template.** A repository with
  no template gets the skill's built-in section list rather than this
  repository's template silently standing in.
- This repository's pull request template remains project-owned structure.
  Portable generation behavior belongs in
  `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md`;
  project-specific PR-body wording stays in `.github/pull_request_template.md`.
- Two call sites remain in the portable `agentdev` plugin and must change
  together when the generated PR-body contract changes:
  `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md` (template
  discovery, fallback sections, testing-strategy prompt, edge cases, and related
  resources) and
  `.agents/plugins/agentdev/skills/code-review-standards/SKILL.md` (the worked
  example and feedback-loop wording).
