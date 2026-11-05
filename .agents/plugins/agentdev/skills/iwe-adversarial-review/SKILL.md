---
name: iwe-adversarial-review
description: Look for ways to defeat an IWE plan's design or its implemented code, from a fresh context — report-only. Use only when the user explicitly asks for an adversarial review of a named plan, or when a plan task being implemented runs `/agentdev:iwe-adversarial-review <plan> <plan|code>`; never while planning, and never on a pull-request review or a Verify request.
---

# Review a plan adversarially

The adversarial rubric is the `iwe-adversarial-reviewer` catalog agent, and
every review starts from a fresh context: whether a design or its code can be
defeated must rest on what the plan and the code record, never on what a
conversation asserted. This skill routes the request there and returns its
report. It is a separate question from `/agentdev:iwe-verify`, which checks
conformance to the plan.

## Steps

1. **Resolve the request.** It names a plan — `data/plans/<YYYYMMDD>-<slug>`,
   its file path, or its slug — and a target: `plan` to review the design, or
   `code` to review the implementation. If either is missing or ambiguous, ask
   the user first; inside the Implement loop, take both from the plan task that
   runs this skill.
2. **Build the dispatch prompt from the request alone.** It carries exactly:
   - **Plan key** — the plan the request names.
   - **Target** — `plan` or `code`.
   - **Approvals** — each approval the user gave in this request, quoted
     verbatim, for example a command the reviewer reported needing.

   Add nothing else: no summary of the conversation, no claim that the design
   is sound, that tests pass, or that a task is done.

3. **Dispatch `iwe-adversarial-reviewer`** with that prompt, forwarding no
   conversation turns, and wait for its report.
4. **Re-post its report verbatim** in your final message text: the subagent's
   result is tool output the user may never see. When it reports
   `Needs decision`, name the approval it needs and tell the user to re-run
   `/agentdev:iwe-adversarial-review <plan> <target>` granting it.

## Rules

- Perform no review step in this session — every check belongs to the
  dispatched agent.
- Never paraphrase an approval into the prompt; quote it, or leave it out.
- Report-only: this skill fixes no code, ticks no box, files nothing, and
  mutates no graph document. Acting on the findings belongs to the caller —
  in the Implement loop, the rules of the `iwe-implementer` rulebook.
