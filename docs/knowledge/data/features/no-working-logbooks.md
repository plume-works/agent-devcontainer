---
type: feature
stage: implemented
description: A repository-wide authoring rule against working-logbook prose, stated once in AGENTS.md as Best Practice 8, with the graph's three narrative exceptions, a capture-and-route section for Implement, and a widened iwe-audit scope.
generated:
  by: claude-code/opus-5
  at: 2026-08-24T00:00:00Z
sources:
- resource: AGENTS.md
- resource: docs/knowledge/AGENTS.md
- resource: .agents/plugins/agentdev/skills/iwe-plan/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-audit/SKILL.md
---

# Never write a working logbook

## Purpose

Text produced during a working session tends to absorb the session itself:
failed attempts, CI run identifiers, per-attempt tables, an account of what was
tried before the thing that worked. The residue is characteristic of the current
generation of LLMs and lands in whatever text is being written — plans, READMEs,
code comments, skill files, agent definitions, issue and PR bodies.

Each addition is individually defensible, which is why per-edit judgment does
not catch it. The failure is visible only in aggregate, so the rule is stated as
a standing authoring constraint rather than left to review.

## Behaviour

**The rule binds every file.** It is stated once, as Best Practice 8 in the
repository `AGENTS.md` — the operating manual every agent reads — not in a
section scoped to the knowledge graph. It covers documents, READMEs, code
comments, skills, agent definitions, docstrings, and issue and PR bodies.

**Two tests coexist deliberately.** *Would this still be true if the work had
gone right the first time?* asks whether a sentence is a logbook trace. *Would
this still be true if the code were rewritten from scratch?* asks whether a fact
is durable. A durable fact can still be phrased as narration, so the first test
is not a restatement of the second.

**The durable-knowledge vocabulary is shared.** It lives in Best Practice 8 and
is duplicated verbatim in the `iwe-audit` skill, which must be able to state its
own criteria without a cross-repository reference. The two copies must stay
identical in wording.

**The graph names its exceptions, not the prohibition.**
`docs/knowledge/AGENTS.md` lists the three places in `data/` where narrative is
the format — `data/bugs/` (Reproduction and Root cause), `data/log.md`
(retrospective, after the fact), and a plan's `## Verification results` — and
points at Best Practice 8 for the rule itself.

**Plans have exactly one narrative section.** `## Verification results` holds
results of the `## Verification` checks and findings that change what the plan
claims. It is not a running account of attempts. `## Context` and `## Approach`
state intent, belong to the Plan skill, and stay stable during implementation.

**Implement routes findings out rather than into the plan.** A durable design
fact goes to `data/architecture/`, a defect in shipped behavior to `data/bugs/`,
work the plan should not absorb to `data/backlog/`, and a finding that changes a
material boundary back through the Plan skill's revise mode — the only route
that may edit intent. Reproducing a finding is normal work; the harness is code
and lives in the repository, but its output is not plan content.

**The auditor's scope matches the rule.** `iwe-audit` audits the non-graph prose
the rule now covers — `README.md`, `AGENTS.md`, skill and agent definitions, and
docstrings — alongside the graph documents and code comments it already read.

## Edge cases

- **Commit messages are out of scope entirely.** `/agentdev:git-commit` owns
  that surface and has its own rules. `iwe-audit` names commit messages only to
  exclude them.
- **Plans already in the graph are not rewritten.** `data/log.md` and closed
  plans are historical records; retroactively cutting narration from them would
  destroy evidence to satisfy a rule written afterwards.
- **Genuine intent corrections still arrive mid-implementation.** They go
  through the material-deviation route, which is why `## Context` and
  `## Approach` are stable rather than immutable.

## Resolved decisions

- The rule lives in `AGENTS.md`, not the graph manual. The behavior is not
  specific to `docs/knowledge/data/`, so scoping it there would have left
  READMEs, comments, and skill files unbound.
- Rejected: a read-only rule making `## Context` and `## Approach` untouchable
  by Implement. It draws the sharpest line and would be mechanically checkable,
  but genuine intent corrections do arrive mid-implementation, so the rule would
  be violated for good reasons and then discounted generally. The existing
  material-deviation route handles those, and pointing at it is enough.
- Rejected for now: extending the plan-shape gate to detect narration
  automatically. The gate reads shape, and narration has none — a line-count or
  prose-to-task ratio heuristic would fire on legitimately long plans and miss a
  short dense logbook. Tracked as
  [Detect plan narration growth mechanically](../backlog/detect-plan-narration-growth.md).
- No new spec document. The general rule is an authoring convention, not a
  workflow-skill contract; the workflow-skill half is recorded as a requirement
  in [IWE workflow skills](../spec/iwe-workflow-skills.md).
