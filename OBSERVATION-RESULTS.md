# Observation results

Evidence wording for the observation boxes of
`data/plans/20261102-adversarial-review`, collected here until every harness
has run. Copy each box's lines into its `- **Evidence:**` line on
`iwe/adversarial-review/iter-1-impl` when the box ticks.

## Task 5: a code review

- **Claude Code:** Claude Code 2.1.318 (cloud, `claude-opus-5-5`), session
  `session_01Q7BhLsjCAGNdn2tLU8PM6G` on `scratch/adversarial-review-fixture`:
  one `Agent` dispatch of `agentdev:iwe-adversarial-reviewer` with a prompt of
  only plan key, target `code`, and approvals; the reviewer ran three
  read-only `Bash` calls and no edit or dispatch; A1 names "Slugs cannot leave
  the plans directory" with `scripts/slug_guard.py:6`;
  `git status --porcelain` empty before and after.
- **OpenCode:** OpenCode session `ses_e5825cbeeffenHmG7Bgao3qB4h`
  (`openai/gpt-6.1-sol`, agent `build`) in `/workspaces/agent-devcontainer`,
  from its exported transcript: the `iwe-adversarial-review` skill loaded once
  with the request; one `subagent` call to `iwe-adversarial-reviewer` with a
  prompt of only plan key, target `code`, and approvals (sub-session
  `ses_e5825bcddffeotiDktQmmwlyXA`); A1 names "Slugs cannot leave the plans
  directory" and "A nested slug is refused" with `scripts/slug_guard.py:6` and
  `is_safe_slug("a/b")` returning True; the final message re-posts the report;
  the session's worktree snapshot is the same tree at start and end with no
  changed files, and the reviewer's `git status --porcelain` was empty before
  and after.

## Task 6: planning leaves the review alone

- **Claude Code:** Claude Code 2.1.318 (cloud, `claude-opus-5-5`), session
  `session_01Q7BhLsjCAGNdn2tLU8PM6G` after `/clear`, on
  `scratch/adversarial-review-fixture`:
  `/agentdev:iwe-plan Plan a change so that is_safe_slug in scripts/slug_guard.py also rejects backslashes.`
  wrote `data/plans/20261104-slug-guard-backslash` in create mode, and
  `iwe schema validate` passed. Across its 21 tool calls, the only `Skill`
  load was `agentdev:iwe-audit`, inside the Durable Knowledge Auditor, and the
  only `Agent` dispatch was `agentdev:Durable Knowledge Auditor`; no call
  loaded `iwe-adversarial-review` or dispatched `iwe-adversarial-reviewer`.
- **OpenCode:** OpenCode session `ses_e5821c2aeffdP6vszCpTPCvBCj`
  (`openai/gpt-6.1-sol`, agent `build`), from its exported transcript: the
  request loaded `iwe-plan`, which wrote
  `data/plans/20261104-slug-guard-backslashes` in create mode, and
  `iwe schema validate` printed no violations. The only skills loaded were
  `iwe-plan` and `git-commit`, and the only `subagent` call was
  `durable-knowledge-auditor` (sub-session `ses_e58206d9affeAwq1qRugv0M01i`);
  no call loaded `iwe-adversarial-review` or dispatched
  `iwe-adversarial-reviewer`.
