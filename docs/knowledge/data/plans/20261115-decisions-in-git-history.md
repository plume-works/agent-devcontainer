---
type: plan
created: 2026-11-15
release: internal
description: Put the decisions of each pull request in its body, and tell agents to look for an answer in the code, then the git history, then a document.
sources:
- resource: AGENTS.md
- resource: .agents/plugins/agentdev/skills/pr-gen-description/SKILL.md
---

# Put decisions in the git history

## Context

[Plan tasks evidence and ADRs as git
history](../archive/next-release/backlog/plan-evidence-and-decisions-in-git-history.md)
asks for the git history as the permanent record of decisions. The user gives
the reason: a document becomes incorrect when no person keeps it correct. The
specs that the graph removed are an example: the code did not agree with 4 of
their 189 reasons ([ADR-0002](../adr/0002-decisions-are-adrs-in-the-graph.md)).

The squash merge writes the pull request body as the commit message
(`squash_merge_commit_message: PR_BODY`). As a result, a decision in the body
becomes part of the history of `main`. Today `/agentdev:pr-gen-description` has
no section for decisions, and `AGENTS.md#project-memory` tells agents that
`docs/knowledge/data/` is the correct source.

The ADRs stay. This plan makes the git history hold the same decisions. [Archive
ADRs when their plans ship](../someday/archive-adrs-when-their-plans-ship.md) is
the step after this plan.

## Approach

This plan adds a `## Decisions` section to `/agentdev:pr-gen-description`. The
section states each decision of the change, with its reason and its rejected
options. For each ADR that the diff adds, the section states the decision of
that ADR.

This plan adds to `AGENTS.md#project-memory` a sequence of places in which to
find an answer: the code, then the git history, then a document. In the git
history, the order is `git log` and `git blame`, then the squash commit body,
then the commits of the pull request with `scripts/completion-evidence.py show`.
A document is the last source, and an agent must not accept it as always
correct. This order replaces the line that names `docs/knowledge/data/` as the
correct source.

Step 5 of `/agentdev:pr-gen-description` says that a pull request body refers to
the data that a different document holds, and does not repeat it. This plan adds
to that rule an exception for a decision that an ADR also states.

## Implementation Steps

### Task 1: Add a Decisions section to the pull request body

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md`

- [ ] Step 7 lists **Decisions**: each decision of the change, with its reason
  and its rejected options. The section also states the decision of each ADR
  that the diff adds. The skill does not write the section when the change makes
  no decision.
- [ ] `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.

### Task 2: Tell agents where to find an answer, and in which sequence

**Files:** Modify: `AGENTS.md`

- [ ] `AGENTS.md#project-memory` gives the order: the code, then the git
  history, then a document, and it names `scripts/completion-evidence.py show`.
  `AGENTS.md` does not contain the line "treat `docs/knowledge/data/` as the
  source of truth for project state and decisions".

### Task 3: Permit a decision in the pull request body

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md`

- [ ] Step 5 item 2, "Reference, never restate, what another document owns",
  permits a pull request body to state a decision that an ADR also states, and
  names ADR-0094.

### Task 4: Examine the body of a pull request that has decisions

**Closed by:** the first pull request after this change whose diff adds an ADR.

- [ ] Its body has a `## Decisions` section that states the decision of the ADR.

## Acceptance

### Scenario: A pull request body states the decisions of the change

- **WHEN** `/agentdev:pr-gen-description` writes the body of a pull request
  whose change makes a decision
- **THEN** the body has a `## Decisions` section with each decision, its reason,
  and its rejected options
- **Checked at ship:**
  `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md`

### Scenario: An agent examines the code and the git history first

- **WHEN** an agent must find an answer about this repository
- **THEN** `AGENTS.md` tells it to read the code first, the git history second,
  and a document last
- **Checked at ship:** `AGENTS.md`

## ADRs

[Code first, git history second, documents
last](../adr/0094-code-then-git-history-then-documents.md)

## Depends on

[Put task evidence in the commit
message](../archive/next-release/plans/20261115-completion-evidence-in-commit-messages.md)

## Verification

``` bash
uv run validate_agent_files --recommend . --require-marketplace claude
rg -n 'source of truth for project state' AGENTS.md
```

The `rg` command prints nothing.

## Out of scope

- A change that moves ADRs to the archive. [Archive ADRs when their plans
  ship](../someday/archive-adrs-when-their-plans-ship.md) holds it.
- The order that the catalog rulebooks (`iwe-planner`,
  `/agentdev-iwe:iwe-explore`) use to find related work. They stay as they are.
- A test of the text of a pull request body.

## Key references

- `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md#step-7-generate-the-description`
  — the list of body sections.
- `AGENTS.md#project-memory` › "treat `docs/knowledge/data/` as the source of
  truth" — the line that the order replaces.
- `.agents/plugins/agentdev/skills/pr-gen-description/SKILL.md#step-5-select-what-needs-stating`
  › "Reference, never restate, what another document owns" — the rule that this
  plan adds the exception to.
