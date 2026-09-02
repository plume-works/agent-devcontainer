---
type: plan
created: 2026-09-02
description: Add a fresh-context durable-knowledge auditor that gates every plan-intent edit in the Plan skill and shares its residue vocabulary with the Evidence checks in Implement and Verify, so the residue caught only in PR 88 review is caught before submission.
generated:
  by: claude-code/opus-4.8
  at: 2026-09-02T00:00:00Z
---

# Audit every plan edit in a fresh context

## Context

Every durable-knowledge finding on [PR
#88](https://github.com/plume-works/agent-devcontainer/pull/88) landed in plan
content the IWE workflow skills authored — provenance in `## Approach` ("a real
rebuild proved…"), estimate-correction narration in task descriptions ("widened
from nine to thirteen"), and session-transcript residue in `- **Evidence:**`
blocks (raw driver stdout, an ephemeral machineID, an uncommitted
`.tmp/task4-driver.sh`). The rules that forbid all of it already exist and were
merged before that PR opened. They were caught only in review.

[Never write a working logbook](20260817-no-logbooks-in-the-graph.md) changed
the *wording* of those rules after the same failure recurred across tasks, and
[Plans record intent, not the path taken to it](../spec/iwe-workflow-skills.md)
made the rule normative. Neither added enforcement: the author who wrote the
residue is the party trusted to notice it, in the same session that accumulated
the context which buried the rule. A polluted context does not reliably audit
itself — a writer cannot proofread their own draft cold. This plan adds the
enforcement layer those left out.

## Approach

A durable-knowledge audit runs in a fresh subagent whose context is only the
scope and the file, with no inheritance of the planning conversation. Isolation,
not a louder rule, is the fix: the residue survives because the rule is buried,
so the audit reads the artifact from a clean context that never saw the work in
progress.

A tiny auditor agent supplies that clean context and defers to the one rulebook.
It carries no rule text of its own — it invokes `/agentdev:iwe-audit`, which
gains a plan-mode scope, and returns the report table. It has no `Edit`/`Write`
tools, so "report-only, fix nothing" is enforced by tooling rather than by
instruction.

"Every plan edit is audited" reduces to two gates, because a plan has exactly
two authors. Plan intent is edited only through the Plan skill — create, revise,
and the routes Implement, Verify, and Ship take back to revise mode all funnel
there — so one gate in Plan, run on both create and revise before validation,
covers every intent edit by construction. Evidence blocks are the one path that
bypasses Plan: Implement writes them at tick time. They need the same auditor's
smell vocabulary applied where Implement writes and Verify checks.

Rejected: a self-audit step inside the Plan skill's own context. It re-reads the
polluted context that hid the residue in the first place, and it forces the rule
text to be duplicated into each skill, where the copies drift. Also rejected:
each caller spawning a generic subagent with the rule inlined — same drift, at
every call site. The named auditor keeps the rule in one place and the isolation
boundary in one agent.

## Implementation Steps

### Task 1: Confirm a subagent can invoke a skill

**Files:** none (smoke test)

The architecture assumes the auditor agent can invoke `/agentdev:iwe-audit` at
runtime. Verify that a dispatched subagent can invoke a skill before building on
it. If it cannot, the auditor prose instead `Read`s
`.agents/plugins/agentdev/skills/iwe-audit/SKILL.md` and follows it — the same
single source of truth, one hop further — and Tasks 2 and 4 adjust their wording
accordingly.

- [x] The subagent-invokes-skill capability is confirmed, or the
  `Read`-and-follow fallback is chosen and recorded in
  `## Verification results`.
  - **Evidence:** Smoke test — a dispatched `general-purpose` subagent invoked
    `agentdev:extract-github-actions-logs` via the Skill tool and received the
    skill's instructions; verdict "SKILL TOOL AVAILABLE — invocation succeeded".
    The primary skill-invocation path is confirmed; the `Read`-and-follow
    fallback is not needed, so Tasks 2 and 4 use the skill-invocation wording.
    Recorded in `## Verification results`.

### Task 2: Add the auditor agent

**Files:** Create:
`.agents/plugins/agentdev/agents/durable-knowledge-auditor.agent.md`

A minimal agent whose only jobs are to be a fresh context and to point at the
rulebook. Frontmatter `name`, `description` (good enough for the validator's
`--recommend`), and `tools: Bash, Read, Grep, Glob, Skill` — no `Edit`/`Write`,
so the agent cannot modify the file it audits. Body carries the
autonomous-subagent stance already used by the TDD agents and no rule text: it
audits the file named in its prompt against the scope named in its prompt by
invoking `/agentdev:iwe-audit`, returns that skill's report table verbatim, and
changes nothing.

- [x] The agent file exists with the tools and stance above and carries no rule
  text of its own.
  - **Evidence:**
    `.agents/plugins/agentdev/agents/durable-knowledge-auditor.agent.md` created
    with `tools: Bash, Read, Grep, Glob, Skill` (no Edit/Write), the
    autonomous-subagent stance, and a body that invokes `/agentdev:iwe-audit`
    and returns its table with no rule text.
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    passed 45/45, 0 errors 0 warnings, with the agent listed.

### Task 3: Give iwe-audit a plan-mode scope

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md`

Extend the existing "Diff scope" caller-scoped, report-only precedent with a
plan-mode scope. When the target is a plan, the candidate set is every plan
section except the two narrative-sanctioned homes: `## Verification results` and
`- **Evidence:**` children. Revise the `Do not audit: data/plans/` line so it no
longer blanket-excludes plans — it excludes only those two sanctioned homes
within a plan. Everything downstream (Durable vs not, verdicts, verify,
report-only) is unchanged and shared with the other scopes.

- [x] iwe-audit audits a plan's intent sections and leaves
  `## Verification results` and `- **Evidence:**` children untouched, with the
  exclusion line reconciled to match.
  - **Evidence:** `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md` §Scope
    drops `data/plans/` from the blanket exclusion and names the two sanctioned
    homes as out-of-scope; a new **Plan scope** paragraph puts intent sections
    in scope and those two homes out; §4 "Diff scope and Plan scope stop here"
    makes plan mode report-only.
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    passed 45/45, 0 errors 0 warnings.

### Task 4: Gate plan edits in the Plan skill

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md`

Add a step between the coherence check and validation, run in both create and
revise mode: dispatch the auditor agent on the plan draft in plan-mode, apply
its report-only verdicts to the draft, then proceed to `iwe normalize` /
`iwe schema validate`. Because create, revise, and every back-to-revise route
funnel through this skill, this one gate covers all plan-intent edits.

- [ ] Both create mode and revise mode dispatch the auditor before validation
  and apply its verdicts.

### Task 5: Extend the Evidence-residue vocabulary in Implement and Verify

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-verify/SKILL.md`

The Evidence-traceability rule already exists in both skills — Implement
requires evidence "specifically enough that a later session can go look", Verify
makes an untraceable citation a CRITICAL. The gap is a negative smell list. Name
the concrete residue that disqualifies an Evidence citation: raw command stdout
transcribed as evidence, ephemeral identifiers that will not exist next session,
and citations of uncommitted `.tmp/` harnesses. Add it where Implement writes
the Evidence child and mirror it in Verify's Evidence check, sharing the
auditor's vocabulary rather than restating the rule.

- [ ] Both skills name the raw-stdout, ephemeral-identifier, and
  uncommitted-`.tmp/` smells as disqualifying an Evidence citation.

### Task 6: Validate the catalog and record the spec

**Files:** Modify: `docs/knowledge/data/spec/iwe-workflow-skills.md` (via Ship,
not here)

Run
`uv run validate_agent_files --recommend . --require-marketplace claude codex`;
the new agent must pass, including a `--recommend`-worthy description. The
`## Spec changes` delta below is the intended contract; Ship merges it into the
durable spec after Verify.

- [ ] `validate_agent_files --recommend` passes with the new agent present.

## Verification results

- **Task 1 (subagent-invokes-skill capability):** Confirmed. A dispatched
  `general-purpose` subagent invoked `agentdev:extract-github-actions-logs`
  through the Skill tool and received that skill's instructions. The primary
  path in the Approach holds; the `Read`-and-follow fallback is unused, so the
  auditor agent (Task 2) and the Plan-skill gate (Task 4) invoke
  `/agentdev:iwe-audit` directly rather than reading its SKILL.md.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — the existing requirement
*Plans record intent, not the path taken to it* states the rule but names no
enforcement. This change adds the enforcement mechanism as a new scenario. The
change touches a requirement's scenario set, so it takes the fenced-delta form.

``` markdown
## MODIFIED Requirements

### Requirement: Plans record intent, not the path taken to it

Plan documents SHALL record what is settled rather than the sequence of attempts
that settled it. `## Verification results` SHALL be a plan's only narrative
section. Implement SHALL route a finding that does not change the plan's intent
to its own document — `data/architecture/`, `data/bugs/`, or `data/backlog/` —
rather than into the plan's `## Context` or `## Approach`, which state intent
and remain the Plan skill's to own. Every edit to a plan's intent sections SHALL
be audited for durable-knowledge residue by a reviewer holding no context beyond
the audit scope and the plan file, before the edit is validated.

#### Scenario: Implementation produces a durable finding

- **WHEN** implementation establishes a constraint, root cause, or rejected
  alternative that the plan did not anticipate
- **THEN** Implement records it in the reference document that owns the area and
  reports the capture, leaving the plan's intent sections unchanged

#### Scenario: A session narrates its attempts into a plan

- **WHEN** a plan would gain a running account of an in-flight investigation —
  failed attempts, CI run identifiers, per-attempt tables
- **THEN** that content is excluded from the plan, because it would not be true
  had the work succeeded the first time

#### Scenario: A finding changes the plan's intent

- **WHEN** a finding alters scope, observable behavior, compatibility,
  acceptance criteria, dependencies, or an out-of-scope boundary
- **THEN** it goes back through the Plan skill's revise mode rather than being
  captured elsewhere or written into the plan directly

#### Scenario: A plan edit is audited before validation

- **WHEN** Plan creates or revises a plan and reaches validation
- **THEN** a reviewer holding only the audit scope and the plan file audits its
  intent sections for durable-knowledge residue, its verdicts are applied, and
  the narrative-sanctioned `## Verification results` and `- **Evidence:**`
  children are left out of that audit
```

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes with the auditor agent present.
- `uv run pytest .agents/plugins/agentdev/tests` passes.
- `iwe normalize` and `iwe schema validate` pass on the graph after the spec is
  synchronized at Ship.
- A manual trace confirms every plan-intent edit path (create, revise, and the
  Implement/Verify/Ship routes back to revise mode) funnels through the Plan
  skill's audit gate, and that the auditor agent carries no rule text.
- A manual read confirms iwe-audit's plan-mode leaves `## Verification results`
  and `- **Evidence:**` children out of scope while auditing intent sections.

## Out of scope

- A mechanical (non-agent) check for plan residue. The gate is a fresh-context
  reviewer, not a linter; a grep-based gate is the subject of the separate
  backlog task
  [Detect plan narration growth mechanically](../backlog/detect-plan-narration-growth.md).
- Auditing spec, architecture, feature, and comment targets. iwe-audit already
  covers those; this plan only adds the plan-mode scope and the two gates.
- Rewriting the residue already in shipped plans. This changes the workflow so
  future edits are audited; back-cleaning existing plans is separate.

## Key references

Verified anchor points (line numbers as of 2026-09-02, re-verified 2026-09-02):

- `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md:29 — Do not audit: data/plans/ (exclusion to reconcile)`
- `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md:34 — Diff scope (caller-scoped report-only precedent)`
- `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md:98 — Diff scope stops here (report-only contract)`
- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:107 — Step 6 Check coherence`
- `.agents/plugins/agentdev/skills/iwe-plan/SKILL.md:111 — Step 7 Validate and stop (gate goes before this)`
- `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md:42 — Evidence child, "specifically enough that a later session can go look"`
- `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md:101 — the only route that may edit plan intent`
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:36 — untraceable evidence is a CRITICAL`
- `.agents/plugins/agentdev/agents/tdd-red.agent.md:10 — autonomous-subagent stance to reuse`
- `docs/knowledge/data/spec/iwe-workflow-skills.md:175 — Requirement: Plans record intent, not the path taken to it`
