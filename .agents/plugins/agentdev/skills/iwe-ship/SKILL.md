---
name: iwe-ship
description: Close or cancel planned work safely — normal shipping requires a zero-CRITICAL Verify report, merges verified behavior into durable specs, and records idempotent graph transitions; cancellation bypasses implementation and release transitions. Also cuts a release when asked.
disable-model-invocation: true
---

# Ship or cancel finished work

Ship always runs as the `iwe-shipper` agent, dispatched with a fresh context:
whether a plan ships must rest on what the code and the graph record, never on
what this conversation asserted. That agent is the whole rulebook; this skill
only builds its prompt and relays its report.

## Steps

1. **Build the dispatch prompt from the request alone.** It carries exactly:
   - **Plan key** — the plan the user named, as `data/plans/<YYYYMMDD>-<slug>`
     or its file path. A release cut takes none.
   - **Operation** — `ship`; `cancel` only when the user explicitly abandons
     the plan; `release <X.Y.Z>` only when the user asks for that release.
   - **Approvals** — each approval the user gave in this request, quoted
     verbatim, for example a command the Shipper reported needing.

   Add nothing else: no summary of the conversation, no claim that tests pass
   or tasks are done. If the plan or the operation is unclear, ask the user
   before dispatching.

2. **Dispatch `iwe-shipper`** with that prompt and wait for its report.
3. **Re-post its report verbatim.** When it reports `Needs decision`, name the
   approval it needs and tell the user to re-run `/agentdev:iwe-ship <plan>`
   granting it. When it returns a Ship blocker report, point at the route it
   names for each blocker: `/agentdev:iwe-implement` for a code or verification
   failure, `/agentdev:iwe-plan` revise mode for intent the plan got wrong.

## Rules

- Never perform a Ship step in this session — no spec merge, stage change, or
  release edit. Every one belongs to the dispatched agent.
- Never paraphrase an approval into the prompt; quote it, or leave it out.
