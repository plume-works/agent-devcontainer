---
type: feature
stage: implemented
description: pr-review reviews docs and skills critically for durable-knowledge adherence by invoking iwe-audit in a report-only diff mode, running a conditional file-following durable-knowledge pass, while only version-only and generated-file-only diffs stay fast-approved.
generated:
  by: claude-code/opus-5
  at: 2026-09-01T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-audit/SKILL.md
---

# Critical docs and durable-knowledge review in pr-review

## Purpose

`pr-review` used to fast-approve docs-only diffs alongside version-only and
generated-file-only ones, so documentation and skills shipped without scrutiny
and the durable-knowledge discipline of `AGENTS.md` Best Practice 8 never ran at
review time. Docs and skills now get a critical review focused on durable
knowledge in the IWE graph, while genuinely mechanical diffs keep the
fast-approve path.

## Behaviour

**iwe-audit has a report-only diff scope.** When a caller runs `iwe-audit` over
a diff, the candidate set is the diff's added lines rather than a grep over a
target, and §1's smell patterns apply to those added lines. Diff mode is
report-only: it produces the §4 `file:line | verdict | replacement | evidence`
table and stops, leaving the changed lines untouched — applying is the caller's
decision. The shared durable-vs-not test, §2 verdicts, and §3 verify discipline
are unchanged and used by both scopes.

**pr-review has a Documentation focus lens.** It applies to docs under `data/`,
`README.md`, `AGENTS.md`, skill and agent definitions, and docstrings. The lens
runs `/agentdev:iwe-audit` in diff mode over the changed docs/skills files and
maps each returned table row to an inline review comment. It restates none of
iwe-audit's criteria; pr-review adds only its own quote-the-line/name-the-rule
high-signal bar, so the exhaustive audit is filtered to review-worthy findings.

**The lens follows the file.** On a mixed docs+code diff, code files get the
correctness lens and docs/skills files get the durable-knowledge lens in the
same review; each lens ignores files outside it.

**Fan-out adds a conditional pass.** The review always runs 2 compliance + 2
correctness passes and adds a 5th durable-knowledge pass only when the diff
contains docs/skills files, so code-correctness coverage is never repurposed.
The parallel-pass budget and completion-count wording accommodate 4 or 5 passes,
with the durable-knowledge pass on the same time ceiling as the others.

**The fast-approve gate narrowed.** Only version-only and generated-file-only
diffs are fast-approved; a docs-only diff is no longer skipped and runs the
durable-knowledge pass.

## Scope

Durable-knowledge findings sit in the Blocking (critical/P1) tier so they win
dedup collisions, and iwe-audit stays ignorant of GitHub — the row→comment
translation lives in pr-review.

## References

- Plan:
  [Critical docs and durable-knowledge review in pr-review](../plans/20260831-pr-review-docs-durable-knowledge.md)
