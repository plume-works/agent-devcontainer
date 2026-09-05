---
type: feature
stage: implemented
description: A consuming repository captures its extra pull request template sections as instructions in a consumer-owned .github/pr-description-guidance.md, which pr-gen-description reads with precedence over its own section generation.
generated:
  by: claude-code/opus-5
  at: 2026-09-05T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-gen-description/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: docs/knowledge/data/architecture/template-boundary.md
---

# Consumer PR description guidance

## Purpose

`pr-gen-description` owns the PR description structure and supersedes any
repository pull request template, which leaves a consuming repository with no
way to say anything about what its descriptions contain. Adopting the template
into an existing repository either lost that repository's own template sections
silently or left a real template in place to drift. A consumer-owned
instructions file gives those sections a destination and gives the skill a
customization channel, without reopening the structure it deliberately closed.

## Behaviour

**A consumer may hold PR description instructions in
`.github/pr-description-guidance.md`.** The file carries instructions —
repository-specific directions such as "always link the Jira ticket in Related"
— never section headings, because a headings list is a structure file, which is
what the skill's own section list supersedes.

**Guidance takes precedence, with one floor.** When the file exists,
`pr-gen-description` reads it and its instructions take precedence over the
default generation of the skill's sections. They may not collapse or rename the
`## Verification` / `## Reviewer Handoff` split: that tense split is what makes
each item's state readable. The skill still never reads structure out of the
pull request template itself.

**Template consumption evaluates an existing template rather than overwriting
it.** Setup with an existing template, and update when the PR-template path
changed upstream, propose a section-by-section mapping of the consumer's
headings onto the skill's sections and present two buckets — covered and extras
— for the user to correct before anything is written. The extras are one batch
decision, defaulting to capture, with three outcomes: capture as guidance, drop
all, or keep the template as-is and let the skill report it as not consulted.

**Capture translates a heading into an instruction.** A consumer
`## Rollback plan` becomes an instruction telling the skill to emit that
content, and the template is reduced to the
`<!-- pr-gen-description: no-template -->` stub. That stub exception applies
only to a marker-bearing file with no Markdown section headings; a marker plus
real headings is still real structure and is reported.

**The guidance file is consumer-created state.** It is absent from this
publisher repository and is not a `tracked_paths` diff input; update mode's
PR-template evaluation preserves an existing one unless the user explicitly
replaces or removes it.

## Specified by

[Template consumption](../spec/template-consumption.md)
