---
type: architecture
description: Why Verify's rulebook lives in the iwe-verifier catalog agent, which the iwe-verify skill dispatches with a conversation-free prompt for every caller, iwe-shipper included, so every Verify run judges the code from a fresh context.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/SKILL.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/skills/iwe-verify/agent-code/verify-cache.py
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
---

# Fresh-context Verify

## Decision

Verify's rulebook is defined once, as the catalog agent `iwe-verifier` in
`.agents/plugins/agentdev/agents/`, the way the Ship and Implement rulebooks
live in `iwe-shipper` and `iwe-implementer` ([Explicit-only workflow
agents](explicit-only-workflow-agents.md)). The agent body is the rulebook on
both harnesses: the Claude Code plugin loads it, and the OpenCode bridge
registers it as a subagent.

Every Verify run starts from a fresh context, so its verdict rests on the code
and the graph, never on what a conversation asserted. `/agentdev:iwe-verify` is
a router with one route behind a saved-report cache: it builds a prompt carrying
only the plan key (or audit mode) and the approvals quoted verbatim, dispatches
`iwe-verifier` forwarding no conversation, and re-posts its report. An approval
the verifier needs comes back as `Needs decision`, and the user re-runs the
skill granting it.

Every caller takes that route — the user's session, the Implement loop, and
`iwe-shipper`. The Shipper carries the `Agent` tool and dispatches
`iwe-verifier` through the skill, quoting the approvals its own prompt carries,
so only the report enters its context ahead of the steps that change the graph.
That dispatch is nested, and relies on the nesting depth both harnesses are set
to ([Nested subagent dispatch](nested-subagent-dispatch.md)).

`iwe-verifier`'s tools are `Bash, Read, Write, Grep, Glob, Skill`. Report-only
is a rule of the rulebook, not a tool boundary.

A verification command whose effects reach beyond the working tree runs only
under a quoted approval that names it; otherwise Verify stops before it and
reports the exact command — the Shipper's rule, applied to both routes.

**A saved report is a fresh-context verdict reused.** The skill keeps one saved
report per plan, and one for audit mode, in `.tmp/verify/`, keyed by the commit
Verify ran on and a digest of every file of the active agentdev catalog. For
every caller, a lookup whose commit is `HEAD` and whose digest is the active
catalog's returns that report without running any check, unless the user asks
for `--fresh`. Verify refuses a dirty worktree, so a commit fully names what was
judged, and a verification command that dirties it is a CRITICAL. A
`Needs decision` report is never saved, so a re-run granting the approval runs
Verify. The Implement loop runs Verify through the skill, so the Shipper's
Verify on the same commit reuses the loop's verdict instead of repeating its
test runs. The lookup and save are a bundled script in the skill, the one place
every caller reaches on every harness. Trust in `.tmp/verify/` rests on a rule:
only that script writes it.

The catalog digest hashes the files of the catalog the script runs from, on disk
rather than Git-tracked, because an installed plugin is not a Git checkout, and
a session can load an installed catalog that differs from the one the commit
holds.

`/agentdev:iwe-verify` stays model-invocable: Verify mutates nothing, and the
Implement loop invokes it to get a fresh-context verdict, so an explicit-only
gate would protect nothing and block that loop.

## Rejected alternatives

- **Have `iwe-shipper` follow the `iwe-verifier` rulebook in place.** It puts
  the whole Verify run in the Shipper's context ahead of its graph changes.
- **Have `/agentdev:iwe-ship` dispatch `iwe-verifier` before the Shipper.**
  Every other route that dispatches the Shipper, such as `/agentdev:iwe-plan`
  answering a Ship blocker report, would need the same step.
- **Keep the rulebook in the skill behind a thin agent**, as the Durable
  Knowledge Auditor does with `iwe-audit`. The skill would then be both the
  rulebook and the entry point that must dispatch, so a session loading it
  already holds the rules it would run inline.
- **Make `/agentdev:iwe-verify` explicit-only.** It would gate a skill that
  mutates nothing and that the Implement loop invokes.
- **Look up the saved report in the `iwe-verifier` rulebook.** A hit would still
  cost a dispatch.
- **A handoff file the Implement side commits for the Shipper.** Committing it
  changes the commit it fingerprints, and committing project state contradicts
  report-only Verify.
- **Key the report by a tree hash or by blob hashes of the plan's files.**
  Verify and Ship run on one commit, so the commit is exact; hashes scoped to
  the plan's files miss changes outside that scope that a verification command
  can still depend on.
