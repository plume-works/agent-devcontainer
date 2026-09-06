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
stale whose prose is entirely accurate. Three such commits marked five of
twenty-six docs stale, and none of the five quotes a value that changed.

Renovate automerges both classes, so the lane goes amber with no human in the
loop. A staleness signal that fires without a real change is one the next
session learns to skip, and skipping it is how a genuine structural drift gets
missed.

## Approach

Filter what the digest covers before hashing. A repository-level map at
`docs/knowledge/digest-masks.json` binds a glob to the patterns masked out of
files matching it: `devcontainer-compose-pins.yml` masks its `@sha256:` pin,
`.github/**/*.yml` masks the pinned tool versions across every workflow and
action in one entry.

**Substitution, not deletion.** Each pattern carries a replacement, so a match
becomes a fixed placeholder rather than vanishing. That keeps file structure
under surveillance: adding a service to the compose pins, changing the image
name, or dropping the pin line still moves the digest — only the pinned value
stops mattering.

The map lives beside `data/`, not in it. `data/` is an OKF v0.2 bundle where
every document carries frontmatter with a non-empty `type` and IWE resolves keys
as Markdown; a bare `.json` inside it would be invisible to `iwe find` and
`iwe tree`, unlinkable from `data/codebase.md`, and a conformance exception. As
a sibling of `data/` it joins `.markdownlint.yml` and `tests/` — files that
govern the library without being documents in it. JSON rather than YAML because
`json` is stdlib: a consuming repository that receives the skill through
`template-consume` needs no third-party parser.

A mask edit invalidates the docs it actually reaches, not the whole lane. Each
doc's digest folds in only the masks that matched at least one of that doc's own
source files, so editing the `.github/**/*.yml` entry marks the three docs
claiming `.github` stale and leaves the rest alone.

Rejected alternatives, in the shape the bug records them:

- **Per-doc `digest_ignore` frontmatter.** The rule "a compose pin's digest is
  machine-managed" is a property of the file, not of a doc. Per-doc, it is
  written once per claiming doc — twice for the compose pins, three times for
  `.github` — five copies of two facts that then drift. Directory-scoped
  `source` makes it worse: `github` claims all of `.github` without naming the
  file whose pin churns, so a per-doc entry needs a path scope anyway, which is
  this map sharded across docs.
- **Skipping Renovate-authored commits.** Hides a real signal; a major-version
  bump genuinely can invalidate a doc.
- **Narrowing `source` fields.** Helps the `.github` fan-out but not
  `devcontainer-compose-pins.yml`, which is legitimately described content that
  happens to hold a digest.

## Implementation Steps

### Task 1: Add the mask map

**Files:** Create: `docs/knowledge/digest-masks.json`

- [ ] Write the map as a `masks` object keyed by glob, each value a list of
  `{pattern, replace, reason}` objects. `reason` is a field rather than a
  comment because JSON has none, and because the script prints it. Regexes carry
  JSON's doubled backslashes.

``` json
{
  "masks": {
    "devcontainer-compose-pins.yml": [
      {
        "pattern": "@sha256:[0-9a-f]{64}",
        "replace": "@sha256:<PIN>",
        "reason": "Renovate automerges agent-desktop digest bumps (.github/renovate.json)."
      }
    ],
    ".github/**/*.yml": [
      {
        "pattern": "version: '[0-9]+\\.[0-9]+\\.[0-9]+'",
        "replace": "version: '<PIN>'",
        "reason": "setup-uv and peers; Renovate automerges github-actions bumps."
      }
    ]
  }
}
```

### Task 2: Mask file content before hashing

**Files:** Modify:
`.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py`

- [ ] Load `<library>/digest-masks.json` when present; its absence is not an
  error, and an absent file leaves every digest exactly as the port computes it
  today.
- [ ] For each tracked file, collect the mask entries whose glob matches its
  repository-relative path. Match with `git ls-files -- <glob>` pathspec
  semantics so `**` crosses directories the way `source` fields already expect.
- [ ] A file no glob matches keeps its `git hash-object` value unchanged, so
  digests for unmasked sources stay identical to the ported script's.
- [ ] A matched file is read, each pattern applied with `re.sub` in the order
  listed, and the result hashed with sha256 — the masked content is hashed,
  never written back to the worktree.
- [ ] Fold the applied masks into the doc's digest: each doc's hash includes the
  `{pattern, replace}` of every mask that matched at least one of its own source
  files, so editing a mask invalidates the docs that mask reaches and no others.
- [ ] A malformed `digest-masks.json` or an uncompilable pattern is a
  `PREFLIGHT_ERROR` naming the offending key on stderr. Failing loudly beats
  silently hashing unmasked content, which would mark the whole lane stale with
  no stated cause.

### Task 3: Report which masks fired

**Files:** Modify:
`.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.py`

- [ ] Add `--explain`, printing one line per applied mask naming the doc key,
  the file, the glob, and the `reason`. A mask that is too broad makes a doc
  permanently `FRESH` — the check stops firing on real changes, which is worse
  than the false staleness it replaced — so a `FRESH` verdict reached through
  masking must be auditable.
- [ ] Keep `RESULT=` last on stdout with `--explain` active, and leave the
  default output unchanged so the existing verdict lines stay stable.

### Task 4: Test the masking behavior

**Files:** Create: `.agents/plugins/agentdev/tests/test_stale_map_docs_masks.py`

- [ ] A fixture repository where a masked pin changes and the doc stays `FRESH`;
  the same repository where an unmasked line in the same file changes and the
  doc goes `STALE`. This pair is the plan's central claim.
- [ ] A change to the *structure* around a masked value — a second service, a
  changed image name, a deleted pin line — marks the doc `STALE`, proving
  substitution keeps structure tracked where deletion would not.
- [ ] A glob spanning a directory (`.github/**/*.yml`) masks a file in a
  subdirectory, covering the pathspec semantics Task 2 depends on.
- [ ] Absent `digest-masks.json` reproduces the unmasked digest exactly;
  malformed JSON and an uncompilable pattern each end `RESULT=PREFLIGHT_ERROR`.
- [ ] Editing a mask entry marks the docs whose sources it matches `STALE` and
  leaves an unrelated doc `FRESH`.
- [ ] Keep the fixtures independent of this repository's identity, as
  `conftest.py:21-24` establishes for the suite.

### Task 5: Re-bump the digests the masks change

**Files:** Modify: `docs/knowledge/data/codebase/*.md` (only those whose digest
moves)

- [ ] Run the script and re-record `source_digest` for every doc whose value
  changed because a mask now applies. This is a one-time mechanical re-bump: the
  described code has not changed, so `verified`, `stale_after`, and the prose
  stay as they are.
- [ ] Rerun until `RESULT=SUCCESS`, which `iwe-map/SKILL.md:229` requires before
  any map commit.

### Task 6: Document the mechanism where the map skill is specified

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-map/SKILL.md`;
`docs/knowledge/data/spec/iwe-workflow-skills.md`

- [ ] Extend the `source_digest` paragraph at `iwe-map/SKILL.md:203` — which
  currently explains only why the digest is not a commit SHA — to state that
  machine-managed content is masked before hashing, and name `digest-masks.json`
  as where the masks live. Add `--explain` to the script's documented interface.
- [ ] State the durable rule in `data/spec/iwe-workflow-skills.md`: the map
  skill's staleness check reflects described content, and a change confined to
  masked machine-managed values is not staleness. The JSON file is the
  mechanism; the spec carries the requirement.

### Task 7: Close the bug

**Files:** Modify: `docs/knowledge/data/bugs/pin-bumps-invalidate-map-docs.md`

- [ ] Set `stage: done` once Tasks 1-6 are complete and the reproduction no
  longer reproduces. The bug's link stays under `data/bugs.md`; the status chip
  is what changes.

## Spec changes

`data/spec/iwe-workflow-skills.md` — the map lane's staleness contract gains a
statement about masked content. The change is contract behavior a future session
must not silently reverse, so it carries a full delta.

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

#### Scenario: An unreadable mask designation stops the check

- WHEN the mask designations cannot be read or a pattern cannot be compiled
- THEN the check exits `PREFLIGHT_ERROR` naming the offending designation,
  rather than computing a fingerprint from unmasked content
```

## Depends on

[Python skill scripts](20260905-python-skill-scripts.md) — Task 2 modifies
`stale-map-docs.py`, which that plan creates. Every task here assumes the Python
port has landed and is proven digest-identical, so that a digest that moves in
Task 5 is attributable to a mask and nothing else.

## Verification

- `uv run pytest .agents/plugins/agentdev/tests/test_stale_map_docs_masks.py`
  passes.
- `uv run pytest .agents/plugins/agentdev/tests/test_stale_map_docs.py` still
  passes unchanged — masking is additive, and a repository with no
  `digest-masks.json` behaves exactly as before.
- The bug's reproduction is replayed: with the masks in place, the three commits
  named in
  [Pin bumps invalidate map docs](../bugs/pin-bumps-invalidate-map-docs.md) no
  longer mark `devcontainer`, `flow-image-build`, `github`, `github/actions`, or
  `flow-pull-request-checks` stale.
- `stale-map-docs.py --explain` names a mask and its `reason` for each doc whose
  `FRESH` verdict depends on one.
- `stale-map-docs.py` ends `RESULT=SUCCESS` on the current checkout after Task
  5.
- `uv run ruff check` and `uv run ruff format --check` pass; Prettier accepts
  `digest-masks.json`.

## Out of scope

- Masking anything outside `data/codebase/` digests. `verified`, `stale_after`,
  and the legacy `commit` fallback are untouched.
- Renovate configuration. `.github/renovate.json` keeps automerging both
  classes; this plan changes what the staleness check concludes about them, not
  what lands.
- Per-document mask overrides. One repository-level map is the whole mechanism;
  if a genuine one-off appears, it is a new decision, not a reserved extension
  point.
- Narrowing the directory-scoped `source` fields that widen the blast radius.
  Still a live option, and independent of this one.

## Key references

Verified anchor points (line numbers as of 2026-09-05):

- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh:141-162` —
  `source_digest_for_paths`, the whole-file fingerprint the masks filter; the
  dependency plan ports it to `stale-map-docs.py`
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh:192-196` —
  the digest comparison that emits `STALE`
- `.agents/plugins/agentdev/skills/iwe-map/SKILL.md:203` — the `source_digest`
  paragraph Task 6 extends
- `.agents/plugins/agentdev/skills/iwe-map/SKILL.md:229` — the
  `RESULT=SUCCESS`-before-commit rule Task 5 must satisfy
- `.agents/plugins/agentdev/tests/conftest.py:21-24` — `plugin_root`, the
  fixture keeping the suite independent of this repository
- `.github/renovate.json:9-27` — the two automerged bump classes
- `devcontainer-compose-pins.yml:14` — the `@sha256:` pin the first mask targets
- `.github/actions/setup-python-venv/action.yml:22-24` — the `setup-uv` version
  pin the second mask targets
- `docs/knowledge/data/codebase/devcontainer.md:4-6` — a directory-scoped
  `source` listing the pin file
- `.iwe/config.toml:78-79` — `[schemas.codebase]`, a path binding that a bare
  `.json` inside the lane could not satisfy
- `.iwe/config.toml:118-119` — `[schemas.okf]`, which binds every document under
  `data/` and makes an untyped file there a conformance exception
- `docs/knowledge/AGENTS.md:100-108` — the OKF bundle rule requiring every
  document under `data/` to carry a `type`
