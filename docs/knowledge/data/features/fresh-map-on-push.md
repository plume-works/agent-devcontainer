---
type: feature
stage: implemented
description: Every agent push runs the codebase-map staleness check first and refreshes a stale map before the branch leaves the machine, and the AI review leaves map staleness to CI.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-02T12:00:00Z
sources:
- resource: .agents/plugins/agentdev/skills/pr-open/agent-code/push-branch.sh
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/skills/update-branch/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-merge/SKILL.md
- resource: .agents/plugins/agentdev/skills/pr-review/SKILL.md
---

# Fresh codebase map on push

## Purpose

A pull request that moves code under a `data/codebase/` doc reaches CI with a
fresh map, instead of failing the
`Check codebase map docs against their sources` step and needing a second push
after a refresh. The AI review does not restate a staleness verdict that CI
already asserts.

## Behaviour

**`push-branch.sh` gates every push on map freshness.** Before pushing, and
before reporting `ACTION=none` for a head the upstream already holds, it runs
`stale-map-docs.py` in a temporary detached worktree at the branch head and
prints `MAP_CHECK=<fresh|skipped|stale|failed|overridden>`. A stale map ends
with `MAP_STALE` (`6`) and pushes nothing; a check that reaches no verdict ends
with `MAP_CHECK_FAILED` (`7`).

**The skills refresh and retry.** On `MAP_STALE`, `pr-open` runs the
`/agentdev:iwe-map` refresh, commits it through `/agentdev:git-commit`, and
reruns the push. `update-branch`, `pr-feedback-resolution`, and `pr-merge` push
through the same helper and handle its result the same way.

**The override is explicit.** `--skip-map-check` pushes without the check and
reports `MAP_CHECK=overridden`; skills pass it only when the user asks to push a
stale map, and CI still fails it.

**The AI review leaves staleness to CI.** `pr-review` raises no map-staleness
finding when the repository's CI runs the staleness check.

The contract is [IWE workflow skills](../spec/iwe-workflow-skills.md).

## Edge cases

- **The repository has no map.** No `.iwe/config.toml` in the pushed commit, a
  missing check script, or `NO_MAP_DOCS` reports `MAP_CHECK=skipped` and pushes
  as before.
- **The working tree holds uncommitted changes.** The check reads only the
  pushed commit, so uncommitted edits do not change the verdict.
- **A head reached the remote through a bare `git push`.** `ACTION=none` still
  runs the check, so `pr-open` refreshes before opening or updating the pull
  request.
- **`pr-merge` repairs in a private worktree branch.** That branch tracks
  `origin/<head-branch>`, so the helper pushes to the pull request head.
- **A consumer's CI omits the staleness check.** The review keeps reporting map
  staleness there.

## Open questions

None — every design question this feature raised is settled.

## References

- Plan: [Refresh the codebase map before pushing and keep its staleness out of
  AI reviews](../plans/20260929-map-refresh-before-push.md)
