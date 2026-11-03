# Handoff: Ship obligations reviewer (exploration in progress)

Temporary. This file tracks an open `/agentdev:iwe-explore` thread so its
decisions show up as diffs. It is deleted when the thread is handed to
`/agentdev:iwe-plan`, which becomes its durable home.

## Trigger

On #657 the Shipper set the listed bug to `stage: done` without writing its
`## Fix` (Shipper step 6), and its step 7 re-check missed it. Nothing enforces a
done bug's Fix: the bug-lifecycle plan decided "no schema rule, CI check, or
refusal gate" (`data/plans/20261102-bug-lifecycle-and-sections`).

## Decided

- **D1** — The Shipper enforces a listed bug's `## Fix`.
- **D2** — A plan reviewer: one agent, one rubric built from Ship's
  obligations, run when a plan is filed and on Ship's result.
- **D3** — Ship-side placement is after the commit: `/iwe-ship` dispatches the
  Shipper, which commits, then dispatches the reviewer from a fresh context; a
  gap becomes a follow-up fix commit.
- **D4** — Verify moves out of the Shipper's context: filed as
  `data/backlog/ship-verifies-before-dispatch`.
- **D5** — A done bug's `## Fix` is enforced mechanically by a checker CLI that
  a pre-commit hook runs over `data/bugs/*.md`, failing a `stage: done` bug with
  no `## Fix` heading. It is a CLI, not a pytest file; tests cover the CLI on
  made-up bug files. CI enforces it through its existing pre-commit runs.

## Findings

- **F1** — `iwe` 0.29.3's document schemas take conditionals only inside
  `frontmatter`. A document-level `if`/`then` or `anyOf` fails with "unknown
  keyword", so a bug schema cannot require `## Fix` only when `stage: done`.
- **F2** — Mechanical graph gates already exist as pre-commit hooks running a
  pytest file over the whole directory: `plan-checkboxes`, `no-status-field`.
  CI runs pre-commit on the pull request's range and on `--all-files` in
  `ci.yml`.
- **F3** — Every done bug carries a `## Fix` as of `12ab309f`, so a gate over the
  whole graph starts green.

## Current question

Plan side: is the reviewer a new agent dispatched beside the Durable Knowledge
Auditor, or the auditor's rubric widened?

## Queued

- Does one rubric hold, or one agent with plan and ship modes?
- Under D3, who writes the follow-up fix commit?
- Recording the reversal of the bug-lifecycle "nothing enforces" decision.
