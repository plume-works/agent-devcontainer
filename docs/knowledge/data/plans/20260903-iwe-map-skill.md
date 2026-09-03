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

The bar the maintainer set for the skill: an archaeology pass that maps a whole
repository into durable knowledge as part of setup, not a thin wrapper around
the frontmatter contract.

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

- [x] Write `SKILL.md` with frontmatter (`name: iwe-map`, a description that
  triggers on "map the codebase / repo", "refresh the map", and Verify's stale
  handoff, `disable-model-invocation: true`, `allowed-tools` for the bundled
  script), the initial-mode and refresh-mode steps, the canonical-key rules, the
  frontmatter template with a quoted `commit`, the script's `RESULT` table, and
  the rules (read the code never memory; what not why; unknown beats fiction;
  never `mv`).
  - **Evidence:** commit `eb60f60`;
    `uv run validate_agent_files --recommend . --require-marketplace claude codex`
    reports 47/47 skills valid, 0 errors, 0 warnings with `iwe-map` counted.

### Task 2: Bundle the staleness script with its test

**Files:** Create:
`.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh`,
`.agents/plugins/agentdev/tests/test_stale_map_docs.py`

- [x] Write `stale-map-docs.sh`: resolve the repo root and the IWE library path
  from `.iwe/config.toml`, walk `data/codebase/**/*.md`, parse `commit`,
  `source` (scalar or list), and `stale_after` from frontmatter, print one
  `FRESH|STALE|GONE|EXPIRED|UNKNOWN_COMMIT <key> ...` line per doc plus count
  keys, and exit `SUCCESS` (all fresh), `STALE_FOUND`, or `NO_MAP_DOCS`;
  shellcheck-clean.
  - **Evidence:** commit `eb60f60`; `shellcheck -x` on the script is clean; run
    against this workspace after the map commit it prints 26 `FRESH` lines and
    `RESULT=SUCCESS`.
- [x] Pin every `RESULT` the skill branches on with pytest tests that build a
  throwaway repository under `plugin_tmp_path`.
  - **Evidence:** commit `eb60f60`;
    `uv run pytest .agents/plugins/agentdev/tests/test_stale_map_docs.py` — 7
    passed, covering `SUCCESS`, `STALE_FOUND` (stale, gone, unknown commit,
    expired), `NO_MAP_DOCS`, `PREFLIGHT_ERROR`, and `--help`.

### Task 3: Rewire the codebase-map handoffs to `/agentdev:iwe-map`

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-setup/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-verify/SKILL.md`,
`docs/knowledge/AGENTS.md`, `docs/knowledge/STRUCTURE.md`,
`.agents/plugins/agentdev/README.md`,
`docs/knowledge/data/features/agentdev-iwe-workflow-skills.md`,
`docs/knowledge/data/bugs/missing-map-skill.md`

- [x] Point Setup's deferred map and Verify's stale-map audit at
  `/agentdev:iwe-map`, route the operating loop's "code structure changed" step
  to the skill's refresh mode, add the skill to the workspace skills table and
  STRUCTURE's skill list, add a knowledge-graph workflow table to the plugin
  README, and update the feature and bug docs to describe the shipped state (the
  bug's `stage` stays for Ship).
  - **Evidence:** commit `eb60f60`; `grep -rn "map skill"` over the skills and
    `docs/knowledge/AGENTS.md` finds only mentions that name
    `/agentdev:iwe-map`.

### Task 4: Release the catalog version

**Files:** Modify: `.agents/plugins/agentdev/.claude-plugin/plugin.json`,
`.agents/plugins/agentdev/.codex-plugin/plugin.json`,
`.claude-plugin/marketplace.json`, `docker/desktop/agent-desktop.Dockerfile`

- [x] Bump the four aligned pins from `3.2.0` to `3.3.0` — a new skill is a
  minor release, and the image build verifies the marketplace version against
  its `AGENTDEV_PLUGIN_VERSION` pin.
  - **Evidence:** commit `eb60f60`; both plugin manifests, the marketplace
    entry, and the Dockerfile `ARG` read `3.3.0`, and the validator's
    marketplace check passes on the aligned versions.

### Task 5: Map this repository in initial mode

**Files:** Create: `docs/knowledge/data/codebase/**/*.md` Modify:
`docs/knowledge/data/codebase.md`

- [x] Run the skill's initial mode on this checkout: component docs for the
  image build, the devcontainer scaffolding, the catalog, the validator package,
  the GitHub workflows and actions, and the knowledge workspace machinery; flow
  docs for the image build, the devcontainer lifecycle, and pull-request checks;
  api docs for the image's runtime contract and the validator CLI;
  `## Getting around` filled and the ✏️ removed.
  - **Evidence:** commit `d132a6c` — 26 docs (19 components, 3 flows, 2
    interfaces) pinned to `eb60f60`; `iwe schema validate` clean;
    `iwe tree -k data/codebase -d 3` renders the containment tree;
    `grep -c '✏️' docs/knowledge/data/codebase.md` prints `0`;
    `stale-map-docs.sh` ends `RESULT=SUCCESS`.

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

## Verification results

Every `## Verification` check passed on the tree at `d132a6c`: the validator
reports 47/47 skills valid with no warnings, the seven script tests pass,
shellcheck is clean, `iwe normalize` and `iwe schema validate` are clean, the
hub has no placeholder, the tree renders 26 docs under the hub, the staleness
script reports every doc fresh, and no handoff still says "map skill" without
naming `/agentdev:iwe-map`. The plan-scope audit by the Durable Knowledge
Auditor returned two rewrites, both applied, and no drops.

Two judgment calls from the mapping run, recorded here because they shape what
the map covers: the catalog's consumer-facing surface is described in the
catalog component doc's `## Public surface` rather than a separate `api-` doc,
since the two would duplicate each other; and the thirteen one-task Ansible
roles are rows in the `ansible` doc's `## Contains` rather than docs, per the
skill's depth budget.

## Out of scope

- Writing `data/architecture/` docs from what the map run reveals — reported as
  candidates, written by the user or Explore.
- Mapping `.tmp/`, vendored, or generated trees.
- Mechanically detecting stale maps in CI; the script is a skill tool, not a
  workflow gate.

## Key references

Verified anchor points (line numbers as of 2026-09-03, tree `d132a6c`):

- `.agents/plugins/agentdev/skills/iwe-map/SKILL.md:22` — `## Steps`; `:122`
  refresh mode; `:158` canonical keys; `:180` frontmatter; `:204` rules
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh:14` —
  declared results; `:146` the per-doc loop; `:206` `STALE_FOUND` exit
- `.agents/plugins/agentdev/tests/test_stale_map_docs.py:76-206` — the seven
  contract tests
- `.agents/plugins/agentdev/skills/iwe-setup/SKILL.md:30-32` — the deferred
  per-module map, now naming the skill
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:81-85` — stale-map audit
  handoff
- `docs/knowledge/AGENTS.md:57-61` — Record step for code-structure changes
- `docs/knowledge/AGENTS.md:217` — the skill's row in the workspace table
- `docs/knowledge/STRUCTURE.md:26-27` — skill list in the layout block
- `.agents/plugins/agentdev/README.md:109-127` — knowledge-graph workflow table
- `docs/knowledge/SCHEMA.md:144-166` — codebase-map authoring contract
- `.iwe/schemas/codebase.yaml:13-21` — `source`, `commit` pattern
- `docs/knowledge/data/codebase.md:22,66` — `## Getting around`, `## Components`
- `docker/desktop/agent-desktop.Dockerfile:18` — `AGENTDEV_PLUGIN_VERSION`
- `.agents/plugins/agentdev/bin/result-codes.sh:43` — `quit_by_code`
