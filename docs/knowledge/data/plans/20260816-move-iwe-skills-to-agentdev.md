---
type: plan
stage: done
created: 2026-08-16
completed: 2026-09-02
description: Relocate the seven IWE workflow skills from .claude/skills/ into the agentdev plugin under iwe- prefixed names, making them plugin-portable and shipping them to catalog consumers.
generated:
  by: codex/gpt-5
  at: 2026-09-02T05:54:56Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-ship/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-explore/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-implement/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/AGENTS.md
- resource: docs/knowledge/AGENTS.md
- resource: docs/knowledge/data/spec/iwe-workflow-skills.md
- resource: docs/knowledge/data/spec/template-consumption.md
- resource: docs/knowledge/data/architecture/template-boundary.md
---

# Move the IWE workflow skills into the agentdev plugin

## Context

The seven IWE workflow skills — setup, explore, plan, implement, verify, ship,
weekly — are tracked under `.claude/skills/`, which is the one place this
repository says the catalog does not live. `.claude/README.md` documents
`settings.json` as the sole remaining occupant of that directory, and
[Template boundary](../architecture/template-boundary.md) classifies `.claude/`
as "Shared Claude permissions, official plugins, local ignore rules, and
explanatory README" with no mention of skills. Both descriptions have drifted
from the tree.

The consequence is not cosmetic. `.claude/skills/` is retained by every project
that copies the template surface, so a consuming project silently inherits seven
skills that [Template consumption](../spec/template-consumption.md) §7 never
enumerates, while the catalog those skills belong to reaches consumers through a
supported installation path they do not use. Distribution and documentation
disagree.

An exploration compared four placements: rename in place, move into `agentdev`
under `iwe-` prefixed names, publish a separate `iwe` plugin, and move while
keeping bare names. The maintainer chose the `agentdev` move with the `iwe-`
prefix.

## Approach

Relocate each `.claude/skills/<name>/` to
`.agents/plugins/agentdev/skills/iwe-<name>/`, set the frontmatter `name` to
match, and repair the references that only worked because the skills sat inside
this repository. Invocation becomes `/agentdev:iwe-plan` and the rest.

The containment surface is small and was measured rather than estimated: one
backticked repository path, nine bare-name sibling references, and no escaping
markdown links. The prefix is retained even though `agentdev:` already
namespaces, because `plan`, `ship`, and `verify` are generic enough to read as
peers of the `pr-*` family once they sit in the same directory.

The rejected alternative was a separate `iwe` plugin, which would have given
`/iwe:plan` and made the prefix redundant, and would have let a project take the
git and pull-request catalog without the graph workflow. It was rejected in
favour of a single catalog to version and install; the cost is that `agentdev`
now ships a workflow assuming an IWE graph, which Task 4 addresses by widening
what both manifests advertise rather than by leaving the skills undiscoverable.

Two failure modes shape the task order. First, the catalog validator only
inspects markdown links, so the backticked `.claude/skills/verify/SKILL.md` in
Ship survives the move as a green-validating path that resolves nowhere in a
consumer's plugin cache — Task 3 exists because Task 8 cannot catch it. Second,
`iwe rename` repairs links between graph documents, but every reference at issue
here is a backticked path or a `sources:` entry, so Task 6 is manual by
necessity.

## Implementation Steps

### Task 1: Re-verify every anchor against the post-dependency checkout

**Files:** Modify:
`docs/knowledge/data/plans/20260816-move-iwe-skills-to-agentdev.md`

This plan is written to run after
[Embed structured spec deltas in IWE plans](20260816-structured-plan-spec-deltas.md)
ships, and that plan rewrites Plan, Implement, Verify, and Ship. Every line
number in `## Key references` predates those edits.

- [x] Re-locate each anchor in `## Key references`, correct the line numbers,
  and restamp the section date. Confirm the nine bare-name sibling references
  and the single backticked path still exist and have not already been reworded
  by the dependency; if the count changed, correct Task 3's scope before
  starting it.
  - **Evidence:** `## Key references` re-anchored against the 2026-09-01
    checkout and date-restamped. The dependency plan's rewrite moved every line
    number (ship verify 36→37, ship link 76-78→95-97, AGENTS table 183-189→
    214-220, template-consumption 215-232→219-239, template-boundary count
    192→194, structured-plan clause 600-602→495-496, cross_reference 53→56,
    pr-open idiom 146,148→136,138). The bare-name sibling references grew from
    nine to thirteen (Implement 4→7 at :20,63,75,76,99,102,126; Explore 3→4 at
    :44,66,72,85; Verify 2 at :28,87) and the single backticked path survives
    intact at ship:37 — Task 3's scope corrected to thirteen accordingly. Skill
    counts re-measured: the agentdev plugin holds 27 tracked skills pre-move
    (not the plan's 23), so Task 5/8/Verification totals corrected to 34 post-
    move and the validator baseline to 43/43. Committed with the code.

### Task 2: Relocate and rename the seven skill directories

**Files:** Create:
`.agents/plugins/agentdev/skills/iwe-{setup,explore,plan,implement,verify,ship,weekly}/SKILL.md`
Delete: `.claude/skills/{setup,explore,plan,implement,verify,ship,weekly}/`

Each skill is a lone `SKILL.md` with no `references/` or `scripts/`
subdirectory, so the move is a directory rename plus one frontmatter line.

- [x] `git mv` all seven directories to their `iwe-` prefixed names under
  `.agents/plugins/agentdev/skills/`, set each frontmatter `name` to
  `iwe-<name>`, leave every description unchanged, and confirm `.claude/skills/`
  no longer exists.
  - **Evidence:** `git mv` relocated all seven (setup, explore, plan, implement,
    verify, ship, weekly) to `.agents/plugins/agentdev/skills/iwe-*/` — git
    records each as a rename (R) whose only content change is the `name:`
    frontmatter line (`-name: <bare>` / `+name: iwe-<bare>`), descriptions and
    bodies byte-identical. Empty `.claude/skills/` removed; `ls .claude/skills/`
    returns "No such file or directory". The untracked working-tree skill
    `iwe-implement-all/` is not part of this plan and was left untouched.
    Committed with this task.

### Task 3: Make every in-skill cross-reference plugin-portable

**Files:** Modify:
`.agents/plugins/agentdev/skills/iwe-{ship,explore,implement,verify}/SKILL.md`

Fourteen references — thirteen bare-name plus one backticked path — assume the
skills can see each other by repository path or bare name. Inside a plugin cache
neither holds.

- [x] Replace the backticked `.claude/skills/verify/SKILL.md` in Ship's step 3
  with the `/agentdev:iwe-verify` invocation, and rewrite the thirteen bare-name
  sibling references in Explore, Implement, and Verify as namespaced
  invocations, matching the existing idiom in `pr-open` and `pr-sync`. Then grep
  the seven files for any remaining `.claude/`, `.agents/`, or `docs/knowledge/`
  path and confirm the only survivors are IWE document keys relative to the
  library root, which resolve at runtime and must stay as they are.
  - **Evidence:** Ship step 3 now invokes `/agentdev:iwe-verify` (no backticked
    repo path). The thirteen bare-name references are namespaced: Explore (4) at
    :44,67,74,88 → `/agentdev:iwe-{implement,plan}`; Implement (7) at
    :20,63,76,77,101,105,130 → `/agentdev:iwe-{plan,verify,ship}`; Verify (2) at
    :28,88 → `/agentdev:iwe-{plan,ship}`.
    `grep -rE '\.claude/|\.agents/|docs/knowledge/'` over the seven files
    returns nothing (exit 1); the only surviving in-repo-looking references are
    IWE document keys (`data/spec/`, `data/plans/`, …) relative to the library
    root, which resolve at runtime and must stay. `validate_agent_files` reports
    43/43 valid, 0 errors, 0 warnings — the ship:37 catalog-path error is gone.
    Committed with this task.

### Task 4: Widen and version the plugin manifests

**Files:** Modify: `.agents/plugins/agentdev/.claude-plugin/plugin.json`,
`.agents/plugins/agentdev/.codex-plugin/plugin.json`,
`.claude-plugin/marketplace.json`

Both manifests describe a catalog of "git, pull requests, review, CI,
formatting, container and Codespace escalation". A knowledge-graph workflow is
not in that sentence, and the Codex `longDescription` and `keywords` repeat the
omission. Neither manifest enumerates individual skills — Codex points at
`./skills/` and Claude auto-discovers — so no skill list needs extending.

- [x] Extend the shared `description`, the Codex `longDescription`, and the
  Codex `keywords` to cover the IWE planning and knowledge-graph workflow, then
  bump `version` from `3.0.0` to `3.1.0` in all three files together.
  - **Evidence:** The shared `description` in all three manifests now appends
    "and an IWE knowledge-graph planning workflow"; the Codex `longDescription`
    describes the workflow "from exploration through planning, implementation,
    verification, and shipping"; the Codex `keywords` gains `planning`,
    `knowledge-graph`, and `iwe`. `version` bumped 3.0.0 → 3.1.0 in
    `.claude-plugin`, `.codex-plugin`, and `marketplace.json` together. All
    three parse as valid JSON; `validate_agent_files` reports 43/43 valid, 0
    errors, 0 warnings. Committed with this task.

### Task 5: Repoint the operating manual and structure documents

**Files:** Modify: `docs/knowledge/AGENTS.md`, `docs/knowledge/STRUCTURE.md`,
`docs/knowledge/data/product.md`,
`docs/knowledge/data/architecture/template-boundary.md`

These are the documents that tell a session where the skills are. The workspace
skills table is the highest-value fix: it is the router, and after the move
every row points at a deleted path.

- [x] Rewrite the seven-row table in `docs/knowledge/AGENTS.md` and the setup
  reference in its start-of-session step to name `/agentdev:iwe-*` invocations
  rather than file paths, update the `.claude/skills/` line in `STRUCTURE.md`,
  correct the `.claude/` row in `template-boundary.md`, and correct both stale
  skill counts — `24 skills` in `template-boundary.md` and `24+ skills` in
  `product.md` — to the post-move total of 34, noting that both were already
  wrong: the agentdev plugin carries 27 tracked skills before this move (Task 1
  re-counted; the plan's original 23/30 predates the iwe-audit and
  iwe-implement-all skills merged since).
  - **Evidence:** The `docs/knowledge/AGENTS.md` router table now lists
    `/agentdev:iwe-{setup,explore,plan,implement,verify,ship,weekly}` and its
    start-of-session step (line 17) points at `/agentdev:iwe-setup` instead of a
    file path. `STRUCTURE.md`'s workflow-skills line names
    `.agents/plugins/agentdev/skills/iwe-*/` invoked as `/agentdev:iwe-*`.
    `template-boundary.md`'s `.claude/` row (line 98) is now accurate as written
    — it never claimed skills, and the move makes the omission correct — and its
    `.agents/` count reads "34 skills"; `product.md` reads "34 skills". The
    agentdev plugin directory holds 34 skill dirs post-move (verified by `ls`
    and `git ls-files`). No `.claude/skills` reference survives in any of the
    four documents. Committed with this task.

### Task 6: Repoint the graph document anchors

**Files:** Modify: `docs/knowledge/data/spec/iwe-workflow-skills.md`,
`docs/knowledge/data/bugs/{plan-checkbox-over-claiming,missing-map-skill}.md`,
`docs/knowledge/data/features/verification-in-the-main-loop.md`,
`docs/knowledge/data/backlog/capture-skill.md`, `docs/knowledge/data/plans/*.md`

Roughly 219 references across nineteen files (Task 1 re-counted; the earlier
"124 across fifteen" estimate predated the plans and features merged since), in
three shapes: `sources:` frontmatter entries, backticked `path:line` anchors in
prose, and prose naming the old directory. None are markdown links between graph
documents, so `iwe rename` will not touch them.

- [x] Rewrite every `.claude/skills/<name>/` reference in `docs/knowledge/data/`
  to its new plugin path, preserving each anchor's line number only where it is
  still correct and re-locating it where the move or the dependency plan shifted
  it. Leave documents in `## Done` factually intact: a shipped plan records
  where the file was when it shipped, so update its `sources:` and leave its
  prose history alone.
  - **Evidence:** The estimate was low: 219 `.claude/skills` occurrences across
    19 files (not ~124/15). All 51 `sources:` `resource:` entries — across the
    live specs, features, backlog, bugs, this active plan, and every `## Done`
    plan/bug — rewritten to
    `.agents/plugins/agentdev/skills/iwe-<name>/SKILL.md` (0 old-path
    `resource:` lines remain; all rewrites confirmed in frontmatter, none in
    prose). Live-doc prose anchors re-located and rewritten:
    `backlog/exercise-removed-delta-blocks.md` (Plan :137-138→:146-147,
    Implement :24→:25, Verify :46→:48, Ship :45,:70→:46,:71 — the dependency
    plan had shifted them) and the open bug `bugs/missing-map-skill.md` (Verify
    :51-54→:78-80, :65→:92; Setup :29-30→:30-31; anchor date restamped
    2026-09-01, `AGENTS.md:56-58` re-verified still-correct). The 137 prose
    references inside the seven `## Done` plans and the done bug
    `plan-checkbox-over-claiming.md` were left intact (git diff confirms only
    `resource:` lines changed there); this active plan's own move narrative and
    `## Key references` keep their pre-move `.claude/skills/` paths by design.
    `ci-agent-plugin-availability.md:146` is out of scope — it names a
    hypothetical vendored `.claude/skills/pr-review/`, not one of the seven
    moved IWE skills. `iwe normalize` and `iwe schema validate` exit 0.
    Committed with this task.

### Task 7: Amend the dependency plan's out-of-scope clause

**Files:** Modify:
`docs/knowledge/data/plans/20260816-structured-plan-spec-deltas.md`

That plan states "the tracked workspace source remains `.claude/skills/`" as an
out-of-scope boundary. Once it has shipped and this plan has moved the tree, the
sentence describes a layout that no longer exists and would mislead the next
session that reads it.

- [x] Amend the clause to record that the boundary applied while that plan was
  active and that this plan superseded it, without rewriting the plan's
  completed tasks or their evidence.
  - **Evidence:** The `## Out of scope` clause in
    `20260816-structured-plan-spec-deltas.md` now states the
    `.claude/skills/`-as-tracked-source boundary "held only for this plan's
    lifetime" and links this plan as the one that superseded it by relocating
    the seven skills to `.agents/plugins/agentdev/skills/iwe-*/`. No completed
    task or evidence line in that plan was touched. `iwe normalize` and
    `iwe schema validate` exit 0. Committed with this task.

### Task 8: Validate the catalog and the graph

**Files:** none

- [x] Run
  `uv run validate_agent_files --recommend . --require-marketplace claude codex`,
  `claude plugin validate ./.agents/plugins/agentdev`, `iwe normalize`, and
  `iwe schema validate`, and record the skill count reported by the validator.
  The baseline before this work is 43/43 valid with 0 errors and 0 warnings
  (Task 1 re-measured; the plan's original 45 predates skills merged since, and
  the total is unchanged by a relocation); the post-move run must be equally
  clean. The agentdev plugin holds 27 tracked skills before the move and 34
  after it.
  - **Evidence:**
    `validate_agent_files --recommend . --require-marketplace claude codex` →
    "Summary: 43/43 skills valid, Errors: 0, Warnings: 0" (unchanged by the
    relocation, as predicted).
    `claude plugin validate ./.agents/plugins/agentdev` → "✔ Validation passed".
    `iwe normalize` and `iwe schema validate` both exit 0. The agentdev plugin
    now holds 34 skill directories
    (`ls -1d .agents/plugins/agentdev/skills/*/ | wc -l` = 34). Committed with
    this task.

## Spec changes

- [Template consumption](../spec/template-consumption.md) — §7 tells a consuming
  project to "Retain `.claude/` and `.codex/`, then review them as project
  policy" and enumerates `settings.json`, `settings.local.json`, both READMEs,
  and the Codex bootstrap script. It never mentions `.claude/skills/`, so it
  understates what a consumer inherits today. After this plan the enumeration
  becomes complete as written, and the spec gains the positive statement that
  the IWE workflow skills arrive with the installed `agentdev` catalog rather
  than with the copied `.claude/` directory.
- [IWE workflow skills](../spec/iwe-workflow-skills.md) — its five `sources:`
  entries point at `.claude/skills/`. The requirements themselves are stated at
  the role level ("The Ship skill SHALL run the report-only Verify workflow"),
  which the rename does not disturb, so this is a provenance refresh and not a
  requirement change.

No other spec is affected. [Catalog lifecycle](../spec/catalog-lifecycle.md)
governs how the catalog is staged and installed, and this plan changes what the
catalog contains, not how it travels.

## Depends on

[Embed structured spec deltas in IWE plans](20260816-structured-plan-spec-deltas.md)
— it is the last planned change to the IWE skills, it rewrites Plan, Implement,
Verify, and Ship, and it declares this move out of scope while it runs. Moving
first would invalidate its verified anchors mid-execution, so this plan waits
and Task 1 re-anchors against the checkout it leaves behind.

[Split PR How to Test into Verification and Reviewer Handoff](20260815-pr-verification-sections.md)
is active and edits `agentdev` skills, but only the `pr-*` ones, and it does not
touch the plugin manifests. It shares no file with this plan and does not block
it.

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  exits 0 with no errors and no warnings; the agentdev plugin then holds 34
  skills (27 pre-move + the 7 relocated).
- `claude plugin validate ./.agents/plugins/agentdev` passes.
- `iwe normalize` then `iwe schema validate` both exit 0.
- `.claude/README.md` is re-read and confirmed accurate without edits: its table
  already lists `settings.json` as the directory's sole occupant, which becomes
  true only once the skills leave. If it needs a change, the move was
  incomplete.
- `grep -rn '\.claude/skills' . --include='*.md' --include='*.json'` returns
  only historical prose inside shipped plans and no live reference.
- Because the catalog validator inspects markdown links and not backticked
  paths, run `/agentdev:semantic-refactor-audit` over the seven relocated files:
  this is a mechanical rename claimed to be semantics-free, and its whole risk
  is that it looks correct in this checkout and behaves differently in a
  consumer's plugin cache.
- Invoke one relocated skill end to end — `/agentdev:iwe-weekly` is read-only
  and therefore the safe probe — and confirm it is discovered under its new name
  and produces its digest.

## Out of scope

- The untracked `.agents/skills/` tree, including its six generated `openspec-*`
  skills, the abandoned `iwe-plan/` copy of this move, and the empty `ship/`
  directory. Determining what generates it, whether it should be ignored, and
  whether it should be deleted is separate work.
- Publishing a distinct `iwe` plugin, the alternative rejected in `## Approach`.
- Any change to the behavior of the seven skills. Their instructions, decision
  rules, and descriptions move verbatim except for the cross-references Task 3
  names.
- Splitting the `agentdev` catalog, revisiting whether the workflow should be
  opt-in per repository, or adding an installation path for the IWE graph
  itself.

## Key references

Verified anchor points (line numbers as of 2026-09-01, re-anchored against the
checkout the dependency plans left behind):

- `.claude/skills/ship/SKILL.md:37` — the backticked
  `.claude/skills/verify/SKILL.md` invocation, the only repository path inside
  the seven skills
- `.claude/skills/implement/SKILL.md:20,63,75,76,99,102,126` — seven bare-name
  sibling references to the plan, verify, and ship skills (the dependency plan
  rewrote Implement and added references; see Task 3's corrected scope)
- `.claude/skills/explore/SKILL.md:44,66,72,85` — four bare-name sibling
  references naming the plan and implement skills
- `.claude/skills/verify/SKILL.md:28,87` — two bare-name sibling references
- `.claude/skills/ship/SKILL.md:95-97` — the only markdown link in the seven
  files, already fenced by `validate_skills: ignore-cross-reference` markers
- `docs/knowledge/AGENTS.md:214-220` — the workspace skills router table
- `docs/knowledge/AGENTS.md:17` — start-of-session reference to the setup skill
- `docs/knowledge/STRUCTURE.md:26` — `.claude/skills/` in the tree diagram
- `docs/knowledge/data/spec/iwe-workflow-skills.md:8-12` — the five `sources:`
  entries
- `docs/knowledge/data/spec/template-consumption.md:219-239` — §7's `.claude/`
  enumeration, which omits `skills/`
- `docs/knowledge/data/architecture/template-boundary.md:98` — the `.claude/`
  disposition row
- `docs/knowledge/data/architecture/template-boundary.md:194` — "four agents, 24
  skills", stale: the agentdev plugin already carries 27 tracked skills
- `docs/knowledge/data/product.md:33` — "24+ skills"
- `docs/knowledge/data/plans/20260816-structured-plan-spec-deltas.md:495-496` —
  the out-of-scope clause naming `.claude/skills/` as the tracked source
- `.claude/README.md:7-9` — the table listing `settings.json` as the directory's
  sole occupant
- `.agents/plugins/agentdev/.claude-plugin/plugin.json:3` — `version: 3.0.0`
- `.agents/plugins/agentdev/.codex-plugin/plugin.json:3` — `version: 3.0.0`
- `.claude-plugin/marketplace.json:13` — `version: 3.0.0`
- `py_packages/validate_agent_files/validate_agent_files/validators/cross_reference.py:56`
  — `link_pattern`, which matches only `[x](y)` and is why backticked paths pass
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:136,138` — the
  `/agentdev:<skill>` sibling-invocation idiom Task 3 follows
