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
- **OpenCode:** pending.

## Task 6: planning leaves the review alone

- **Claude Code:** pending.
- **OpenCode:** pending.
