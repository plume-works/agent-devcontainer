---
type: bug
description: setup and verify both hand codebase-map work to a "map skill" that does not exist, so data/codebase/ is never populated and its staleness audit can never be acted on.
generated:
  by: claude-code/opus-5
  at: 2026-08-15T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-setup/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: https://github.com/iwe-org/dev-workspace/issues/1
---

# Missing map skill

## Symptom

Two shipped skills delegate codebase-map work to a skill that is not present in
`.agents/plugins/agentdev/skills/`, so both delegations are silent no-ops.

`setup` defers the per-module map as "follow-up work" without naming an owner.
`verify` audit mode detects stale `data/codebase/` docs and flags them "for the
map skill's refresh mode" — a handoff to nothing. Because `verify` is barred
from fixing anything ("Report, never fix"), a stale map has no path back to
accurate: the only skill that can see the problem is forbidden to repair it, and
the skill it names does not exist.

The visible result in this workspace: `data/codebase.md` is a hub with no
members. `data/index.md:32` advertises it, and `iwe tree -k data/codebase`
renders nothing.

## Reproduction

Setup ran to completion here — `data/product.md` contains zero `✏️`
placeholders, and both onboarding tasks are `stage: done`
(`backlog/fill-product-doc.md`, `backlog/capture-current-architecture.md`).

Yet:

``` console
$ ls docs/knowledge/data/codebase/
ls: cannot access 'data/codebase/': No such file or directory

$ iwe find --included-by data/codebase -f keys
(no output)

$ grep -n '✏️' docs/knowledge/data/codebase.md
27:✏️
```

`data/codebase.md` still holds its `## Getting around` placeholder and its
`## Components`, `## Flows`, and `## Interfaces` sections are empty — the
post-setup state, unchanged, with no skill able to advance it.

## Root cause

The skill set has seven members — `explore`, `implement`, `plan`, `setup`,
`ship`, `verify`, `weekly` — and none writes `data/codebase/`. Every other
`data/` lane has a writer: `plan` files plans, `ship` writes specs, implemented
features, releases, and the log, and `explore` captures someday, architecture,
and concept docs.

`data/codebase/` is also the lane least recoverable by hand. `SCHEMA.md` gives
it the heaviest authoring contract: canonical keys mirroring source paths with
wrapper segments elided, a `## Contains` tree that `iwe tree` depends on, and
required `source` + `commit` + `verified` frontmatter where `commit` must be
required `source` + `source_digest` + `verified` frontmatter. `source_digest`
fingerprints tracked source contents so codebase docs rot when the code they
describe moves — so the refresh path `verify` cannot reach is the one the design
expects to run most often.

## Fix

Upstream:
[iwe-org/dev-workspace#1](https://github.com/iwe-org/dev-workspace/issues/1),
filed 2026-08-15 against
[`249943b`](https://github.com/iwe-org/dev-workspace/commit/249943bcc30ac1016469d5ee89a16ce454cc882f),
proposing a `map` skill with two modes — **initial** (walk the containment tree,
one doc per component at its canonical key, wire `## Contains`, stamp
provenance, fill the `## Getting around` placeholder) and **refresh** (consume
`verify`'s stale list, re-read changed sources, bump `source_digest` and
`verified`).

The IWE skills ship from this repository's `agentdev` catalog rather than by
template sync, so the fix is local:
[Add the iwe-map skill](../plans/20260903-iwe-map-skill.md) adds
`/agentdev:iwe-map` with the two modes the issue proposes, a bundled
`stale-map-docs.sh` that classifies every map doc as fresh, stale, gone, or
expired, and repoints Setup, Verify, and the operating loop at it.

## Key references

Verified anchor points (line numbers as of 2026-09-03):

- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:81-85` — stale-map audit,
  handing off to `/agentdev:iwe-map`
- `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md:96` — "Report, never
  fix", which is why the handoff needs a real owner
- `.agents/plugins/agentdev/skills/iwe-setup/SKILL.md:30-32` — per-module map
  deferred to the map skill's initial mode
- `docs/knowledge/AGENTS.md:57-61` — Record step routes refreshes to the skill
- `docs/knowledge/SCHEMA.md:144-166` — the codebase-map authoring contract
- `docs/knowledge/data/codebase.md:22` — `## Getting around`, filled
- `docs/knowledge/data/index.md:32` — the hub advertised to readers
