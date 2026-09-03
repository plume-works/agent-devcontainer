---
name: pr-gen-description
description: Generate comprehensive pull request description following /agentdev:code-review-standards with change analysis, testing strategy, and migration notes. Use when creating a PR, writing PR description, preparing for code review, or documenting technical decisions.
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/*)
---

# Generate Pull Request Description

Generate a comprehensive PR description by analyzing the change set and writing it into the section structure defined by Step 7 below, which is this skill's own and does not come from any repository file. Use [code-review-standards](../code-review-standards/) for wording and review conventions, and use the Coding Conventions section of that repository's root `AGENTS.md` only for shared quality expectations rather than repeating them here.

## When to Use This Skill

- Creating a pull request for code changes
- Need detailed PR description that explains changes
- Want to follow project conventions for PR documentation
- Preparing for code review
- Documenting technical decisions and assumptions

## Prerequisites

- Changes committed to a branch
- Understanding of what was changed and why
- Related GitHub issues identified (optional)
- Testing performed

## Inputs

- **Base Ref** or **Commit Range**: Default to the PR merge base with
  `origin/main`; accept an explicit base ref or range when the caller provides
  one. A caller updating an existing pull request passes that PR's base branch.
- **Related Issues**: GitHub issue numbers
- **Breaking Changes**: Yes/No
- **Migration Steps**: If breaking

## Bundled Scripts

Use this helper instead of retyping inline git commands:

- [review-git-changes.sh](scripts/review-git-changes.sh) prints the branch,
  working tree status, diff stat, patch, and commit log for the change set.

The last line of stdout is always `RESULT=<NAME>`; match on that name, not on a
bare number.

## Workflow

### Step 1: Analyze Git Changes

```bash
${CLAUDE_SKILL_DIR}/scripts/review-git-changes.sh
```

Pass `--base-ref <ref>` when the caller supplies a base other than
`origin/main`, or `--range <range>` for an explicit commit range. Add
`--stat-only` to skip the patch on a very large change set.

The script compares against the merge base rather than a raw `origin/main..HEAD`
range: when the branch and its base have diverged, PR review shows the changes
introduced by the head branch since that common ancestor.

Handle the result:

| RESULT            | Exit | Meaning                                                                  | Action                                                                                                                             |
| ----------------- | ---- | ------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`         | `0`  | The change report was printed                                            | Continue with Step 2.                                                                                                              |
| `NO_CHANGES`      | `3`  | Nothing to describe: no working tree changes and no commits in the range | **STOP.** Follow the **No changes** edge case instead of writing a description.                                                    |
| `PREFLIGHT_ERROR` | `2`  | Bad usage, not a repo, no commits, or an unknown ref                     | **STOP.** Fix the reported error — usually a wrong `--base-ref` or `--range`, or a base ref that has not been fetched — and rerun. |
| `SCRIPT_FAILURE`  | `1`  | The script broke                                                         | **STOP.** Report the blocker verbatim; do not retry or reconstruct the analysis with ad-hoc `git` commands.                        |

Categorize: new, modified, deleted, renamed.

Describe the committed branch, which is what the pull request will contain. The
script also prints uncommitted working-tree changes — report those to the caller
as out of scope instead of writing them into the description.

### Step 2: Identify Change Categories

Features, Bug Fixes, Refactoring, Tests, Documentation, Configuration, Performance, Security.

### Step 3: Extract Technical Details

For each significant change: purpose, approach, files affected, dependencies, side effects.

### Step 4: Identify Related Issues

Search commits and branch name for #123, GH-456. Link issues, design docs, related PRs.

### Step 5: Select What Needs Stating

This step selects; it does not inventory. Read `.github/workflows/` for what CI
already runs on the branch, then keep only what survives both filters:

1. **Omit what an automated check covers.** No linter, formatter, image build,
   or test suite CI executes, and no "CI is green" line — the checks report that
   themselves, continuously, and a sentence claiming it goes stale on the next
   push.
2. **Reference, never restate, what another document owns.** A plan carrying
   per-task evidence is the record; link it under `## Related` instead of
   copying its verification list.

What remains is the residue: manual checks no test covers, and
environment-dependent behavior CI cannot reach. Sort it by tense for Step 7 —
already done into `## Verification`, still outstanding into
`## Reviewer Handoff`. Expect the residue to be short and often empty.

### Step 6: Check Breaking Changes

API changes, config changes, dependency version changes, schema changes.

Identify any required migration work such as config changes, rollout order, data backfills, operator actions, or compatibility notes.

### Step 7: Generate The Description

This section list is the structure. Follow the wording rules from [code-review-standards](../code-review-standards/), and remove sections that do not apply:

- **Summary**: 2-3 sentences
- **What Changed**: Group related changes instead of listing files
- **Why**: User or system impact
- **Verification**: Closed items only, each a `- [x]` box with an
  `**Evidence:**` child naming what closed it. Past tense: work already done.
  Frequently empty — when CI covers the change, an empty `## Verification` is
  the expected outcome, not a gap.
- **Reviewer Handoff**: Open items only, each a `- [ ]` box with a
  `**Closed by:**` child naming the party who can close it. Future tense: work
  still outstanding.
- **Breaking Changes**: Only when applicable
- **Migration**: Required rollout, upgrade, backfill, or operator steps
- **Related**: Issues, design docs, or follow-up work

Neither verification section may hold the other's box type — the split by tense
is what makes each item's state readable without reading its text.

When a consumer-owned guidance file `.github/pr-description-guidance.md` exists,
read it and let its instructions take precedence over the default generation of
the sections above. It holds instructions — repository-specific directions such
as "always link the Jira ticket in Related" — not section headings; a heading
list would be a structure file, which this step supersedes. Its instructions
MAY add to or override how any section is generated, but SHALL NOT collapse or
rename the `## Verification` / `## Reviewer Handoff` split: that tense split is
the one floor guidance may not override. This is the only customization channel;
the skill still never reads structure out of the pull request template itself.

Check whether the repository has its own pull request template —
`.github/pull_request_template.md` or a file under
`.github/PULL_REQUEST_TEMPLATE/` — but only in order to report it. When one
exists, tell the caller that this skill's structure was used and their template
was not consulted, so they can keep it, replace it with a pointer stub, or ask
for the structure to change. Never read a structure out of it, never merge it
with the list above, and never ignore it in silence.

The one exception is a template that opts out: if the file contains the HTML
comment `<!-- pr-gen-description: no-template -->`, it is a deliberate
placeholder that defers to this skill's structure, so use the structure and say
nothing about the template. Report only templates that carry a real structure
this skill overrode.

### Step 8: Review and Validate

Ensure completeness, technical accuracy, valid links, and that every `## Verification` item names evidence that actually exists. Confirm that the final description follows the Step 7 section list and does not repeat generic review or clean-code checklists from the referenced documents.

## Edge Cases

- **No changes**: the script reports `NO_CHANGES` and notes the empty change
  set on stderr. Report that there is nothing to describe and check the branch
  and commit range with the caller.
- **Too many changes**: Summarize categories, detail significant only
- **Empty `## Verification`**: under green CI this is the expected outcome, not
  a gap to fill. Everything CI covers was correctly filtered out in Step 5;
  writing items back in to make the section look complete reintroduces the
  noise the filters exist to remove.
- **No test covers a change**: say so under `## Reviewer Handoff` as an open
  item naming who can close it. Do not warn about a thin verification section
  that is thin because CI covers the change.
- **An item nobody reviewing can close**: it still belongs under
  `## Reviewer Handoff`, with `**Closed by:**` naming the party who can — a
  human with the hardware, a follow-up deploy, an operator. An item the
  reviewer cannot perform is exactly what the section exists to carry; dropping
  it is how it gets silently absorbed into a "verified" verdict.
- **Multiple unrelated changes**: Suggest splitting PRs

## Related Resources

- The section structure: the list in Step 7 of this skill
- The consumer customization point: `.github/pr-description-guidance.md`, a
  consumer-owned instructions file whose directions take precedence over the
  default section generation (subject to the Step 7 tense-split floor)
- [code-review-standards](../code-review-standards/)
- Coding Conventions in the repository's root `AGENTS.md`
