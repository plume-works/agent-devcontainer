---
type: feature
stage: implemented
description: The self-improve experiential-learning plugin ships from this repository's Claude marketplace as a second catalog plugin, published but not enabled by default.
generated:
  by: claude-code/opus-5
  at: 2026-09-09T00:00:00Z
sources:
- resource: .claude-plugin/marketplace.json
- resource: .agents/plugins/self-improve
- resource: .devcontainer/scripts/reinstall-agentdev-claude.sh
- resource: .devcontainer/scripts/reinstall-agentdev-codex.sh
- resource: Makefile
---

# Self-improve plugin in the catalog

## Purpose

`self-improve` is a hook-driven experiential-learning engine for Claude Code: it
captures turns, decides when a lesson is worth reviewing, runs an isolated
reviewer, and proposes edits to `CLAUDE.md`, rules, and skills under user
authorization. It previously lived in its own repository and consumed this one's
catalog, so the two moved on separate clocks while sharing one toolchain. The
consolidation decision and its rejected alternatives are recorded in
[Self-improve consolidation](../architecture/self-improve-consolidation.md).

## Behaviour

**The catalog publishes two plugins on Claude, one on Codex.**
`.claude-plugin/marketplace.json` publishes `agentdev` and `self-improve`;
`.agents/plugins/marketplace.json` publishes `agentdev` alone, because
`self-improve` ships no Codex manifest. The validator accepts the asymmetry — it
skips an ecosystem a plugin does not ship for.

**The Claude reinstall script iterates every published plugin.**
`reinstall-agentdev-claude.sh` uninstalls each published plugin across the
`user`, `project`, and `local` scopes, then reinstalls each at the requested
scope, so adding a third plugin needs no further change. The Codex script keeps
its single-plugin read, which is accurate for the manifest it drives.

**Published is not enabled.** Nothing this repository ships enables the plugin:
the tracked `.claude/settings.json` names it nowhere, and the Ansible catalog
role selects its plugin by name and asserts exactly one match, so a second
published entry is invisible to it. Local enablement written by
`claude plugin install` lives in gitignored `.claude/settings.local.json` —
working state, not a published default.

**Live tests are guarded at collection.** Tests marked `smoke` or `pty` drive a
real Claude session and spend model usage. A `pytest_collection_modifyitems`
hook skips them unless `SELF_IMPROVE_RUN_LIVE` is set, so the guard holds at
every entry point a marker filter misses — selection by path, by `-m`, and by
node id. The `harness` marker is deliberately unguarded: it self-checks the pty
harness against a fake terminal and costs nothing.

**The plugin runs on the repository's interpreter floor** of Python 3.12, while
its standard-library-only runtime rule is preserved intact and enforced by an
AST walk over every runtime module. The two properties are independent, and only
the second is load-bearing.

**One Makefile at the repository root** carries the live-session targets
(`smoke`, `smoke-auto`, `wake`, `wake-memory`, `wake-repeat`), `test-harness`,
`validate`, and `check`. Formatting and linting targets are absent by design —
those belong to pre-commit, per
[Let pre-commit own formatting](pre-commit-owns-formatting.md).

## Scope

The plugin's behavior is unchanged by the move; it ships exactly as it arrived,
and its durable behavior is specified in
[Self-improve learning loop](../spec/self-improve-learning-loop.md). Enabling
the plugin, staging it into `agent-desktop`, and Codex support for it are each
separate decisions. Two measured defects ship with it, recorded rather than
fixed:
[Reviewer decline asymmetry](../bugs/self-improve-reviewer-decline-asymmetry.md)
and
[Unstageable routing option in the improve skill](../bugs/self-improve-unstageable-routing-option.md).

## References

- Plan:
  [Consolidate the self-improve plugin into this repository](../plans/20260909-consolidate-self-improve-plugin.md)
- Decision:
  [Self-improve consolidation](../architecture/self-improve-consolidation.md)
- Runtime design:
  [Self-improve runtime](../architecture/self-improve-runtime.md)
- Spec: [Self-improve learning loop](../spec/self-improve-learning-loop.md)
