---
name: iwe-verify
description: Verify that implementation matches the graph — check a plan's tasks, spec requirements, and scenarios against the actual code before shipping, or sweep the whole workspace for doc↔code drift.
---

# Verify implementation against the graph

The Verify rulebook is the `iwe-verifier` catalog agent, and every Verify run
starts from a fresh context: whether the code matches the graph must rest on
what the code and the graph record, never on what a conversation asserted. This
skill only routes the run there. Pick the route by where you are.

## From inside `iwe-shipper`

You are already a fresh context, and you stay a leaf. Read [the iwe-verifier
rulebook](../../agents/iwe-verifier.agent.md) in full and follow it in place,
in its **In place inside `iwe-shipper`** mode, for the plan you are shipping and
with the approvals your own prompt quotes. Do not dispatch any agent. Return its
report to your Verify step.

## From a session

1. **Build the dispatch prompt from the request alone.** It carries exactly:
   - **Plan key** — the plan the user named, as `data/plans/<YYYYMMDD>-<slug>`
     or its file path — or **audit mode** when the user asked for a
     workspace-wide drift check with no plan.
   - **Approvals** — each approval the user gave in this request, quoted
     verbatim, for example a command the verifier reported needing.

   Add nothing else: no summary of the conversation, no claim that tests pass
   or tasks are done. If neither a plan nor audit mode is clear from the
   request, ask the user before dispatching.

2. **Dispatch `iwe-verifier`** with that prompt, forwarding no conversation
   turns, and wait for its report.
3. **Re-post its report verbatim.** When it reports `Needs decision`, name the
   approval or choice it needs and tell the user to re-run
   `/agentdev:iwe-verify <plan>` granting it.

## Rules

- Never perform a Verify step in this session from the session route — no
  check, no verification command. Every one belongs to the dispatched agent.
- Never paraphrase an approval into the prompt; quote it, or leave it out.
- Report-only: neither route fixes code, ticks a box, or mutates the graph.
