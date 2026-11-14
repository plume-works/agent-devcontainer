---
type: spec
description: How pr-gen-description and code-review-standards write a pull request's verification — a Verification section of closed items with evidence and a Reviewer Handoff section of open items naming who can close them, both limited to what no automated check covers and no other document records — and how a repository's pull request template is reported rather than read.
sources:
- resource: .agents/plugins/agentdev/skills/pr-gen-description/SKILL.md
- resource: .agents/plugins/agentdev/skills/code-review-standards/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .github/pull_request_template.md
---

# PR description

## Purpose

Defines the verification sections of a pull request description the agentdev
skills generate, and where the description's structure lives. The section list
is the `pr-gen-description` skill's; this spec holds the rules that make each
verification item's state readable from its box alone. The `## Depends on`
section belongs to `stacked-prs`, and the consumer guidance file to
`template-consumption`.

## Rationale

### Two verification sections, distinguished by tense, with per-item children

A single `## How to Test` mixes states to observe, commands already run, and
instructions to the reader under one numbering. Every pull request here is
reviewed by an agent that will not, for example, rebuild a devcontainer; under
one heading an instruction it cannot perform is skipped in silence or absorbed
into a "verified" verdict. A `**Closed by:**` child naming a party other than
the reviewer keeps the item open through review, and the `**Evidence:**` child
matches the vocabulary plan checkboxes use for the same rule. No mechanical gate
can reach a pull request body, so the skills that write the format and the
reviewers that read it enforce it, and the format stays simple enough to hold by
hand.

Rejected:

- **Renaming `## How to Test` to `## How to Verify`.** Leaves past and future in
  one list, which is the defect.
- **Two sections of prose bullets without per-item children.** A prose bullet
  under `## Verification` is again a line whose closure cannot be told from its
  text, and it would be a second vocabulary for the plan-checkbox rule.
- **The reviewing agent writing the handoff.** The handoff must exist before
  review to tell the reviewer what to do, and it would put body content outside
  the author's control.

### The skill owns the structure; the template is a pointer stub

No pull request here is opened by hand, and `pr-open` always passes
`gh pr create --body-file`, so nothing reads a template's structure; a skill
that deferred to a template kept one structure in two documents that could
drift. The stub keeps GitHub's web-UI textarea non-empty and points a human
reader at the skill, and makes no structural claim that can go stale. The cost
is that the structure is visible only in the skill, which is acceptable where
authorship and review are automated.

Rejected:

- **Deleting the template.** The web-UI textarea would open blank, and a human
  would find nothing pointing at where the structure lives.
- **Symlinking the template at the skill.** Nothing reads the template; the
  structure is a list inside `SKILL.md`, not a file to point at; and the
  repository tracks no symlinks.
