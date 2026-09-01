---
type: architecture
description: Replace the PR template's How to Test with a Verification section of closed items carrying evidence and a Reviewer Handoff section of open items naming who can close them.
generated:
  by: claude-code/opus-5
  at: 2026-08-15T00:00:00Z
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

**Delete `.github/pull_request_template.md` outright.** The file carries no
structure after this change, so deleting it is the honest end state. Rejected
for a small but real cost: GitHub's web-UI textarea would open blank, and a
human arriving at the repository would find nothing pointing at where PR
structure lives. A stub that names no sections buys both back and can never
drift, because it makes no structural claim.

**Symlink the template at the skill.** Keeps one copy of the content while the
path still exists. Rejected on three grounds: nothing reads the template
(`pr-open` always passes `gh pr create --body-file`, and templates auto-populate
only in the web UI), so the link would faithfully preserve an unread file; the
skill's structure is a section list *inside* `SKILL.md`, not a standalone file
to point at, so a symlink would need a third artifact extracted first; and this
repository tracks no symlinks at all, having just removed its only one — the
reasoning in [uv environment location](uv-environment-location.md) transfers
clause for clause, since a template symlink would likewise duplicate a
structure, go stale when the target moves, and teach that the template is the
source of truth. Whether GitHub resolves symlinks for template lookup is
undetermined — the workflow case is [known
broken](https://github.com/orgs/community/discussions/109744) and the template
case has no authoritative answer — but the payoff is zero either way, so it was
not worth establishing.

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
- **The skill owns the structure; `.github/pull_request_template.md` becomes a
  pointer stub.** No pull request in this project or a consuming one is opened
  by hand, and `pr-open` always passes `gh pr create --body-file`, so nothing
  ever read the template's structure. `pr-gen-description` previously *deferred*
  to a discovered template and fell back to its own section list; that deference
  is what made one structure live in two documents that could drift. The skill
  now states the structure unconditionally and looks for no template.
- The stub keeps GitHub's web-UI textarea non-empty and gives a human reader an
  in-repo pointer to the authority, at no drift cost — it names no sections, so
  it makes no structural claim that can go stale. A stub that ever lists
  sections has reintroduced the defect.
- A consuming repository's own `pull_request_template.md` is consequently
  ignored — but never silently. The skill still checks for one and reports that
  it was not consulted, so a consumer can replace it with a stub of their own,
  keep it for human readers, or argue for a change to the structure. Adopting
  the new behavior means the copied file stops being a format and becomes a
  pointer, or goes away.
- The cost is that PR structure is no longer *visible* to anyone who has not
  loaded the skill. The stub keeps the web textarea non-empty and says where the
  structure lives, but it does not state the shape, so a human reader must open
  the skill to learn it. Acceptable here because authorship and review are both
  automated; it would not be in a human-contributor project.
- Two call sites remain in the portable `agentdev` plugin and must change
  together: `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md` (Step
  5's testing-strategy prompt, Step 7's now-authoritative section list, the
  `## Edge Cases` entries, and the intro and `## Related Resources` template
  references) and
  `.agents/plugins/agentdev/skills/code-review-standards/SKILL.md:75-83` (the
  worked example) and `:180` (the feedback loop's "update How to Test"
  instruction).
