---
type: feature
stage: implemented
description: 'A pull request body splits work into a ## Verification section for closed items and a ## Reviewer Handoff section for open items, with the pr-gen-description skill owning the structure.'
generated:
  by: claude-code/opus-5
  at: 2026-09-01T17:47:39Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-gen-description/SKILL.md
- resource: .agents/plugins/agentdev/skills/code-review-standards/SKILL.md
- resource: .github/pull_request_template.md
- resource: docs/knowledge/data/architecture/template-boundary.md
---

# Split PR How to Test into Verification and Reviewer Handoff

## Purpose

`## How to Test` mixed three moods under one heading — state to observe,
commands already run, and instructions for the reader — and invited a transcript
of the automated runs CI already performs. Splitting it by tense makes each
item's state readable without reading its text, and filtering out CI-covered
work removes the noise that heading accumulated.

## Behaviour

**A PR body carries `## Verification` and `## Reviewer Handoff`.**
`## Verification` holds closed items, each a `- [x]` box with an `**Evidence:**`
child naming what closed it; `## Reviewer Handoff` holds open items, each a
`- [ ]` box with a `**Closed by:**` child naming the party who can close it.
Neither section may hold the other's box type. An empty `## Verification` under
green CI is the expected outcome, not a gap.

**The `pr-gen-description` skill owns the structure.** Step 7 states the section
list unconditionally rather than discovering a template; Step 5 reads
`.github/workflows/` and keeps only the residue that survives both filters — no
linter, formatter, image build, or test suite CI executes, and no restatement of
a plan's own verification record.

**A consuming repository's own template is reported, never honored.** The skill
checks for `.github/pull_request_template.md` and
`.github/PULL_REQUEST_TEMPLATE/` only to tell the caller that the skill's
structure was used and their template was not consulted — never merging the two,
never silently ignoring one.

**The repository template is a pointer stub.**
`.github/pull_request_template.md` carries no sections — only prose naming
`agentdev:pr-gen-description` as the authority — so GitHub's web-UI textarea is
non-empty and a human reader has something in-repo naming where the structure
lives, with nothing in it to drift.

**The review-standards worked example shows both sections.** The
`### Recommended Template` example in `code-review-standards` demonstrates a
real `- [x]` + `**Evidence:**` item and a real `- [ ]` + `**Closed by:**` item,
and its feedback-loop instruction states the one-way direction of travel: closed
work moves from `## Reviewer Handoff` to `## Verification` with its evidence,
never back.

## Scope

Enforcement is prose only — PR bodies live on GitHub and are not in the graph,
so no mechanical gate is possible and each site states the rule itself.
**Downstream break**: a consuming repository that copied
`.github/pull_request_template.md` still holds the old structural version and
its updated `agentdev` skills now report it as not consulted; adopting means
replacing the copied file with the pointer stub or deleting it.

## References

- Plan:
  [Split PR How to Test into Verification and Reviewer Handoff](../plans/20260815-pr-verification-sections.md)
- Decision:
  [PR verification sections](../architecture/pr-verification-sections.md)
