---
type: plan
description: Mask machine-managed content out of source_digest so an automerged pin bump stops marking map docs stale.
created: 2026-09-05
generated:
  by: claude-code/opus-5
  at: 2026-09-05T00:00:00Z
---

# Digest masks for map docs

## Context

[Pin bumps invalidate map docs](../bugs/pin-bumps-invalidate-map-docs.md)
records the defect: `source_digest` fingerprints whole tracked files, so an
automerged Renovate bump of an image digest or a tool version marks map docs
stale whose prose is entirely accurate.

## Approach

Filter what the digest covers before hashing. The masks live in
`.agent.metadata.json` files colocated with the sources they describe, under an
`iwe-map.digest_ignore` key — the format and its resolution rules are
[Agent metadata files](../architecture/agent-metadata-files.md), of which this
is the first consumer.

Resolving a source file walks from the repository root down to that file's own
directory, accumulating every `.agent.metadata.json` on the way, shallowest
first. Globs are relative to the directory declaring them, so
`.github/.agent.metadata.json` matching `**/*.yml` covers every workflow and
action below it and keeps working if `.github/` is copied elsewhere.

**Substitution, not deletion.** Each pattern carries a replacement, so a match
becomes a fixed placeholder rather than vanishing. That keeps file structure
under surveillance: adding a service to the compose pins, changing the image
name, or dropping the pin line still moves the digest — only the pinned value
stops mattering.

A mask edit invalidates the docs it actually reaches, not the whole lane. Each
doc's digest folds in only the masks that matched at least one of that doc's own
source files, so editing the `.github` entry marks the three docs claiming
`.github` stale and leaves the rest alone.

A metadata file that cannot be read makes the subtree containing it
unresolvable, and every map doc whose sources reach that file reports `BROKEN`
rather than a freshness verdict. That is a new verdict rather than `STALE`: a
doc whose masks failed to load has unknown freshness, and telling a session to
re-verify prose would send it to fix the wrong thing.

Rejected alternatives to the metadata-file format — a single repository-level
map, replace-instead-of-accumulate precedence, and repository-root-relative
globs — are recorded in
[Agent metadata files](../architecture/agent-metadata-files.md). Alternatives to
masking itself:

- **Per-doc `digest_ignore` frontmatter.** The rule "a compose pin's digest is
  machine-managed" is a property of the file, not of a doc. Per-doc, it is
  written once per claiming doc — twice for the compose pins, three times for
  `.github` — five copies of two facts that then drift. Directory-scoped
  `source` makes it worse: `github` claims all of `.github` without naming the
  file whose pin churns, so a per-doc entry needs a path scope anyway.
- **Skipping Renovate-authored commits.** Hides a real signal; a major-version
  bump genuinely can invalidate a doc.
- **Narrowing `source` fields.** Helps the `.github` fan-out but not
  `devcontainer-compose-pins.yml`, which is legitimately described content that
  happens to hold a digest.

## Implementation Steps

### Task 1: Declare the masks beside the sources they describe

**Files:** Create: `.agent.metadata.json`; `.github/.agent.metadata.json`

- [x] Write the repository-root file for the compose pin. Globs are relative to
  the file's own directory, so `devcontainer-compose-pins.yml` names the pin
  file at the root without a path.
  - **Evidence:** `.agent.metadata.json` at the repository root; its pattern
    matches the `@sha256:` pin in `devcontainer-compose-pins.yml` once, leaving
    the image name and tag in place.

``` json
{
  "iwe-map": {
    "digest_ignore": {
      "devcontainer-compose-pins.yml": [
        {
          "pattern": "@sha256:[0-9a-f]{64}",
          "replace": "@sha256:<PIN>",
          "reason": "Renovate automerges agent-desktop digest bumps (.github/renovate.json)."
        }
      ]
    }
  }
}
```

- [x] Write the `.github` file. Its globs are relative to `.github/`, and the
  walk reaches every workflow and action below it, so one entry serves `github`,
  `github/actions`, and `flow-pull-request-checks`. Both the pinned action
  reference and the pinned tool version churn, so both are masked; `reason` is a
  field, printed by `--explain`.
  - **Evidence:** `.github/.agent.metadata.json`; against
    `actions/setup-python-venv/action.yml` the action-reference pattern masks
    two `uses:` pins and the tool-version pattern masks one `version:` input,
    each keeping the action name it qualifies.

``` json
{
  "iwe-map": {
    "digest_ignore": {
      "**/*.yml": [
        {
          "pattern": "(uses: [^@\\s]+)@v[0-9]+(\\.[0-9]+)*",
          "replace": "\\1@v<PIN>",
          "reason": "Renovate automerges github-actions version bumps (.github/renovate.json)."
        },
        {
          "pattern": "version: '[0-9]+\\.[0-9]+\\.[0-9]+'",
          "replace": "version: '<PIN>'",
          "reason": "Tool versions pinned to actions, bumped by the same automerge."
        }
      ]
    }
  }
}
```

### Task 2: Resolve metadata files along the walk

**Files:** Modify:
`.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py`

- [x] For a tracked file being hashed, walk from `git rev-parse --show-toplevel`
  down to that file's own directory, reading each `.agent.metadata.json` found
  and taking its `iwe-map.digest_ignore` object. A file with no such key
  contributes nothing and is not an error.
  - **Evidence:** `MetadataResolver._for_directory` walks root-to-leaf and
    caches per directory; `read_metadata` returns `[]` for a file without the
    key. `test_a_parent_rule_reaches_a_subdirectory_and_a_child_adds_to_it`
    passes.
- [x] Accumulate shallowest first: a deeper file's entries are appended to its
  ancestors', never substituted for them. Within the resulting list, patterns
  apply in order, so a deeper rule transforms what a shallower one left.
  - **Evidence:**
    `test_a_parent_rule_reaches_a_subdirectory_and_a_child_adds_to_it` — the
    parent's digest rule and the child's build-number rule both apply to the
    same file, which a replace implementation would fail.
- [x] Match each glob against the candidate file's path *relative to the
  directory declaring it*, so a copied directory's rules keep working. `**`
  crosses directory separators and a single `*` does not, matching the pathspec
  semantics the `source` fields already assume; `fnmatch` does not make that
  distinction, so it is not the matcher to reach for.
  - **Evidence:** `glob_to_regex` compiles `**` to cross separators and `*` to
    stop at one; `test_globs_match_relative_to_the_declaring_directory` copies
    the same rules to two depths and both mask their own relative paths.
- [x] A file no glob matches keeps its `git hash-object` value unchanged, so
  digests for unmasked sources stay identical to the ported script's, and a
  repository with no metadata files behaves exactly as before.
  - **Evidence:** `test_absent_metadata_reproduces_the_unmasked_digest` asserts
    the digest equals the unmasked `git hash-object` fold; the 48 pre-existing
    plugin tests pass unchanged.

### Task 3: Mask matched content before hashing

**Files:** Modify:
`.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py`

- [x] A matched file is read, each pattern applied with `re.sub` in resolution
  order, and the result hashed with sha256. The masked content is hashed, never
  written back to the worktree.
  - **Evidence:** `masked_hash` substitutes into an in-memory string and hashes
    it; no write path exists. `test_a_masked_pin_bump_leaves_the_doc_fresh`
    passes.
- [x] Fold the applied masks into the doc's digest: each doc's hash includes the
  `{pattern, replace}` of every mask that matched at least one of its own source
  files, so editing a mask invalidates the docs that mask reaches and no others.
  - **Evidence:** `fold_in_masks` folds in only masks recorded as applied;
    `test_editing_a_mask_invalidates_only_the_docs_it_reaches` shows the masked
    doc go STALE and an unrelated doc stay FRESH.
- [x] Add `--explain`, printing one line per applied mask naming the doc key,
  the file, the glob, the declaring metadata file, and the `reason`. A mask that
  is too broad makes a doc permanently `FRESH` — the check stops firing on real
  changes, which is worse than the false staleness it replaced — so a `FRESH`
  verdict reached through masking must be auditable.
  - **Evidence:** `test_explain_names_the_mask_its_source_and_its_reason`
    asserts the exact MASK line; on this checkout `--explain` names each mask's
    doc, source file, declaring metadata file, pattern, and reason.
- [x] Keep `RESULT=` last on stdout with `--explain` active, and leave the
  default output unchanged so the existing verdict lines stay stable.
  - **Evidence:** the same test asserts `lines[-1] == 'RESULT=SUCCESS'` with
    `--explain`; the 9 pre-existing `test_stale_map_docs.py` cases pass with
    assertions unchanged.

### Task 4: Report an unresolvable subtree as its own verdict

**Files:** Modify:
`.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py`

- [x] A `.agent.metadata.json` that is unparseable, whose `digest_ignore` is
  malformed, or that holds an uncompilable pattern makes its directory subtree
  unresolvable. Every doc whose sources reach that file emits
  `BROKEN <key> <metadata-path>` and is counted separately; docs whose walks
  never enter that subtree are unaffected and keep their normal verdicts.
  - **Evidence:**
    `test_an_unparseable_metadata_file_breaks_only_its_own_subtree` and
    `test_an_uncompilable_pattern_is_broken_metadata` pass. `classify` calls
    `MetadataResolver.verify` for every doc, so a broken file is reported on the
    legacy commit path too, not only the digest path.
- [x] Register `5=BROKEN_METADATA` in the code-to-name mapping
  `bin/result_codes.py` provides, alongside the `3=STALE_FOUND` and
  `4=NO_MAP_DOCS` the ported script already declares. 5 is the next free code:
  `bin/result-codes.sh:5-14` reserves 0, 1, 2, 129, 130 and 143 and leaves 3
  through 125 to the script, and this script has taken 3 and 4.
  - **Evidence:** `rc.RESULT_CODES[BROKEN_METADATA] = 'BROKEN_METADATA'` beside
    the existing two registrations; the broken-metadata tests observe
    `RESULT=BROKEN_METADATA`.
- [x] Exit `5` when any doc is `BROKEN`, in preference to `3`. A broken subtree
  means some verdicts were not computed, so it outranks a staleness the run may
  have only partly established.
  - **Evidence:** the exit selection returns `BROKEN_METADATA` before
    `STALE_FOUND`; both broken-metadata tests assert exit 5, and
    `test_an_unparseable_metadata_file_breaks_only_its_own_subtree` has a stale
    doc present at the same time.
- [x] Add `BROKEN_COUNT` to the `KEY=VALUE` block and document the verdict and
  the result code in the script's usage text, beside `STALE` and `NO_MAP_DOCS`.
  - **Evidence:** `BROKEN_COUNT` prints after `EXPIRED_COUNT`; the usage text
    documents the `BROKEN` line, the `MASK` line, `--explain`, `BROKEN_COUNT`,
    and `BROKEN_METADATA 5`.

### Task 5: Test the resolution and masking behavior

**Files:** Create: `.agents/plugins/agentdev/tests/test_stale_map_docs_masks.py`

- [x] A fixture repository where a masked pin changes and the doc stays `FRESH`;
  the same repository where an unmasked line in the same file changes and the
  doc goes `STALE`.
  - **Evidence:** `test_a_masked_pin_bump_leaves_the_doc_fresh` and
    `test_an_unmasked_change_in_the_same_file_marks_the_doc_stale`.
- [x] A change to the *structure* around a masked value — a second service, a
  changed image name, a deleted pin line — marks the doc `STALE`, proving
  substitution keeps structure tracked where deletion would not.
  - **Evidence:**
    `test_structural_change_around_a_masked_value_is_still_staleness` covers all
    three changes and asserts `STALE_FOUND` for each.
- [x] A rule declared in a parent directory reaches a file in a subdirectory,
  and a child `.agent.metadata.json` declaring its own rule leaves the parent's
  still applying — the accumulate semantics, which a replace implementation
  would fail.
  - **Evidence:**
    `test_a_parent_rule_reaches_a_subdirectory_and_a_child_adds_to_it`.
- [x] A glob is matched relative to the directory declaring it: the same
  metadata file copied to a different depth masks the same relative paths.
  - **Evidence:** `test_globs_match_relative_to_the_declaring_directory` writes
    identical rules at `shallow/` and `nested/deeper/` and both docs stay
    `FRESH` after a pin bump.
- [x] Absent metadata files reproduce the unmasked digest exactly, so a
  repository that adopts none of this behaves as the ported script does.
  - **Evidence:** `test_absent_metadata_reproduces_the_unmasked_digest`.
- [x] An unparseable metadata file makes docs whose sources reach it emit
  `BROKEN` and exit `5`, while a doc in an unrelated subtree still reports its
  normal verdict.
  - **Evidence:**
    `test_an_unparseable_metadata_file_breaks_only_its_own_subtree` asserts the
    BROKEN line, `FRESH data/codebase/timer`, and `BROKEN_COUNT=1`.
- [x] Editing a mask entry marks the docs whose sources it matches `STALE` and
  leaves an unrelated doc `FRESH`.
  - **Evidence:** `test_editing_a_mask_invalidates_only_the_docs_it_reaches`.
- [x] Keep the fixtures independent of this repository's identity, as
  `conftest.py:21-24` establishes for the suite.
  - **Evidence:** the fixtures build their own repositories through
    `build_workspace` with invented paths (`deploy/`, `stack/`,
    `example.invalid/app`) and resolve the script through the `plugin_root`
    fixture.

### Task 6: Re-bump the digests the masks change

**Files:** Modify: `docs/knowledge/data/codebase/*.md` (only those whose digest
moves)

- [x] Run the script and re-record `source_digest` for every doc whose value
  changed because a mask now applies. This is a one-time mechanical re-bump: the
  described code has not changed, so `verified`, `stale_after`, and the prose
  stay as they are.
  - **Evidence:** six docs re-bumped — `devcontainer`, `flow-image-build`,
    `flow-pull-request-checks`, `github`, `github/actions`, and
    `github/workflows` — identified by comparing each doc's masked and unmasked
    digest, so only mask-caused movement was re-recorded. Only the
    `source_digest` line changed in each.
- [x] Rerun until `RESULT=SUCCESS`, which `iwe-map/SKILL.md:229` requires before
  any map commit.
  - **Evidence:** `stale-map-docs.py` ends `RESULT=SUCCESS` with `DOC_COUNT=26`,
    `FRESH_COUNT=26`, and every other count zero. The six docs stale for content
    reasons were refreshed through the map skill's refresh mode, which re-read
    their sources and re-stamped `verified`.

### Task 7: Document the mechanism where the map skill is specified

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-map/SKILL.md`;
`docs/knowledge/data/spec/iwe-workflow-skills.md`

- [x] Extend the `source_digest` paragraph at `iwe-map/SKILL.md:203` to state
  that machine-managed content is masked before hashing, and point at
  [Agent metadata files](../architecture/agent-metadata-files.md) for where the
  masks live and how they resolve. Add `--explain` and the `BROKEN` verdict to
  the script's documented interface.
  - **Evidence:** the `source_digest` paragraph now states the placeholder
    normalization and names the `iwe-map.digest_ignore` key and the
    agent-metadata-files document in prose — a plugin file cannot link outside
    the plugin root. `--explain` is documented in the Script results intro and
    `BROKEN_METADATA 5` is a row in the results table.
- [x] State the durable rule in `data/spec/iwe-workflow-skills.md`: the map
  skill's staleness check reflects described content, and a change confined to
  masked machine-managed values is not staleness. The metadata files are the
  mechanism; the spec carries the requirement.
  - **Evidence:** `### Requirement: Map staleness reflects described content`
    added to `data/spec/iwe-workflow-skills.md` with all four scenarios from the
    plan's delta; `iwe schema validate` passes.

### Task 8: Close the bug

**Files:** Modify: `docs/knowledge/data/bugs/pin-bumps-invalidate-map-docs.md`

- [x] Set `stage: done` once Tasks 1-7 are complete and the reproduction no
  longer reproduces. The bug's link stays under `data/bugs.md`; the status chip
  is what changes.
  - **Evidence:** `stage: done` set via `iwe update`; the link is unmoved, and
    `data/bugs.md` has no status sections to move it between. Replaying the
    reproduction — a compose digest bump and a `setup-uv` version bump applied
    together — leaves all 26 docs `FRESH` at `RESULT=SUCCESS`, where it
    previously marked five stale.

## Spec changes

`data/spec/iwe-workflow-skills.md` — the map lane's staleness contract gains a
statement about masked content and a verdict for designations it cannot read.
The change is contract behavior a future session must not silently reverse, so
it carries a full delta.

``` markdown
## ADDED Requirements

### Requirement: Map staleness reflects described content

The codebase-map staleness check SHALL classify a map document by whether the
content it describes changed, not by whether any byte under its `source`
changed. Content designated machine-managed SHALL be normalized to a fixed
placeholder before the source fingerprint is computed.

#### Scenario: An automerged pin bump leaves the document fresh

- WHEN a dependency-update commit changes only a pinned value designated
  machine-managed under a map document's `source`
- THEN the staleness check reports that document as `FRESH`

#### Scenario: A structural change around a masked value is still staleness

- WHEN a commit changes the structure holding a masked value — the identity of
  the pinned artifact, the set of pinned entries, or the presence of the pin
- THEN the staleness check reports the document as `STALE`

#### Scenario: Changing the mask set invalidates the documents it reaches

- WHEN the mask designations change
- THEN the staleness check reports as `STALE` every document with a source file
  the changed designation matches, and reports the remaining documents
  unchanged

#### Scenario: An unreadable designation breaks only its own subtree

- WHEN a mask designation cannot be read or a pattern cannot be compiled
- THEN the check reports every document whose sources reach that designation as
  broken, naming it, rather than computing a fingerprint from unmasked content
- AND documents whose sources do not reach it keep their normal verdicts
```

## Depends on

[Python skill scripts](20260905-python-skill-scripts.md) — Tasks 2 through 4
modify `stale-map-docs.py`, which that plan creates. Every task here assumes the
Python port has landed and is proven digest-identical, so that a digest that
moves in Task 6 is attributable to a mask and nothing else.

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_stale_map_docs_masks.py`
  passes.
- `uv run pytest .agents/plugins/agentdev/tests/test_stale_map_docs.py` still
  passes unchanged — masking is additive, and a repository with no
  `.agent.metadata.json` behaves exactly as before.
- The bug's reproduction is replayed: with the masks in place, the three commits
  named in
  [Pin bumps invalidate map docs](../bugs/pin-bumps-invalidate-map-docs.md) no
  longer mark `devcontainer`, `flow-image-build`, `github`, `github/actions`, or
  `flow-pull-request-checks` stale.
- `stale-map-docs.py --explain` names a mask, its declaring metadata file, and
  its `reason` for each doc whose `FRESH` verdict depends on one.
- Corrupting `.github/.agent.metadata.json` reports the docs claiming `.github`
  as `BROKEN` with exit `5`, and leaves `ansible` and `py_packages/*` reporting
  their normal verdicts; restoring it returns the run to `RESULT=SUCCESS`.
- `stale-map-docs.py` ends `RESULT=SUCCESS` on the current checkout after Task
  6.
- `uv run ruff check` and `uv run ruff format --check` pass; Prettier accepts
  both `.agent.metadata.json` files.

## Out of scope

- Consumers of `.agent.metadata.json` other than `iwe-map.digest_ignore`. The
  format is general by design, but this plan adds exactly one key and no
  registry, discovery command, or schema for the rest.
- An unignore or negation operation.
  [Agent metadata files](../architecture/agent-metadata-files.md) records that
  accumulation has no removal step; adding one is a new decision.
- Masking anything outside `data/codebase/` digests. `verified`, `stale_after`,
  and the legacy `commit` fallback are untouched.
- Renovate configuration. `.github/renovate.json` keeps automerging both
  classes; this plan changes what the staleness check concludes about them, not
  what lands.
- Narrowing the directory-scoped `source` fields that widen the blast radius.
  Still a live option, and independent of this one.

## Key references

Verified anchor points (line numbers as of 2026-09-06):

- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py:123-138` —
  `source_digest_for_paths`, the whole-file fingerprint the masks filter
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py:175-215` —
  `classify`, the per-document verdict function the `BROKEN` verdict joins,
  alongside `GONE`
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py:59-60` —
  the `STALE_FOUND = 3` and `NO_MAP_DOCS = 4` constants, the two codes already
  taken, which is why the new verdict is `5`
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py:48-56` —
  the usage block's result table Task 4 extends
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py:265-273` —
  the counter block and the exit selection the new code slots into
- `.agents/plugins/agentdev/bin/result-codes.sh:5-14` — the contract reserving
  0, 1, 2, 129, 130, 143 and assigning 3 through 125 to the script
- `.agents/plugins/agentdev/skills/iwe-map/SKILL.md:203` — the `source_digest`
  paragraph Task 7 extends
- `.agents/plugins/agentdev/skills/iwe-map/SKILL.md:229` — the
  `RESULT=SUCCESS`-before-commit rule Task 6 must satisfy
- `.agents/plugins/agentdev/tests/conftest.py:21-24` — `plugin_root`, the
  fixture keeping the suite independent of this repository
- `.github/renovate.json:9-27` — the two automerged bump classes
- `devcontainer-compose-pins.yml:14` — the `@sha256:` pin the root file's mask
  targets
- `.github/actions/setup-python-venv/action.yml:22-24` — the `setup-uv@v10.0.1`
  reference and its `version: '0.12.10'` input, both masked by the `.github`
  file
- `docs/knowledge/data/codebase/devcontainer.md:4-6` — a directory-scoped
  `source` listing the pin file
- `docs/knowledge/data/architecture/template-boundary.md:19-25` — the
  classification a colocated metadata file inherits from its directory
