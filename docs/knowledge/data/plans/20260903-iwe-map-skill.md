---
type: plan
created: 2026-09-03
description: Add the iwe-map skill that writes and refreshes data/codebase/ — the codebase-map lane every other skill hands off to but nothing populates — and map this repository with it.
generated:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:00:00Z
sources:
- resource: https://github.com/iwe-org/dev-workspace/issues/1
  title: Missing "map" skill — verify and setup both refer to it, data/codebase/ has no writer
- resource: docs/knowledge/data/bugs/missing-map-skill.md
- resource: docs/knowledge/SCHEMA.md
- resource: .agents/plugins/agentdev/skills/iwe-setup/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/skills/skill-scripts/SKILL.md
---

# Add the iwe-map skill

## Context

[Missing map skill](../bugs/missing-map-skill.md) records the gap: Setup defers
the per-module map to "follow-up work", Verify's audit flags stale
`data/codebase/` docs "for the map skill's refresh mode", and the operating loop
assigns map refreshes to the bare session — but no skill writes the lane. The
hub `data/codebase.md` still carries its ✏️ placeholder and has no members.

The upstream template filed the same gap as
[iwe-org/dev-workspace#1](https://github.com/iwe-org/dev-workspace/issues/1),
proposing a `map` skill with an initial mode and a refresh mode. Upstream has
not shipped it, and this repository's IWE skills now live in the `agentdev`
catalog rather than arriving by template sync, so the fix lands here.

The maintainer's stated priority is an archaeology skill good enough to map a
whole repository into durable knowledge as part of setup — not a thin wrapper
around the frontmatter contract.

## Approach

Ship `/agentdev:iwe-map` as the eighth IWE workflow skill, with the two modes
the issue proposes plus the discipline that makes the map worth reading:

- **Initial mode** surveys the outside of the system before the inside (entry
  points, external surfaces, build/run/test), draws the containment tree and
  asks for confirmation before bulk-writing, then digs one component at a time —
  manifests, entry file, public surface, tests, git history for the hot files
  and the constraints comments record — and writes one doc per component at its
  canonical key, plus `flow-` docs for traces that cross component boundaries
  and `api-` docs for external surfaces. It fills `## Getting around` in the hub
  and wires `## Contains` so `iwe tree -k data/codebase` renders the code.
- **Refresh mode** consumes a bundled script that classifies every map doc as
  fresh, stale (commits touched `source` after `commit`), gone (`source` no
  longer exists), or expired (`stale_after` passed), re-reads only what moved,
  and repairs structure with `iwe rename` / `iwe delete` rather than `mv`.

The script exists because the staleness query is the one part of the workflow
that must be exact and is tedious to reconstruct: frontmatter parsing, quoted
SHAs, list-valued `source`, and the `git log <commit>..HEAD -- <source>` range
per doc. It follows the `/agentdev:skill-scripts` contract so Verify's audit and
the skill branch on the same `RESULT` names.

Rejected: writing the map from the Setup skill. Setup's job is the product doc
and a first architecture note, drafted in one conversation; a full map is a
separate, longer pass that must be re-runnable on its own when code moves, and
the issue's two-mode shape only makes sense as its own skill. Also rejected: a
per-file map. The unit is the component someone names in conversation; a doc per
file rots fastest and reads worst.

The skill is validated by running it: this repository gets mapped in initial
mode as the plan's last task, which is also the forward-test the create-skill
gate requires.

## Implementation Steps

### Task 1: Write the iwe-map skill

**Files:** Create: `.agents/plugins/agentdev/skills/iwe-map/SKILL.md`

- [ ] Write `SKILL.md` with frontmatter (`name: iwe-map`, a description that
  triggers on "map the codebase / repo", "refresh the map", and Verify's stale
  handoff, `disable-model-invocation: true`, `allowed-tools` for the bundled
  script), the initial-mode and refresh-mode steps, the canonical-key rules, the
  frontmatter template with a quoted `commit`, the script's `RESULT` table, and
  the rules (read the code never memory; what not why; unknown beats fiction;
  never `mv`).

### Task 2: Bundle the staleness script with its test

**Files:** Create:
`.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh`,
`.agents/plugins/agentdev/tests/test_stale_map_docs.py`

- [ ] Write `stale-map-docs.sh`: resolve the repo root and the IWE library path
  from `.iwe/config.toml`, walk `data/codebase/**/*.md`, parse `commit`,
  `source` (scalar or list), and `stale_after` from frontmatter, print one
  `FRESH|STALE|GONE|EXPIRED|UNKNOWN_COMMIT <key> ...` line per doc plus count
  keys, and exit `SUCCESS` (all fresh), `STALE_FOUND`, or `NO_MAP_DOCS`;
  shellcheck-clean.
- [ ] Pin every `RESULT` the skill branches on with pytest tests that build a
  throwaway repository under `plugin_tmp_path`.

### Task 3: Rewire the handoffs that named a skill that did not exist

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-setup/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-verify/SKILL.md`,
`docs/knowledge/AGENTS.md`, `docs/knowledge/STRUCTURE.md`,
`.agents/plugins/agentdev/README.md`,
`docs/knowledge/data/features/agentdev-iwe-workflow-skills.md`,
`docs/knowledge/data/bugs/missing-map-skill.md`

- [ ] Point Setup's deferred map and Verify's stale-map audit at
  `/agentdev:iwe-map`, route the operating loop's "code structure changed" step
  to the skill's refresh mode, add the skill to the workspace skills table and
  STRUCTURE's skill list, add a knowledge-graph workflow table to the plugin
  README, and update the feature and bug docs to describe the shipped state (the
  bug's `stage` stays for Ship).

### Task 4: Release the catalog version

**Files:** Modify: `.agents/plugins/agentdev/.claude-plugin/plugin.json`,
`.agents/plugins/agentdev/.codex-plugin/plugin.json`,
`.claude-plugin/marketplace.json`, `docker/desktop/agent-desktop.Dockerfile`

- [ ] Bump the four aligned pins from `3.2.0` to `3.3.0` — a new skill is a
  minor release, and the image build verifies the marketplace version against
  its `AGENTDEV_PLUGIN_VERSION` pin.

### Task 5: Map this repository in initial mode

**Files:** Create: `docs/knowledge/data/codebase/**/*.md` Modify:
`docs/knowledge/data/codebase.md`

- [ ] Run the skill's initial mode on this checkout: component docs for the
  image build, the devcontainer scaffolding, the catalog, the validator package,
  the GitHub workflows and actions, and the knowledge workspace machinery; flow
  docs for the image build, the devcontainer lifecycle, and pull-request checks;
  api docs for the image's runtime contract and the validator CLI;
  `## Getting around` filled and the ✏️ removed.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md) gains the Map contract:

``` markdown
## ADDED Requirements

### Requirement: Map derives the codebase lane from the code and refreshes it incrementally

The Map skill SHALL write `data/codebase/` only from reading the current
checkout, SHALL place each component doc at the canonical key that mirrors its
source path, SHALL stamp every doc with the `source` it describes, the quoted
`commit` it was read at, and a `verified` record, SHALL link children from
their parent's `## Contains` so the hub tree renders the code's containment,
and SHALL re-read only the docs whose `source` changed after their `commit`
when refreshing.

#### Scenario: The map is written for the first time

- **WHEN** the user asks to map the codebase and `data/codebase.md` has no
  members
- **THEN** Map surveys entry points, external surfaces, and the build, run,
  and test commands first, proposes the containment tree before writing, writes
  one doc per confirmed component plus flow and api docs, fills
  `## Getting around`, and ends with `iwe normalize` and `iwe schema validate`
  passing

#### Scenario: Code moved after the map was written

- **WHEN** Map runs in refresh mode, or Verify's audit hands it stale map docs
- **THEN** Map re-reads only the components whose `source` has commits after
  their `commit`, rewrites the affected sections, bumps `commit`, `verified`,
  and `stale_after`, and leaves fresh docs untouched

#### Scenario: A mapped component was moved or deleted

- **WHEN** a map doc's `source` no longer exists in the checkout
- **THEN** Map relocates the doc with `iwe rename` when the code moved, or
  removes it with `iwe delete` when the code is gone, and never moves or
  deletes the file by hand

#### Scenario: The code answers a question the map cannot

- **WHEN** reading a component reveals a design decision or its rationale
- **THEN** Map records what the code does in the map doc and reports the
  rationale as a candidate `data/architecture/` doc rather than writing it
  into the map
```

## Verification

- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  passes with the new skill counted.
- `uv run pytest .agents/plugins/agentdev/tests/test_stale_map_docs.py` passes.
- `shellcheck -x .agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh`
  is clean.
- `iwe normalize && iwe schema validate` pass; `iwe tree -k data/codebase -d 3`
  renders the component tree; `grep -c '✏️' docs/knowledge/data/codebase.md`
  prints `0`.
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh` ends with
  `RESULT=SUCCESS` immediately after the map commit.
- `grep -rn "map skill" .agents/plugins/agentdev/skills docs/knowledge/AGENTS.md`
  finds no dangling reference — every mention names `/agentdev:iwe-map`.

## Out of scope

- Writing `data/architecture/` docs from what the map run reveals — reported as
  candidates, written by the user or Explore.
- Mapping `.tmp/`, vendored, or generated trees.
- Mechanically detecting stale maps in CI; the script is a skill tool, not a
  workflow gate.

## Key references

Verified anchor points (line numbers as of 2026-09-03):

- `.agents/plugins/agentdev/skills/iwe-setup/SKILL.md:30-31` — the deferred
  per-module map
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:78-80` — stale-map audit
  handoff
- `docs/knowledge/AGENTS.md:55-57` — Record step for code-structure changes
- `docs/knowledge/AGENTS.md:214-222` — workspace skills table
- `docs/knowledge/STRUCTURE.md:26-27` — skill list in the layout block
- `docs/knowledge/SCHEMA.md:144-166` — codebase-map authoring contract
- `.iwe/schemas/codebase.yaml:10-20` — `source`, `commit` pattern
- `docs/knowledge/data/codebase.md:22-26` — `## Getting around` placeholder
- `.agents/plugins/agentdev/README.md:98-108` — last skills table
- `docker/desktop/agent-desktop.Dockerfile:18` — `AGENTDEV_PLUGIN_VERSION`
- `.agents/plugins/agentdev/bin/result-codes.sh:38-41` — `quit_by_code`
