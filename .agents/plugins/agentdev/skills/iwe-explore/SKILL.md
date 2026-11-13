---
name: iwe-explore
description: Investigate problems, compare approaches, and clarify ideas with the user before planning. Read code and the graph. Do not write code. Use when the user says "let's think about ...", "explore <idea>", or "what are our options for ...". Also use when the user wants to discuss an idea before a decision. To investigate a GitHub issue before planning, accept an issue URL, OWNER/REPO#N, or a number prefixed with a hash sign.
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/agent-code/*)
---

# Explore mode

Help the user understand the problem. There are no fixed steps or required outputs.
Read any necessary material, including the codebase and the graph. Analyze the
problem carefully. Use diagrams as necessary. Follow the discussion at the user's
pace. Adjust explanations to the user's knowledge. Do not press the user to make
a decision or plan before the user is ready.

**Do not write code in explore mode.** You can add a document to the graph when
the user asks. This records the discussion; it does not implement a change.

## Starting from a GitHub issue

Accept an issue URL, `OWNER/REPO#N`, `#N`, or a number as a starting point.
Resolve a number without a repository name against the current repository.
Before you assess the problem, read the issue with the supplied script:

```bash
agent-code/fetch-issue.py 123
```

The script prints `ISSUE_REPO`, `ISSUE_NUMBER`, `ISSUE_URL`, `ISSUE_STATE`,
`ISSUE_TITLE`, and `ISSUE_FILE`. `ISSUE_FILE` identifies a Markdown file under
`./.tmp/`. This file contains the title, labels, body, and all comments.
Read the full file. A comment can contain a decision that the body does not contain.
The last stdout line is `RESULT=<NAME>`.

| RESULT            | Exit   | Action                                                                                                                                           |
| ----------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `SUCCESS`         | `0`    | Read `ISSUE_FILE`. Continue the investigation. Keep `ISSUE_URL` for the handoff.                                                                 |
| `ISSUE_NOT_FOUND` | `4`    | Stop. Show the resolved `OWNER/REPO#N`. Ask for the correct reference.                                                                           |
| `GH_UNAVAILABLE`  | `3`    | If a connected GitHub MCP server is available, use it to read the issue. Save the text to `./.tmp/`. Otherwise, stop and ask for the issue text. |
| `PREFLIGHT_ERROR` | `2`    | Stop. Report the error text exactly. Examples: the directory is not a repository, or the reference cannot be parsed.                             |
| `SCRIPT_FAILURE`  | `1`    | Stop. Report the error text exactly. Do not retry or use an alternative method.                                                                  |
| `SIGNAL_*`        | `129`+ | Stop. Report that the run was interrupted.                                                                                                       |

The issue describes the user's view of the problem. It is not the spec.
Check claims against the code and the graph before you use those claims.
State each difference between the issue and the checkout clearly.
Search the repository for specific terms from the issue. Identify the code
that supports each claim about behavior. Ask the user for clarification in
the conversation. Do not edit the issue from explore mode.

If the investigation identifies work for a plan, include `ISSUE_URL` in the
handoff to `/agentdev:iwe-plan`. The plan links the issue and closes the issue
after the plan is filed. If no plan is necessary, report the reason.
Examples include an existing fix, an issue outside the scope, or a duplicate.
The user decides in the conversation whether to close such an issue.

## The stance

- **Use evidence.** Propose a change only for an observed problem. Evidence can
  be a transcript, commit, issue, failed run, or code identified by an anchor.
  Collect and count the occurrences before you propose a change. Propose the
  smallest change that would have prevented those occurrences. Propose a general
  rule only when several observed cases support that rule. List imagined cases
  under "not observed". Do not design changes for imagined cases.
- **Check existing knowledge.** Before you propose an approach, use
  `iwe find --fuzzy <topic> -f keys` and
  `iwe find --lexical "<phrase>" -f keys`. Read related `data/spec/` documents,
  including `## Rationale`. Read related `data/findings/` documents and plans.
  Cite existing decisions. Do not derive those decisions again.
- **Check principles.** Read `data/concept/` early. If an approach contradicts
  a stated principle, identify the contradiction explicitly. The principle can
  be wrong. Do not leave the contradiction unstated.
- **Investigate with the user.** Ask questions as necessary. Check assumptions.
  Consider other ways to describe the problem. Identify open topics. Discuss
  one topic at a time. Do not direct the discussion toward a conclusion.
- **Use visual explanations.** Use ASCII diagrams frequently. Examples include
  state machines, data flows, module maps, and comparisons before and after a change.
  Use tables to compare options.
- **State unknowns.** Identify risks and missing information that the evidence
  shows. State which unknowns need a small experiment, called a spike.
  If only an experiment can supply the answer, that limit is a finding.

Select the methods that help the investigation. You can read the implementation,
trace a flow, compare options and their costs, or check existing decisions.
You can draw a state machine or data flow. You can identify the smallest spike
that can answer an open question. These methods are optional, not a checklist.

## Settling open questions

If the problem has open questions, ask the user one question at a time.

- **Discuss one topic per turn.** Name the topic. Continue until the user
  settles the topic. List remaining topics only after the current topic closes.
  Note findings about other topics for later. Do not start those topics.
- **Ask for one decision per question.** Give numbered options. State the
  consequence of each option. Put your recommendation first. Use the
  structured-question tool when the options fit the tool.
- **Keep the user's names and design.** Ask a separate question before you
  change a name or the design. Do not make an unannounced substitution.
- **Check behavior before discussion.** If a choice depends on system behavior,
  establish that behavior with a read-only replay or a scratch test. Then ask
  the question. Do not introduce an edge case without evidence of that case.
- **Record each answer immediately.** Use `.tmp/approved-wording-<slug>.md`.
  Copy the user's words exactly. Mark the words as approved only after an explicit yes.

## During implementation

If an implementation problem starts the investigation, first read the active
plan and current task. Do not write code. Summarize resulting decisions,
scope changes, and newly identified work. Prepare a handoff to
`/agentdev:iwe-plan`, which controls changes to the written plan.
Do not start Plan or Implement from explore mode. Do not change the plan
without telling the user.

## Capturing

Offer once to record a settled topic. Do not file a document without a user request.
When the user wants a record, select the applicable destination:

- **An idea without a commitment:** Write `data/someday/<slug>.md`.
  Link the document from `data/someday.md`.
- **A decision about behavior covered by an existing spec:** Record the decision
  and rejected alternatives in that spec's `## Rationale`. For behavior not yet
  implemented, use the plan's `## Approach`. Include that decision in the plan handoff below.
- **A measurement that does not yet settle a question:** Write
  `data/findings/<slug>.md`. Include `## Measurement`, eliminated hypotheses,
  and `## Closing`. Link the document from `data/findings.md`.
- **A procedure that a contributor will repeat:** Write `data/guides/<slug>.md`.
  Link the document from `data/guides.md`.
- **A lasting principle:** Write `data/concept/<slug>.md`.
  Link the document from `data/concept.md`.
- **An established defect, proposed feature, or actionable task:** Hand the
  settled content to `/agentdev:iwe-capture`. Specify `bug`, `feature`, or `task`.
  A defect includes code that contradicts a `data/spec/` document or reproducible
  incorrect behavior. `/agentdev:iwe-capture` controls the document format, hub
  link, and duplicate check. If the investigation started from a GitHub issue,
  include `ISSUE_URL`. The captured document links the issue and closes the issue.
  If a finding belongs to an active plan, use `## During implementation` instead.
  Return the finding to that plan. Do not create a separate document beside the plan.
- **Work ready for implementation:** Write a handoff. Ask the user to run
  `/agentdev:iwe-plan` with the handoff. The investigation supplies the plan's
  `## Context` and `## Approach`. Only the user starts `/agentdev:iwe-plan`.
  Do not invoke `/agentdev:iwe-plan` from explore mode. An answer about plan scope
  or timing is not a request to start `/agentdev:iwe-plan`. If the investigation
  started from a GitHub issue, include `ISSUE_URL`. The plan links the issue and closes the issue.
- **Approved wording:** Write `.tmp/approved-wording-<slug>.md` before the
  conversation continues. Approved document text, snippets, and messages are
  deliverables. Do not replace approved text with a description. Copy the text
  exactly into the handoff. Name the file so `/agentdev:iwe-plan` includes the
  exact approved text, not equivalent wording. Use the repository-root `.tmp/`
  scratch directory required by `AGENTS.md`. This directory is gitignored.
  The plan becomes the permanent record when the plan includes the text.
  Choose a slug for the specific approval, not the topic. Until the plan includes
  the text, this file is the only copy. Do not overwrite existing text. If the
  path exists, append under a new heading or choose a new slug. Name the file you wrote.

After each capture, run `iwe normalize` and `iwe schema validate`.

## Rules

- **Do not write code or implement changes.** This includes small fixes.
  If the user asks for implementation, direct the user to `/agentdev:iwe-plan`.
  Continue the conversation without implementation.
- **Check system claims.** Before you state a claim about the existing system,
  check the claim against the code or the graph.
- **Assess proposal costs as proposal costs.** Do not treat a proposal's own
  risks as existing system problems. Assess risks and questions caused only by
  a proposal when you assess that proposal. Reject the proposal if necessary.
  Do not start a separate topic for those risks or questions. Keep an open
  question only if its answer changes what gets built for an observed case.
- **Use the simplest approach that can work (YAGNI).** Investigate only options
  required by the current problem. Do not propose speculative abstractions,
  unrequested configuration flags, options, or parameters. Do not propose an
  interface with only one implementation or a hook for possible future use.
- **Summarize before you finish.** State the current understanding. Offer an
  optional next step: continue the investigation, capture the result, plan the
  work, return to the plan, or stop work on the topic.
- **Do not paraphrase approved text.** Preserve the exact wording or omit the
  text. Save the text in `.tmp/` at approval time. Include the text in the
  plan's tasks as fenced blocks. Conversation history is not permanent storage.
  A new session must be able to reproduce the exact text from the written plan alone.
