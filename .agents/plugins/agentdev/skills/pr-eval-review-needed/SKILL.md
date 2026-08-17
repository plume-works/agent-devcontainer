---
name: pr-eval-review-needed
description: 'Decide whether work just pushed to an open pull request needs a fresh AI review, because it went beyond what a reviewer already saw. Use after implementing, refactoring, or fixing anything on a branch with an open PR that has already been reviewed — especially when resolving review feedback led to changes wider than the feedback asked for, or when new behavior, files, or dependencies entered the PR since the last review. Keywords: re-review needed, stale review, reviewed changed since, beyond feedback scope, review scope.'
---

# Evaluate Whether a Re-Review Is Needed

Decide whether the current head of an open, already-reviewed pull request
contains work the last review never saw, and request a fresh review when it
does. Run this after pushing to such a PR, particularly at the end of a
feedback-resolution pass. This skill owns the outcome: it decides, and when the
answer is yes it carries the request out through
[pr-request-ai-review](../pr-request-ai-review/SKILL.md).

## Why this decision has an owner

The `ai-review-present` gate passes once any accepted AI review exists on a PR,
and keeps passing across later pushes. That is intended: a review per commit
would be prohibitively expensive. The consequence is that no check ever asks
whether the newest work was reviewed, so nothing surfaces a stale review on its
own. This skill is that missing prompt.

You have the authority to make this call and to request the review. Requesting
one is cheap and reversible; shipping unreviewed behavior behind a green gate is
neither. When genuinely balanced, request it.

## The test

Compare what is on the PR head now against what the last review saw.

**Ask: did I change anything the reviewer did not direct?**

- **No** — the diff since the last review only applies what reviewers asked
  for. That is the review working as intended, and re-reviewing it re-reads the
  reviewer's own instructions. Reply in the threads; do not request a review.
- **Yes** — behavior entered the PR that no reviewer has seen. Request a fresh
  review.

Applying feedback faithfully is not new scope, even across many files. A
one-line change can be new scope. Judge by what a reviewer would need to look at
again, not by diff size.

## What counts as beyond the feedback

Request a review when the work since the last one did any of these:

- Added or changed runtime behavior that no thread asked for, including a fix
  you noticed on your own along the way.
- Generalized a requested fix into a refactor, or applied it to call sites
  outside the one raised.
- Changed a public interface, a schema, a configuration contract, or a
  dependency.
- Changed security-relevant, authentication, permission, or credential-handling
  code for any reason.
- Resolved a thread by a materially different approach than the one discussed.
- Merged the base branch and resolved conflicts by making a judgment call rather
  than taking one side cleanly.

Do not request a review when the work since the last one was only:

- The exact edits reviewers requested, applied as discussed.
- Formatter, linter, or generated-file output.
- Comment, docstring, or documentation wording with no behavioral change.
- A rebase or clean base merge with no conflict judgment.
- Test additions that pin already-reviewed behavior.

## Establish what the last review saw

Do not answer from memory of the session — a plan statement or an earlier
summary is not evidence of what was reviewed. Read the PR:

```bash
gh pr view <pr> --json reviews,headRefOid \
  --jq '{head: .headRefOid, reviews: [.reviews[] | {author: .author.login, state: .state, commit: .commit.oid}]}'
```

Then diff the newest reviewed commit against the current head to see exactly
what has landed since:

```bash
gh pr diff <pr> --name-only          # scope of the PR overall
git diff <last-reviewed-sha>..HEAD   # what no review has seen
```

If no AI review exists at all, this skill does not apply — the gate itself is
unsatisfied, and that is a merge-time concern for `/agentdev:pr-merge`.

## Report the decision

State the call and the reason in one or two sentences:

- Requesting — name what entered the PR beyond the feedback, then run
  [pr-request-ai-review](../pr-request-ai-review/SKILL.md) to post it.
- Not requesting — say that the changes since the last review only apply what
  reviewers asked for.

Report the decision even when the answer is no; a silent skip is
indistinguishable from never having considered it.
