---
type: architecture
description: Why Verify's rulebook lives in the iwe-verifier catalog agent, which the iwe-verify skill dispatches with a conversation-free prompt and iwe-shipper follows in place, so every Verify run judges the code from a fresh context.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-30T14:00:00Z
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
all three harnesses: the Claude Code plugin loads it, the Codex installer
renders it into `agentdev-iwe-verifier.toml`, and the OpenCode bridge registers
it as a subagent.

Every Verify run starts from a fresh context, so its verdict rests on the code
and the graph, never on what a conversation asserted. `/agentdev:iwe-verify` is
a router with two routes, both behind one saved-report cache:

- **From a session** — the skill builds a prompt carrying only the plan key (or
  audit mode) and the user's approvals quoted verbatim, dispatches
  `iwe-verifier` forwarding no conversation, and re-posts its report. An
  approval the verifier needs comes back as `Needs decision`, and the user
  re-runs the skill granting it.
- **From inside `iwe-shipper`** — the Shipper is already a fresh context and
  stays a leaf, so the skill tells it to read the `iwe-verifier` rulebook and
  follow it in place. The Shipper reaches the rulebook through the skill because
  a skill can link the agent file plugin-relatively on every harness, while an
  agent body rendered into a Codex TOML cannot.

`iwe-verifier`'s tools are `Bash, Read, Write, Grep, Glob, Skill`. `Write` makes
the Codex installer give it a `workspace-write` sandbox, which a
`## Verification` command that writes caches or a virtual environment needs.
Report-only is a rule of the rulebook, not a tool boundary.

A verification command whose effects reach beyond the working tree runs only
under a quoted approval that names it; otherwise Verify stops before it and
reports the exact command — the Shipper's rule, applied to both routes.

**A saved report is a fresh-context verdict reused.** The skill keeps one saved
report per plan, and one for audit mode, in `.tmp/verify/`, keyed by the commit
Verify ran on and a digest of every file of the active agentdev catalog. On
either route, a lookup whose commit is `HEAD` and whose digest is the active
catalog's returns that report without running any check, unless the user asks
for `--fresh`. Verify refuses a dirty worktree, so a commit fully names what was
judged, and a verification command that dirties it is a CRITICAL. A
`Needs decision` report is never saved, so a re-run granting the approval runs
Verify. The Implement loop runs Verify through the skill, so the Shipper's
in-place Verify on the same commit reuses the loop's verdict instead of
repeating its test and e2e runs. The lookup and save are a bundled script in the
skill, the one place both routes reach on every harness. Trust in `.tmp/verify/`
rests on a rule: only that script writes it.

The catalog digest hashes files on disk rather than Git-tracked ones, because an
installed plugin is not a Git checkout; inside this repository the commit
already covers the catalog, and the digest adds nothing there.

`/agentdev:iwe-verify` stays model-invocable: Verify mutates nothing, and the
Implement loop invokes it to get a fresh-context verdict, so an explicit-only
gate would protect nothing and block that loop.

## Rejected alternatives

- **Give `iwe-shipper` the Agent tool and nest the dispatch.** OpenCode refuses
  a nested dispatch at its default depth, and raising it takes an experimental
  key ([Nested subagent dispatch](nested-subagent-dispatch.md)).
- **Keep the rulebook in the skill behind a thin agent**, as the Durable
  Knowledge Auditor does with `iwe-audit`. The skill would then be both the
  rulebook and the entry point that must dispatch, so a session loading it
  already holds the rules it would run inline.
- **A Codex sandbox override key read by the installer.** The maintainer chose
  `Write` in the tools list over a new installer contract.
- **Make `/agentdev:iwe-verify` explicit-only.** It would gate a skill that
  mutates nothing and that the Implement loop invokes.
- **Look up the saved report in the `iwe-verifier` rulebook.** An agent body
  rendered into a Codex TOML cannot reach a skill's bundled script, and a hit
  would still cost a dispatch.
- **A handoff file the Implement side commits for the Shipper.** Committing it
  changes the commit it fingerprints, and committing project state contradicts
  report-only Verify.
- **Key the report by a tree hash or by blob hashes of the plan's files.**
  Verify and Ship run on one commit, so the commit is exact; hashes scoped to
  the plan's files miss changes outside that scope that a verification command
  can still depend on.
