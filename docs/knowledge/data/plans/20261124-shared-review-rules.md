---
type: plan
created: 2026-11-24
release: internal
description: Put the review rules that pr-review applies and pr-feedback-resolution acts on in one shared rulebook, and move pr-review's publishing format into its own reporting reference.
sources:
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md
- resource: .agents/plugins/agentdev/skills/code-review-standards/SKILL.md
- resource: .agents/plugins/agentdev/agents/principal-engineer.agent.md
---

# Share review rules between pr-review and pr-feedback-resolution

## Context

The review chain runs code → `/agentdev:pr-review` → a review →
`/agentdev:pr-feedback-resolution` → code. Its rules are taught in several
places that disagree:

- `pr-review` and `code-review-standards` hold two different review bars.
  `principal-engineer.agent.md` sends a reviewer to `code-review-standards`,
  which `pr-review` never uses.
- `pr-feedback-resolution` decides whether to act on a comment by a confidence
  score read from its wording, not by checking the comment against the code.
- About half of `pr-review/SKILL.md` is how a review is published, mixed into
  how findings are found and validated.

This plan applies ADR-0108 to the `pr-review` and `pr-feedback-resolution` pair.

## Approach

One rulebook, `.agents/plugins/agentdev/rules/review.md`, holds what to raise,
what not to raise, how to write a finding, what blocks a merge, and how to act
on a finding. `pr-review` pastes its full text into every review pass and
validator prompt, because a subagent does not inherit the skill's text.
`pr-feedback-resolution` links it and judges each comment by it, in place of its
confidence score. Everything about how `pr-review` publishes a review moves to
`pr-review/references/reporting.md`, and `pr-review/SKILL.md` keeps only finding
and validating. `code-review-standards` drops its review half, and the Principal
Engineer reviews through `pr-review`. `.agents/AGENTS.md` records where shared
rules and output formats live.

## Implementation Steps

### Task 1: Create the review rulebook

**Files:** Create: `.agents/plugins/agentdev/rules/review.md`

- [x] `.agents/plugins/agentdev/rules/review.md` holds exactly this text:

``` markdown
# Review rules

## Terms

- **Explicit request**: names the change it wants.
- **Question**: asks something; may be a finding phrased as a question.
- **Suggestion**: proposes an alternative; the author decides.
- **Observation**: remarks without asking; may need no action.

## Raise

1. Correctness and behavioral regressions, with an input the code really
   receives and the wrong result it produces.
2. Missing or weak tests for changed behavior.
3. Maintainability risks that materially raise future cost.
4. Security or performance issues with concrete impact.
5. Violations of a rule you can quote.

## Do not raise

- Taste, style a formatter owns, or alternatives not shown to be better.
- Speculation: a fault with no input that reaches it.

A comment or PR description calling a behavior deliberate is evidence, not a
verdict.

## Write

- Point at the place, say what breaks and why, suggest a fix.
- Keep the tone about the code.
- Ask when the code does not show its intent and the answer decides whether
  it is wrong.

## What blocks

- Blocks: a wrong outcome, a security exposure, session residue a rule
  forbids, a PR title or description that misstates the change.
- Everything else does not block.

## Act on a finding

- Check it against the code, not against how sure the comment sounds.
- Holds: make the smallest change that answers it.
- Does not hold: reply with the evidence.
- Unclear: ask.
```

### Task 2: Move pr-review's publishing into a reporting reference

**Files:** Create:
`.agents/plugins/agentdev/skills/pr-review/references/reporting.md`. Modify:
`.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [x] `references/reporting.md` holds the verdict rule, the review body rules,
  the inline comment rules, the standalone-comment exception, the rule against
  review text as chat, the pending-review tool sequence, and the single-call
  fallback script with its RESULT table, all taken from `SKILL.md` Steps 3 and
  7–9, `#prerequisites`, `#fallback-single-call-script`, and `#constraints`. It
  is concise: rules, not reasons or examples.
- [x] In `SKILL.md`, Steps 7–9 are one step that says to publish the validated
  findings as `references/reporting.md` describes.
- [x] `SKILL.md` has no `## Fallback: single-call script` section.

### Task 3: Have pr-review apply the review rulebook

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-review/SKILL.md`

- [x] `#review-focus` holds no "CRITICAL: we only want HIGH SIGNAL issues" list,
  no "Do NOT flag" list, and no severity tier definitions; it keeps each pass's
  focus, the Trigger/Path/Outcome shape of a correctness candidate, and the
  durable-knowledge and metadata focuses.
- [x] Steps 4 and 6 say that every review pass prompt and every validator prompt
  carries the full text of `rules/review.md`, linked as `../../rules/review.md`.
- [x] Step 6 has no "Stated intent is evidence, not a verdict" paragraph.

### Task 4: Have pr-feedback-resolution judge comments by the rulebook

**Files:** Modify:
`.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md`

- [ ] `#workflow-2-classify-review-comment-intent` is one step: read
  `rules/review.md` (linked as `../../rules/review.md`) and judge each
  unresolved thread and review body by its `## Act on a finding` section. The
  skill holds no confidence score, no "≥70%" or "<70%" branch, and no
  comment-language categories.
- [x] `#workflow-3-address-review-comments` has no confidence branch and keeps
  its procedure: delegate runtime code to the Principal Engineer, edit
  non-executable artifacts directly, reply, verify, resolve that exact thread.
- [ ] `#quality-standards` holds no "Avoid risky refactors without explicit
  reviewer request" or "Prefer targeted, minimal diffs" line.
- [ ] `#troubleshooting` has no "Cannot determine comment intent" entry.

### Task 5: Remove the review half of code-review-standards

**Files:** Modify:
`.agents/plugins/agentdev/skills/code-review-standards/SKILL.md`

- [ ] The skill has no `## Review Workflow` section, and
  `## Responding To Review Feedback` stays.
- [ ] Its `## Troubleshooting` table has no "Feedback seems nitpicky", "Author
  defensive about feedback", "Conflicting feedback from reviewers", or "Too many
  comments per review" row.
- [ ] Its `description` and `## When to Use This Skill` name no code review.

### Task 6: Point the Principal Engineer at pr-review

**Files:** Modify: `.agents/plugins/agentdev/agents/principal-engineer.agent.md`

- [ ] `#pull-requests` › "Reviewing" names `pr-review` alone, with no
  `code-review-standards` link.

### Task 7: Record the convention

**Files:** Modify: `.agents/AGENTS.md`

- [ ] `#catalog-locations-and-portability` holds exactly this item:

``` markdown
- Shared rules live in `rules/<artifact>.md` at the plugin root: concise,
  instructional, naming no skill. A skill that uses one says how. A skill's
  output format is prescriptive and stays private in its
  `references/reporting.md`.
```

### Task 8: Examine the first review published under the reporting reference

**Closed by:** the first AI review of a pull request that runs the
`agentdev:pr-review` this plan changes.

- [ ] The review has a short body, every finding as an inline comment, and the
  verdict that `references/reporting.md` gives for its findings.

## Acceptance

### Scenario: Review passes and validators apply the shared rulebook

- **WHEN** `/agentdev:pr-review` dispatches a review pass or a validator
- **THEN** its prompt carries the full text of `rules/review.md`
- **Checked at ship:**
  `.agents/plugins/agentdev/skills/pr-review/SKILL.md#steps`

### Scenario: A review can raise missing tests and maintainability risks

- **WHEN** `/agentdev:pr-review` reviews a change with untested changed behavior
  or a maintainability risk that materially raises future cost
- **THEN** a pass may raise it as a non-blocking finding
- **Checked at ship:** `.agents/plugins/agentdev/rules/review.md`

### Scenario: Feedback is judged against the code, not its wording

- **WHEN** `/agentdev:pr-feedback-resolution` reads an unresolved review
  comment, from a bot or a person
- **THEN** it checks the comment against the code and makes the smallest change,
  replies with the evidence, or asks, with no confidence score
- **Checked at ship:**
  `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md#workflow-2-classify-review-comment-intent`

### Scenario: The Principal Engineer reviews through pr-review

- **WHEN** the Principal Engineer agent reviews a pull request
- **THEN** it runs `/agentdev:pr-review` and no separate review checklist
- **Checked at ship:**
  `.agents/plugins/agentdev/agents/principal-engineer.agent.md#pull-requests`

## ADRs

[Shared rules live at the plugin
root](../adr/0108-shared-rules-at-plugin-root.md)

## Depends on

None.

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
- `grep -n "70%" .agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md`
  prints nothing.
- `grep -n "Review Workflow" .agents/plugins/agentdev/skills/code-review-standards/SKILL.md`
  prints nothing.
- `grep -n "code-review-standards" .agents/plugins/agentdev/agents/principal-engineer.agent.md`
  prints nothing.

## Out of scope

- A shared rulebook for pull request titles and descriptions
  (`pr-gen-description` and `pr-review` Step 3), and the rest of
  `code-review-standards`.
- A shared rulebook for code, written by the Principal Engineer and `tdd`.
- Moving `agentdev-iwe`'s `iwe-plan-review/references/plan-rules.md` to a
  `rules/` folder.

## Key references

- `.agents/plugins/agentdev/skills/pr-review/SKILL.md#review-focus` — the review
  bar and severity tiers that move to the rulebook.
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md#steps` — Steps 4 and 6
  dispatch passes and validators; Step 7 publishes.
- `.agents/plugins/agentdev/skills/pr-review/references/reporting.md#single-call-script`
  — the single-call fallback, moved out of `SKILL.md`.
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md#constraints` — the
  publishing constraints move to `references/reporting.md`.
- `.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md#workflow-2-classify-review-comment-intent`
  — the confidence score that the rulebook replaces.
- `.agents/plugins/agentdev/skills/code-review-standards/SKILL.md#review-workflow`
  — the review half that is removed.
- `.agents/plugins/agentdev/agents/principal-engineer.agent.md#pull-requests` —
  where the Principal Engineer is sent to review.
- `.agents/AGENTS.md#catalog-locations-and-portability` — where the convention
  is recorded.
- `py_packages/validate_agent_files/validate_agent_files/validators/bundled_markdown.py@find_bundled_markdown`
  — checks the links of `rules/review.md`.
