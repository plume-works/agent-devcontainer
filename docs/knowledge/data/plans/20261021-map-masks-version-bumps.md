---
type: plan
stage: done
created: 2026-10-21
completed: 2026-10-21
description: Teach the iwe-map refresh to mask a version-only change in the colocated .agent.metadata.json, prove the mask with a new stale-map-docs.py --replay mode, and commit the mask with the digest re-stamps it explains before refreshing any prose.
release:
- features/map-masks-version-bumps
generated:
  by: opencode/gpt-6.1-sol
  at: 2026-10-21T05:18:06Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-map/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py
- resource: .agents/plugins/agentdev/tests/test_stale_map_docs_masks.py
- resource: docs/knowledge/data/spec/iwe-workflow-skills.md
---

# Mask version-only changes during a map refresh

## Context

[Map masks version-only changes](../features/map-masks-version-bumps.md) is the
feature this plan delivers. [Digest masks for map
docs](20260905-digest-masks.md) built the masking mechanism; its rules live in
`.agent.metadata.json` files per [Agent metadata
files](../architecture/agent-metadata-files.md). Nothing in the
`/agentdev:iwe-map` refresh routes a version-only change to that mechanism: step
8 tells the agent to re-read and rewrite every `STALE` doc, so a doc whose only
change is a pinned value gets a hand refresh, and the missing mask is left for
the next bump of the same kind to hit again.

Two decisions were made with the maintainer: any version-only change qualifies
for a mask whoever authored it, and the behavior runs in agent-driven refreshes
(including the pre-push refresh from [Refresh the codebase map before
pushing](20260929-map-refresh-before-push.md)), not in a CI job on
dependency-update pull requests.

## Approach

The judgment and the proof are split. The agent decides what counts as a version
and writes the rule; a new `--replay` mode of `stale-map-docs.py` proves it
mechanically against history and tells the agent which digests the rule alone
explains. SKILL.md step 8 gains a classification pass that runs before any prose
refresh and ends in one atomic commit of the metadata change plus
`source_digest` re-stamps.

Replay applies the **working-tree** metadata to historical file contents
(`git show <commit>:<path>` against its first parent), so a candidate rule is
tested before it is committed. A doc is `RESTAMP` when its recorded digest
equals the digest computed with the metadata committed at `HEAD` — the new rule
is the only difference — or when every first-parent commit since its
`verified.at` that touched its sources, plus any uncommitted change, is absorbed
by the working-tree masks. Everything else is `REFRESH`.

Rejected: recovering a doc's "before" content exactly by searching history for
the commit whose tree reproduces its recorded digest. It is exact but costs a
digest computation per candidate commit, and the `verified.at` cutoff errs only
toward `REFRESH`, which is the safe direction. Also rejected: letting the script
write the re-stamps itself. The script stays read-only; the agent applies the
`RESTAMP` digests, as it already copies `STALE` digests.

Assumption: `--since` defaults to the earliest `verified.at` across the map
docs, so the replay corpus covers every change any current doc could have
missed.

## Implementation Steps

### Task 1: Add `--replay` to `stale-map-docs.py`

**Files:** Modify:
`.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py`

- [x] `parse_arguments` accepts `--replay` and `--since <YYYY-MM-DD>`; `--since`
  without `--replay` is a `PREFLIGHT_ERROR`. `USAGE` documents both and the
  replay output lines below.
  - **Evidence:** same commit; `stale-map-docs.py --since 2026-01-01` and
    `--replay --since yesterday` both end `RESULT=PREFLIGHT_ERROR`, and
    `--replay --since 2026-10-15` reports `SINCE=2026-10-15`.
- [x] `MetadataResolver` can read metadata from the `HEAD` tree as well as the
  working tree, so replay can compute a doc's digest under committed metadata. A
  metadata file unreadable in either view is `BROKEN_METADATA`, the existing
  code.
  - **Evidence:** this correction commit;
    `test_malformed_committed_metadata_is_broken` passes for otherwise fresh,
    restamp, and refresh verdicts; the working-tree regression also passes.
    `replay_verdict` validates both metadata views before classifying a doc.
- [x] Replay walks `git log --first-parent --since=<since>` over the files the
  working-tree masks reach under any map doc's `source`, and for each
  commit/file pair whose raw content changed prints `ABSORBED <commit> <path>`
  when the masked contents are equal, else `MOVED <commit> <path>`.
  - **Evidence:** same commit; `--replay` over this repository marks `c8d0aca`
    (uv `0.13.4`) `ABSORBED` in both files it touched, among 336 `ABSORBED` and
    65 `MOVED` lines since the earliest `verified.at`.
- [x] Replay prints one `HIDDEN <metadata-path> <pattern> <value>` line per
  distinct value each mask matched across the replayed contents.
  - **Evidence:** same commit; the same run prints 360 `HIDDEN` lines across the
    four metadata files, each value once as a JSON string.
- [x] Replay prints `RESTAMP <key> <digest>` or `REFRESH <key>` for every map
  doc that is not `FRESH` under the working-tree metadata, by the rule in
  `## Approach`, then `ABSORBED_COUNT`, `MOVED_COUNT`, `RESTAMP_COUNT`,
  `REFRESH_COUNT`, and `RESULT`. Replay uses the existing result codes:
  `SUCCESS` when it ran to completion, whatever it found.
  - **Evidence:** same commit; the same run ends `RESULT=SUCCESS` with `REFRESH`
    for the two `agents/plugins/agentdev` map docs whose source this commit
    edits.

### Task 2: Test replay

**Files:** Create:
`.agents/plugins/agentdev/tests/test_stale_map_docs_replay.py`

- [x] Reuse `build_workspace`, `commit_file`, `write_map_doc`, and `run_script`
  from `test_stale_map_docs.py` and `write_metadata` from
  `test_stale_map_docs_masks.py`; fixtures use made-up paths and images.
  - **Evidence:** same commit;
    `.agents/plugins/agentdev/tests/test_stale_map_docs_replay.py` imports those
    helpers and `BUMPED_PIN`/`PIN`/`compose_text`/`current_digest`/`digest_mask`
    from the mask suite, with `deploy/` and `example.invalid` fixtures.
- [x] A doc stale only from a pin bump, with a new uncommitted rule covering it,
  is `RESTAMP` with the digest a plain run computes afterwards, and the bump
  commit is `ABSORBED`.
  - **Evidence:** same commit;
    `test_a_doc_stale_only_from_a_pin_bump_is_restamped` passes.
- [x] A doc already fresh that the new rule reaches is `RESTAMP` (the
  committed-metadata branch of the rule).
  - **Evidence:** same commit;
    `test_a_fresh_doc_the_new_rule_reaches_is_restamped` passes with no
    `verified` in the doc, so only the HEAD-metadata branch can restamp it.
- [x] A doc whose sources also changed outside the rule since `verified.at` is
  `REFRESH`, and that commit is `MOVED`.
  - **Evidence:** same commit;
    `test_a_change_outside_the_rule_is_moved_and_refreshed` passes, and fails
    when `Replayer.explains` is forced to return True.
- [x] An uncommitted unmasked source edit makes the doc `REFRESH`.
  - **Evidence:** same commit;
    `test_an_uncommitted_unmasked_edit_forces_a_refresh` passes, and fails under
    the same forced `explains`.
- [x] `HIDDEN` lists every distinct matched value once.
  - **Evidence:** same commit; `test_hidden_lists_each_distinct_value_once`
    passes.
- [x] `--since` without `--replay` ends `PREFLIGHT_ERROR`; replay over a
  malformed working-tree metadata file ends `BROKEN_METADATA`.
  - **Evidence:** same commit; `test_since_without_replay_is_a_preflight_error`
    and `test_malformed_working_tree_metadata_is_broken` pass.

### Task 3: Route version-only changes in SKILL.md

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-map/SKILL.md`

- [x] Step 8 opens with a classification pass before the per-verdict list: for
  each `STALE` doc, read `git log -p --first-parent --since=<verified.at>` over
  its `source` and sort the change as version-only (every changed span a
  version, digest, or pin value, nothing around it moved, and the doc does not
  quote the old value) or not.
  - **Evidence:** same commit; step 8 opens with **Mask version-only changes
    first**, which reads `git log -p --first-parent --since=<verified.at>` and
    `git diff HEAD` over the source and defines version-only, including the
    quoted-value exclusion.
- [x] For version-only changes: add or widen a `digest_ignore` rule in the
  nearest `.agent.metadata.json` whose directory covers every file holding that
  kind of value, with a `reason` naming what moves it; run
  `agent-code/stale-map-docs.py --replay`; keep the rule only if every
  `ABSORBED` commit is version-only and every `HIDDEN` value is version-shaped;
  apply each `RESTAMP` digest to `source_digest` and nothing else; commit the
  metadata files and re-stamps alone, with a message like
  `map: mask <kind> in <dir>`; rerun the check and refresh only what is still
  stale.
  - **Evidence:** same commit; that pass's numbered steps 1-4 place the rule,
    gate it on `--replay`'s `ABSORBED` and `HIDDEN` lines, apply `RESTAMP`
    digests to `source_digest` only, and commit them alone as
    `map: mask <kind> in <dir>` before rerunning the check.
- [x] The finish of step 8 reports each masked kind whose rule also hides
  major-version changes.
  - **Evidence:** same commit; step 8's finish names every added mask and each
    masked kind that hides a major-version change.
- [x] `## Script results` documents `--replay`, its line types, and that its
  `SUCCESS` means "ran", not "nothing to do".
  - **Evidence:** same commit; `## Script results` gains the `--replay` line
    table and states that its `SUCCESS` means "ran"; `validate_agent_files`
    reports 62/62 skills valid.

### Task 4: Validate the catalog and suite

**Files:** none

- [x] `uv run pytest .agents/plugins/agentdev/tests` passes.
  - **Evidence:** this commit, at `58f2037`;
    `uv run pytest .agents/plugins/agentdev/tests` passes 182 tests.
- [x] `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes.
  - **Evidence:** this commit, at `58f2037`; the validator reports 62/62 skills
    valid with 0 errors and 0 warnings.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) — a new requirement; it
governs when a staleness signal may be silenced, so it is a delta.

``` markdown
## ADDED Requirements

### Requirement: Map masks a version-only change before refreshing

When a refresh finds a map document stale and every change under its `source`
since it was verified is a version, digest, or pin value whose surrounding
structure is unchanged, the Map skill SHALL mask that kind of value in the
colocated `digest_ignore` designation, SHALL keep the mask only when replaying
it over history absorbs no change other than version-only ones, SHALL re-stamp
`source_digest` only on documents the new mask alone explains, and SHALL commit
the designation change and those re-stamps together before refreshing any
document's prose.

#### Scenario: A version-only change re-stamps instead of refreshing

- **WHEN** a map document is stale only because a pinned value moved
- **THEN** the refresh commits a mask for that kind of value and the
  document's new `source_digest`, without editing the document's body
- **AND** the staleness check then reports the document `FRESH`

#### Scenario: A mixed change is masked first and refreshed after

- **WHEN** a change under a document's `source` moves a pinned value and also
  changes described content
- **THEN** the mask lands in its own commit first
- **AND** the document is refreshed for the remaining change

#### Scenario: A document stale for another reason is not re-stamped

- **WHEN** a new mask reaches a document whose sources also changed outside
  that mask since it was verified
- **THEN** replay reports the document `REFRESH`
- **AND** its `source_digest` is left for the prose refresh to update

#### Scenario: A quoted value is not masked away

- **WHEN** the document quotes the value that moved
- **THEN** the change is not version-only for that document and it is refreshed

#### Scenario: The report names hidden major bumps

- **WHEN** a mask added by the refresh also hides major-version changes of the
  value it covers
- **THEN** the run's report names that kind of value
```

## Verification

- Task 2 tests pass:
  `uv run pytest .agents/plugins/agentdev/tests/test_stale_map_docs_replay.py`.
- The existing mask suite still passes:
  `uv run pytest .agents/plugins/agentdev/tests/test_stale_map_docs_masks.py .agents/plugins/agentdev/tests/test_stale_map_docs.py`.
- In this repository, `stale-map-docs.py --replay` with the committed metadata
  ends `RESULT=SUCCESS`, reports `RESTAMP_COUNT=0` and `REFRESH_COUNT=0` on a
  fresh map, and lists `ABSORBED` lines for the automerged bump commits since
  the earliest `verified.at` (for example `c8d0aca`, the uv `0.13.4` bump).
- A plain `stale-map-docs.py` run still ends `RESULT=SUCCESS`; its output is
  unchanged without `--replay`.

## Verification results

Correction verification (this commit): all 185 plugin tests pass, including 10
replay tests and 24 existing staleness/mask tests. Catalog validation passes
with zero errors or warnings. The plain check reports all 28 docs fresh; replay
ends `RESULT=SUCCESS` with 336 absorbed changes and zero restamps, refreshes, or
broken docs. Committed-metadata regressions require `BROKEN_METADATA` even when
the working-tree metadata has been repaired.

At `dc890e2`:

- `test_stale_map_docs_replay.py`: 7 passed. `test_stale_map_docs_masks.py` with
  `test_stale_map_docs.py`: 24 passed.
- `stale-map-docs.py --replay` with the committed metadata reads from
  `SINCE=2026-09-07T23:43:50Z`, reports 336 `ABSORBED` and 65 `MOVED` lines,
  `RESTAMP_COUNT=0`, `REFRESH_COUNT=0`, `BROKEN_COUNT=0`, and ends
  `RESULT=SUCCESS`; both files `c8d0aca` touched are `ABSORBED`.
- A plain run ends `RESULT=SUCCESS`. Its stdout, with and without `--explain`,
  is byte-identical to the script at `6b1ea4e` run over the same tree.

## Out of scope

- A CI job or bot that masks or re-stamps on dependency-update pull requests.
- Restricting automatic masks to bot-authored changes.
- Writing frontmatter from the script; the agent applies `RESTAMP` digests.
- Changing how masks are declared, resolved, or folded into a digest.

## Key references

Verified anchor points (line numbers as of 2026-10-21):

- `.agents/plugins/agentdev/skills/iwe-map/SKILL.md:122` — step 8, refresh mode
- `.agents/plugins/agentdev/skills/iwe-map/SKILL.md:168` — step 8's finish
- `.agents/plugins/agentdev/skills/iwe-map/SKILL.md:173` — `## Script results`
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:26` —
  `USAGE`
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:280` —
  `MetadataResolver`
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:299` —
  `MetadataResolver._for_directory`, the working-tree metadata read
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:355` —
  `masked_hash`
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:364` —
  `source_digest_for_paths`
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:408` —
  `fold_in_masks`
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:444` —
  `parse_arguments`
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:487` —
  `classify`
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:688` —
  `main`
- `.agents/plugins/agentdev/tests/test_stale_map_docs.py:43` — `commit_file`
- `.agents/plugins/agentdev/tests/test_stale_map_docs.py:65` — `build_workspace`
- `.agents/plugins/agentdev/tests/test_stale_map_docs.py:79` — `write_map_doc`
- `.agents/plugins/agentdev/tests/test_stale_map_docs.py:86` — `run_script`
- `.agents/plugins/agentdev/tests/test_stale_map_docs_masks.py:33` —
  `write_metadata`
- `docs/knowledge/data/spec/iwe-workflow-skills.md:507` — Requirement: Map
  staleness reflects described content
