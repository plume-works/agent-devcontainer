---
type: bug
description: source_digest hashes whole files, so an automerged Renovate version-pin bump marks map docs stale even though no described behavior changed.
generated:
  by: claude-code/opus-5
  at: 2026-09-05T00:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh
- resource: .github/renovate.json
- resource: docs/knowledge/data/codebase/devcontainer.md
---

# Pin bumps invalidate map docs

## Symptom

`stale-map-docs.sh` reports `STALE` for `data/codebase/` docs whose prose is
still entirely accurate, because a dependency pin changed somewhere under their
`source`. The docs do not mention the pinned value; nothing they claim is wrong.

Renovate automerges both classes of bump that trigger this, so the map lane goes
amber with no human in the loop. A staleness signal that fires without a real
change is one the next session learns to skip — and skipping it is how a genuine
structural drift gets missed.

## Reproduction

Three automerged pin bumps landed after the map was written at `e50ebdb`, and
between them marked five of twenty-six docs stale:

| Commit    | Changed file                                   | Change                               | Docs marked stale                                      |
| --------- | ---------------------------------------------- | ------------------------------------ | ------------------------------------------------------ |
| `660ce06` | `devcontainer-compose-pins.yml`                | image digest `12842ec…` → `2b56604…` | `devcontainer`, `flow-image-build`                     |
| `4cc8615` | `.github/actions/setup-python-venv/action.yml` | uv `0.12.9` → `0.12.10`              | `github`, `github/actions`, `flow-pull-request-checks` |
| `dad544c` | `devcontainer-compose-pins.yml`                | image digest `2b56604…` → `08300b1…` | `devcontainer`, `flow-image-build`                     |

Each is a one-line edit. Grepping all five docs for the digests and both uv
version strings returns nothing — no doc quotes a value that changed:

``` console
$ .agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh | tail -3
STALE_COUNT=5
GONE_COUNT=0
RESULT=STALE_FOUND
```

Two of the three commits bump the same digest line twice, so a refresh run
between them would have been invalidated again immediately.

## Root cause

`source_digest_for_paths` fingerprints whole tracked files: it runs
`git hash-object` per file under `source` and hashes the pairs. Any byte change
registers, whether or not the doc says anything about that byte.

The digest was deliberately chosen over a commit SHA so that squash merges and
branch rewrites do not cause false staleness. That reasoning holds; it just does
not extend to content churn *inside* the described tree, which is the case a pin
bump hits.

Directory-scoped `source` fields set the blast radius. `github` claims all of
`.github`, `flow-pull-request-checks` claims `.github` plus
`.pre-commit-config.yaml`, and both `devcontainer` and `flow-image-build` list
`devcontainer-compose-pins.yml` — so one touched file invalidates every doc
claiming that subtree.

## Fix

Mask machine-managed content out of the digest input before hashing, driven by a
repository-level map of glob to pattern at `docs/knowledge/digest-masks.json`.
Each pattern carries a replacement rather than deleting its match, so the
structure around a pinned value stays tracked while the value itself stops
mattering: a changed image name or a dropped pin line still marks the doc stale.

The map is keyed by glob so one entry covers a fan-out — `.github/**/*.yml`
serves `github`, `github/actions`, and `flow-pull-request-checks` together. It
sits beside `data/` rather than inside it, because `data/` is an OKF bundle of
typed Markdown documents, and it is JSON so a consuming repository needs no
third-party parser.

Planned in [Digest masks for map docs](../plans/20260905-digest-masks.md), which
depends on [Python skill scripts](../plans/20260905-python-skill-scripts.md) —
the glob, JSON, and regex work needs the ported script.

Three alternatives were considered and rejected. Per-doc `digest_ignore`
frontmatter puts a property of a file into every doc that claims it — five
copies of two facts here — and directory-scoped `source` fields mean a per-doc
entry needs a path scope anyway, which is the same map sharded. Skipping
Renovate-authored commits hides a real signal, since a major-version bump
genuinely can invalidate a doc. Narrowing `source` fields helps the `.github`
fan-out but not `devcontainer-compose-pins.yml`, which is legitimately described
content that happens to hold a digest.

## Key references

Verified anchor points (line numbers as of 2026-09-05):

- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh:141-162` —
  `source_digest_for_paths`, the whole-file `git hash-object` fingerprint
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh:192-196` —
  the digest comparison that emits `STALE`
- `.agents/plugins/agentdev/skills/iwe-map/SKILL.md:203` — why the digest is not
  a commit SHA
- `.github/renovate.json:9-27` — the two automerged bump classes
- `docs/knowledge/data/codebase/devcontainer.md:4-6` — a directory-scoped
  `source` listing the pin file
