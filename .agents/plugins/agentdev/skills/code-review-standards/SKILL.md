---
name: code-review-standards
description: Apply review standards and write pull request descriptions. Use when asked to review code, assess a change for correctness or maintainability, or draft a PR description. Commit creation belongs to /agentdev:git-commit and PR publishing belongs to /agentdev:pr-open.
---

# Code Review Standards

Write high-quality pull request descriptions and conduct effective code reviews using established best practices. Use the Coding Conventions section of the `AGENTS.md` at the root of the repository being reviewed as the source of truth for project-specific style, testing, and error-handling expectations.

## When to Use This Skill

- Write PR descriptions for GitHub
- Review code for quality and standards compliance
- Ensure PR documentation is complete
- Apply clean code principles to reviews
- Evaluate code for maintainability
- Provide constructive feedback on changes
- Validate against project coding standards

## Prerequisites

- Understanding of project coding standards (see AGENTS.md)
- Knowledge of changed files and their purposes
- Context about what the changes accomplish
- Understanding of why specific design decisions were made
- Familiarity with the codebase being reviewed

## Scope

This skill covers review-specific workflow and PR-writing structure. Do not restate broad engineering rules from the shared instructions unless the review needs a tighter, task-specific requirement.

## PR Description Workflow

### Golden Rules

1. **Use imperative mood**: "Fix", "Add", "Refactor" (not "Fixes", "Added", "Refactoring")
2. **Write for clarity**: Assume reader knows nothing about your changes
3. **Be comprehensive**: Include what changed and why, not just what
4. **Avoid tables**: Never use per-file changes tables or line counts
5. **No marketing**: Never add AI assistant ads or AI tool information
6. **No invisible content**: Never use HTML comments or hidden Unicode
7. **Treat as permanent project history**: Apply the highest standards

### Recommended Template

Create a comprehensive pull request description.

1. Start with concise summary (1-2 lines):

   ```
   Add timeout handling to serial communication driver
   ```

2. Add "What changed" section describing modifications:

   ```markdown
   ## What Changed

   - Implement exponential backoff retry logic for failed reads
   - Add configurable timeout settings to the client constructor
   - Remove deprecated synchronous request helpers
   - Add comprehensive timeout error messages
   ```

3. Add "Why" section explaining motivation:

   ```markdown
   ## Why

   Upstream timeouts cause worker tasks to block indefinitely,
   preventing graceful shutdown. This change allows workers to recover
   and log meaningful errors for debugging.
   ```

4. Add the two verification sections. Omit anything CI already runs and
   anything another document records — what is left is usually short, and an
   empty `## Verification` under green CI is the expected outcome:

   ```markdown
   ## Verification

   - [x] Retry recovers from an unresponsive endpoint
     - **Evidence:** pointed the client at a black-holed port by hand; the
       timeout fired at 5s and the second attempt succeeded.

   ## Reviewer Handoff

   - [ ] Behavior under a proxy that half-closes the connection
     - **Closed by:** a human on the staging network — no CI runner reaches
       the proxy.
   ```

   `## Verification` holds only closed items, each `- [x]` with an
   `**Evidence:**` child naming what closed it. `## Reviewer Handoff` holds
   only open items, each `- [ ]` with a `**Closed by:**` child naming the party
   who can close it. Neither section may hold the other's box type.

5. Add "Related issues" if applicable:

   ```markdown
   ## Related Issues

   Closes #45
   Related to #42, #43
   ```

6. Add "Breaking changes" if any:

   ```markdown
   ## Breaking Changes

   - Changed `serial_read()` timeout parameter from milliseconds to seconds
   - Removed `sync_read()` function (use async variant instead)
   ```

## Review Workflow

Evaluate code changes against the shared engineering standards, then focus your review on findings, evidence, and impact.

**Code is the source of truth.** Base the review on the actual diff — analyze every branch change with git diff, file listings, and code search — not on the commit messages or PR description. Read those with healthy skepticism: flag where they misstate the change, hide side effects, overclaim, or leave modifications undocumented.

### What To Check

1. Correctness and behavioral regressions
2. Missing or weak tests for changed behavior
3. Maintainability risks that materially raise future cost
4. Security or performance issues with concrete impact
5. Standards violations that conflict with the shared engineering guidelines

### How To Write Findings

Write helpful, actionable review comments.

**Good feedback example:**

```
The mutex lock here could be a deadlock risk if `process_data()`
throws an exception. Consider using RAII pattern or try/finally
to ensure lock is always released.
```

**Poor feedback example:**

```
This is bad. Fix it.
```

**Guidelines:**

1. **Be specific**: Point to exact lines and explain why it's an issue
2. **Suggest solutions**: Provide code examples when helpful
3. **Use neutral language**: Avoid judgmental tone
4. **Consider context**: Ask questions if you don't understand intent
5. **Praise good code**: Acknowledge well-written sections
6. **Focus on impact**: Explain how the issue affects functionality/maintenance

### Common Finding Categories

```
## Clarity Issues
- "Variable name X is ambiguous; consider Y for clarity"
- "This logic could be extracted to method Z for reuse"

## Potential Bugs
- "This could fail if Z is null; add guard clause"
- "Race condition possible here if called from multiple threads"

## Performance
- "O(n²) loop could be optimized to O(n) using a set"
- "String concatenation in loop creates many allocations"

## Testing
- "This error case isn't tested; add test_X"
- "Coverage would be higher if we test the else branch"

## Architecture
- "This couples module A to module B unnecessarily"
- "Consider using pattern X instead for better separation"
```

## Responding To Review Feedback

Update PR based on code review feedback.

1. Make requested code changes
2. Invoke [git-commit](../git-commit/) to stage the accepted feedback changes
   and create the conventional commit. Do not duplicate its staging or
   commit-message workflow here.

3. Update PR description if scope changed:
   - Add new accomplishments to "What Changed"
   - Update `## Verification` and `## Reviewer Handoff`. Work closed since
     the last review moves from `## Reviewer Handoff` to `## Verification`
     with the evidence that closed it — items travel in that direction
     only, never back
   - Document why feedback was accepted or rejected
   - Only amend the existing PR description when the overall scope or test instructions materially changed; preserve prior content and append deltas instead of rewriting from scratch.

4. Reply to comments:
   - Acknowledge the feedback
   - Explain changes made
   - Link to specific commits

5. Request re-review when ready

## Troubleshooting

| Issue                               | Solution                                             |
| ----------------------------------- | ---------------------------------------------------- |
| PR description too technical        | Add "Why" section explaining user impact             |
| Feedback seems nitpicky             | Consider if it genuinely improves maintainability    |
| Author defensive about feedback     | Keep tone neutral; focus on code, not person         |
| Conflicting feedback from reviewers | Discuss in thread; find consensus or escalate        |
| Changes seem unnecessary            | Ask for clarification of impact/rationale            |
| Too many comments per review        | Prioritize critical issues; discuss style separately |

## References

- Coding Conventions in the reviewed repository's root `AGENTS.md`
- [Generate pull request description](../pr-gen-description/)
- [Create conventional commits](../git-commit/)
