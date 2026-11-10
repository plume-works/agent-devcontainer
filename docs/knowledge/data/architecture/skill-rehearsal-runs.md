---
type: architecture
description: How to rehearse a catalog skill whose session must dispatch a subagent — where that session can run, the fixture it needs, how to run and read it, and why a rehearsal never closes an observation task.
sources:
- resource: https://code.claude.com/docs/en/sub-agents
- resource: https://code.claude.com/docs/en/cli-reference
stale_after: 2027-05-04
---

# Skill rehearsal runs

A rehearsal runs a catalog skill once against a fixture, so that a skill or
agent that will not behave is caught before anyone spends a real observation
session on it. It matters most for a skill whose session dispatches a subagent —
a fresh-context reviewer, verifier, or evaluator — because a session that cannot
dispatch cannot run such a skill at all.

The Claude Code behavior this document relies on holds for Claude Code 2.1.318
in a cloud session, run headless and in-session; recheck it on a version bump.

## A rehearsal is not an observation

A rehearsal never closes an observation task. The session that prepares the
fixture knows the planted defect, the run is headless, and it covers one
harness. An observation task's `**Closed by:**` line names who closes it, and
the rehearsal is not that.

A rehearsal is an ad-hoc run. It never becomes a committed test: the repository
writes no end-to-end test that drives an agent session against a live model.

## Where the dispatching session can run

The session that loads the skill must itself be able to dispatch. On Claude Code
that means a top-level session, or a session started as an agent whose `tools:`
lists `Agent` ([Nested subagent
dispatch](../../../../openspec/specs/nested-agent-dispatch/spec.md#rationale)).

- **An in-session subagent of a Claude Code cloud session does not qualify.** It
  receives no `Agent` tool, whatever its definition's `tools:` lists; it
  receives `Skill` when its `tools:` lists it. A dispatching skill run there
  either stops, which is the skill working, or is followed by hand through some
  other mechanism, which does not exercise the skill's dispatch at all.
- **A fresh `claude` process does qualify.** Started headless with
  `--agent <runner>`, where the runner's `tools:` lists `Agent` and `Skill`, it
  dispatches the subagent the skill names.
- **Agent definitions load when the process starts.** A user or project
  `agents/` directory created during a session is not picked up by that session;
  write the runner definition first, then start the process.

## The fixture

- **A scratch branch, never merged,** cut from the branch that holds the skill
  and agent under test, so the catalog on it is the one being rehearsed. Push it
  when someone else will run the observation from it.
- **The smallest inputs that exercise the rubric:** for a review skill, a plan
  and the code it describes, with one defect planted where the skill should find
  it. Run the fixture's own checks once to confirm the defect is real.
- **The checkout the session runs in holds the fixture.** A dispatched agent
  runs in its parent session's working directory, and a session's catalog comes
  from its plugin source, not from the directory it works in. A rehearsal from
  another checkout therefore starts its process there, with `--plugin-dir`
  pointing at that checkout's catalog.
- **A recorded baseline:** `git rev-parse HEAD` and an empty
  `git status --porcelain`, so a report-only skill can be checked against them.

## Running it

Keep the runner definition outside the repository, in `~/.claude/agents/`, so
the worktree stays clean for the baseline check, and delete it afterwards. Its
body tells the process to treat its prompt as the user's first message and to
follow the skill that message invokes.

``` bash
claude -p --verbose --output-format stream-json \
  --plugin-dir <catalog plugin directory in the fixture checkout> \
  --agent <runner> \
  --allowedTools '<Agent,Skill, and every tool the skill and its subagent need>' \
  < <file holding the slash command> > <stream file>
```

- **The prompt goes on stdin.** `--allowedTools` takes a variable number of
  values and consumes a prompt given after it as an argument.
- **List every tool the run needs in `--allowedTools`.** A workspace never
  opened interactively is untrusted, and Claude Code then ignores the project's
  `permissions.allow` entries; a headless run cannot answer a permission prompt.
  Scope `Bash` to the commands the subagent should run.

## Reading the result

The `stream-json` output is the evidence:

- the `system` `init` event lists the tools, agents, and skills the session
  received — check the runner has `Agent` and the subagent under test is listed;
- each tool call's `parent_tool_use_id` separates the dispatching session's
  calls (none) from the subagent's (the dispatch call's id);
- the dispatch call's input holds the subagent type and the exact prompt it
  received, for a check that nothing beyond the skill's inputs was forwarded;
- the `result` event holds the final message, for a check that the report was
  re-posted.

Then compare `HEAD` and `git status --porcelain` with the baseline.

## Rejected alternatives

- **An in-session `general-purpose` or catch-all subagent as the dispatching
  session.** It has no `Agent` tool, so the skill cannot dispatch.
- **An existing catalog agent whose `tools:` lists `Agent`, as a stand-in.** In
  a cloud session it still receives no `Agent`, and it carries its own
  instructions into the run.
- **Running the skill in the session that built the fixture.** It exercises the
  dispatch, but the dispatching session knows the defect; acceptable for a quick
  smoke check only.
