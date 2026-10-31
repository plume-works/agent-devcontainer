---
type: feature
stage: deprecated
status: deprecated
description: An iwe-map refresh that finds a map doc stale only because a version, digest, or pin value moved masks that kind of value, proves the mask against history, and re-stamps the digests it explains in one commit before refreshing any prose.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T16:40:07Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-map/SKILL.md
- resource: .agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py
- resource: docs/knowledge/data/architecture/agent-metadata-files.md
- resource: docs/knowledge/data/bugs/pin-bumps-invalidate-map-docs.md
---

# Map masks version-only changes

## Purpose

A refresh spends its effort only on docs whose described content moved. When a
map doc is stale because a pinned value changed and nothing around it did, the
refresh fixes the cause — a missing digest mask — instead of hand-refreshing the
doc, so the next bump of the same kind leaves the map fresh.

## Behaviour

**Sort the change before refreshing.** For each `STALE` doc, refresh mode reads
what changed under its `source` since its `verified.at`. A change is
version-only when every changed span is a version, digest, or pin value and the
text around it — the artifact's name, the set of pinned entries, the presence of
the pin — is unchanged. Who authored the change does not matter.

**Mask the kind, not the value.** For a version-only change, the skill adds or
widens a `digest_ignore` rule in the `.agent.metadata.json` nearest to the
changed files whose directory covers every file holding that kind of value, with
a `reason` naming what moves it.

**Prove the mask against history.** `stale-map-docs.py --replay` applies the
working-tree masks to every historical change of the files they reach and
reports which changes they absorb, which still move the digest, and every value
each mask hid. A mask is kept only when every absorbed change is version-only
and every hidden value is version-shaped.

**Re-stamp what the mask alone explains.** Replay names each doc the new mask
reaches as `RESTAMP` with its new digest, or `REFRESH` when the mask does not
explain all of the doc's change. A re-stamp changes only `source_digest`.

**One commit, first.** The metadata change and the re-stamps land as one commit,
before any prose refresh; the staleness check is rerun and only what is still
stale is refreshed.

**Name the hidden majors.** The run's report names each masked kind whose mask
also hides major-version changes, such as an Ubuntu base moving from 24.04 to
26.04.

This applies to agent-run refreshes, including the refresh before an agent push.
A dependency-update pull request is not repaired in CI.

## Edge cases

- **A change mixes a version bump with a real edit.** The mask commit lands
  first; the doc is then refreshed for the remaining change.
- **The doc quotes the value that moved.** The change is not version-only for
  that doc; it is refreshed, not masked.
- **A doc the new mask reaches was already stale for another reason.** Replay
  reports it `REFRESH`; its digest is not re-stamped.
- **The doc's own commit lands after its `verified.at`.** Its changes are not
  absorbed, so the doc is reported `REFRESH` — the safe direction.
- **Uncommitted source edits.** A working-tree change the masks do not absorb
  makes the doc `REFRESH`.

## Open questions

None — scope and the qualifying changes are settled.
