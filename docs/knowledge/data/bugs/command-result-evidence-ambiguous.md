---
type: bug
description: An evidence line that names a check command and says it passed, with no commit, is accepted by one iwe-verifier run and rejected as residue by the next, because the evidence rule leaves such a line undecided and asks for the commit to be named from inside that same commit.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-28T09:00:00Z
sources:
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: docs/knowledge/data/spec/plan-checkbox-evidence.md
- resource: scripts/e2e/iwe-workflows/test_iwe_workflows_codex.py
---

# Bug: Command-result evidence is judged inconsistently

## Symptom

On Codex and OpenCode the implementer closes a task with an evidence line that
names the plan's check command and says it passed, and cites no commit:

``` markdown
- [x] Write `e2e/loop.txt` containing `loop`.
  - **Evidence:** `grep -qx loop e2e/loop.txt` passed.
```

`iwe-verifier` judges that line both ways. In one `/agentdev:iwe-implement-all`
run on Codex it called the line on both plans non-traceable residue, a CRITICAL
with "untick it", so the coordinator spent a second implementer round and a
second Verify per plan replacing it with a commit citation. In the next run, on
the same fixture and catalog, the verifier accepted lines of the same form on
both plans. OpenCode's verifier accepted them as well. On Claude Code the
implementer cites the task's commit and the question does not come up.

The cost of a rejection is one extra implement-and-verify round per plan. The
cost of an acceptance is worse: Ship runs the same Verify, so a plan the
Implement loop reported ready can still be blocked at Ship by a run that judges
the same line the other way.

## Reproduction

1. Reinstall the catalog into Codex with
   `.devcontainer/scripts/reinstall-agentdev-codex.sh`.
2. Run
   `E2E_RUN_LIVE=1 uv run pytest -m e2e "scripts/e2e/iwe-workflows/test_iwe_workflows_codex.py::test_implement_all"`
   several times.
3. In each run's `~/.codex/sessions` rollouts, read the plan's `- **Evidence:**`
   line after the first implementer round and the first `iwe-verifier` verdict.
   With the same command-result line, some runs report `Blocked` with the
   residue CRITICAL, followed by an evidence-repair implementer round, and
   others report `Ready to ship`.

Reasoning effort does not settle it. With `gpt-5.6-sol`, the first Verify of a
plan rejected the line in 2 of 4 plan runs at `low` effort and 2 of 6 at
`medium`, which `E2E_CODEX_REASONING_EFFORT=medium` selects. At both efforts the
implementer's first evidence line cited the check alone.

## Root cause

The rule names the line it allows and the line it forbids, but not where this
line falls between them. The implementer rulebook and the spec allow "the test
run and its result" as evidence, and both rulebooks call "raw command stdout
transcribed as evidence" residue. A named, re-runnable check plus its outcome is
neither: it is not stdout, and it is not a durable record of a run a later
session can look up. The verifier settles it by judgment on every run, and the
judgment flips between runs.

The implementer's other rules then push it toward that line. Evidence must "name
the commit", but the tick and its evidence line must land "in the same commit as
the code they describe", and a commit cannot name its own hash. The rulebook
does not say how to name a commit that does not exist yet when the line is
written. The harnesses resolve it differently, from the same rulebook:

- **Claude Code** commits the code first, ticks the box citing the new hash,
  amends the tick into that commit, and, because the amend changes the hash,
  rewrites the line to cite the commit's subject and amends again.
- **Codex** writes the file, runs the check, ticks the box, and makes one commit
  holding both, as the same-commit rule reads. No commit exists when it writes
  the line, so it cites the check. Its repair round then cites the commit from a
  separate follow-up commit, which breaks the same-commit rule.
- **OpenCode** cites the check and names the task commit by its subject.

## Fix

Unfixed. Decided by the maintainer: a named check plus its result is evidence
only together with the commit that holds the change it checks. A check on its
own is not evidence. The spec in [Plan checkbox
evidence](../spec/plan-checkbox-evidence.md) and both rulebooks change to say so
in the same words.

Since the tick lands in the same commit as the code, the fix also has to say how
that commit is named, because its hash is unknown when the line is written.

The `test_implement_all` e2e checks pass whether or not a fix round runs, since
a fix round is the loop working as specified.

## Key references

Verified anchor points (line numbers as of 2026-10-28):

- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:63` — Step 6, "the
  commit, the test run and its result, the CI run" as evidence
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:65` — "raw command
  stdout transcribed as evidence" listed as residue
- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md:62` — the CRITICAL for
  evidence not "traceable to a commit, test run, or CI run"
- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md:63` — the same residue
  list on the verifier side
- `docs/knowledge/data/spec/plan-checkbox-evidence.md:31` — Requirement: A
  ticked task carries the evidence that closed it
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md:215` — the tick and
  its evidence line in "the same commit as the code they describe"
- `docs/knowledge/data/spec/plan-checkbox-evidence.md:67` — Scenario: A tick
  lands in a commit
- `.agents/plugins/agentdev/skills/iwe-implement-all/SKILL.md:21` — the
  coordinator's fix-round re-dispatch that a rejection triggers
- `scripts/e2e/iwe-workflows/test_iwe_workflows_codex.py:208` — the e2e check
  that allows more than one implementer round per plan
