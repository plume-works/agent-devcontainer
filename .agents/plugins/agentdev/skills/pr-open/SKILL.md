---
name: pr-open
description: 'Create a GitHub pull request from conversation context — or refresh the branch existing PR in place — with accurate title/body generation, branch sync, and remote push. Use when asked to open/create/submit a PR, draft a pull request, sync or update a PR description, or finalize changes after implementation. Keywords: open pr, create pr, submit pr, update pr, sync pr description, pull request, github pr, draft pr, ready for review.'
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/*)
---

# Open PR

This skill instructs AI agents on how to create GitHub pull requests from conversation context
with meaningful titles and proper formatting. The AI agent
should analyze the conversation, extract PR details, and create the pull request directly
without pausing for confirmation.

When the current branch already has an open pull request, this skill updates
that pull request in place instead of creating a second one: the same title and
body generation runs, and the result is written to the existing PR.

## GitHub Access

The GitHub CLI (`gh`) is the primary GitHub client for this skill, and a
connected GitHub MCP server is a secondary fallback used only when `gh` is
missing or unauthenticated. Every GitHub step below is written against `gh`:

- `gh pr list` (through `find-branch-pr.sh`) - detect an existing pull request
- `gh pr create` - create the pull request
- `gh pr edit` - update an existing pull request's title and body
- `gh issue list` - list recent issues when an issue number is missing
- `gh pr view` - fetch PR details after creation

If `gh` is unavailable or unauthenticated, fall back to the equivalent GitHub
MCP operations (for example a pull-request listing tool for detection, or a
`create_pull_request` tool for creation) only when the active environment
documents them; do not assume particular MCP tool names. That fallback covers
existing-PR detection too: `find-branch-pr.sh` reports every unusable-`gh`
condition as `RESULT=GH_UNAVAILABLE` (exit `6`) — distinct from the preflight
failures no fallback can rescue — and prints `HEAD_BRANCH` before it checks
`gh`, so the head branch to look up is available even then. If neither path
works, stop and report the blocker.

The branch is always pushed with local `git` through `push-branch.sh` — never
through a GitHub API or MCP tool.

## PR Description Source of Truth

The PR body content **MUST** be generated using the
[pr-gen-description](../pr-gen-description/) skill.

The pr-open skill is responsible for:

- detecting whether the branch already has a pull request
- optional issue linking in title/body when issue context exists
- delegating mandatory formatting and validation to the `local-reformat` skill
- delegating staging and commit creation to the `git-commit` skill
- delegating branch sync with the base branch to the `update-branch` skill
- pushing the branch to its remote head ref
- GitHub PR creation and PR title/body update through `gh`

## Bundled Scripts

Use these exact helper scripts instead of retyping inline shell commands:

- [find-branch-pr.sh](scripts/find-branch-pr.sh) resolves the single pull request whose head is the current branch, and fails loudly when more than one matches.
- [push-branch.sh](scripts/push-branch.sh) verifies upstream tracking, pushes the branch when needed, and blocks on divergence without ever rewriting history.

The detailed PR description structure, section requirements, and quality checks
are defined in the [pr-gen-description](../pr-gen-description/) skill
and **MUST NOT** be duplicated here.

## Workflow for AI Agents

When this skill is invoked, the AI agent **MUST** follow these steps:

### 1. Context Analysis Phase

Review the entire conversation history and git changes to extract PR details:

- Identify what work was completed during the conversation
- Review git diff and git status to see actual changes made
- Extract key details: what was changed, why, which files were affected
- Determine the type of changes (feature, bugfix, refactor, etc.)
- Check if there's a related issue number mentioned in the conversation (optional)

Context signals for PR type:

- Feature signals: new functionality added, new files created, capabilities extended
- Bugfix signals: fixed error, resolved issue, corrected behavior
- Refactor signals: improved code structure, reorganized code, better patterns
- Documentation signals: updated README, added comments, wrote guides
- Test signals: added test coverage, modified test cases

### 2. Existing Pull Request Detection

Before doing any work, resolve whether this branch already has a pull request:

```bash
${CLAUDE_SKILL_DIR}/scripts/find-branch-pr.sh
```

The last stdout line is `RESULT=<NAME>`; it decides the rest of the run:

| RESULT             | Exit | Meaning                                                  | Action                                                                                                                                                                                                                                |
| ------------------ | ---- | -------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`          | `0`  | Exactly one open PR has this head branch                 | **Update mode.** Keep `PR_NUMBER`, `PR_BASE`, and `PR_TITLE`; the PR will be edited in place, never recreated.                                                                                                                        |
| `NO_PR_FOUND`      | `3`  | No open PR for this branch                               | **Create mode.** Continue and create the PR at the end. Use `main` as the base unless the user says otherwise.                                                                                                                        |
| `MULTIPLE_PRS`     | `4`  | Several PRs share this head branch                       | **STOP.** Show the candidates and ask which PR to update.                                                                                                                                                                             |
| `PROTECTED_BRANCH` | `5`  | Branch, or the upstream it tracks, is `main` or `master` | **STOP.** A PR head must be a feature branch — see the error handling section below.                                                                                                                                                  |
| `GH_UNAVAILABLE`   | `6`  | `gh` is missing, unauthenticated, or its API call failed | **Fallback.** Detect the PR through the GitHub MCP server as described under GitHub Access, using the printed `HEAD_BRANCH`; the result selects update or create mode exactly as above. **STOP** only if no such server is connected. |
| `PREFLIGHT_ERROR`  | `2`  | Not a repo, detached HEAD, or a bad argument             | **STOP.** Report the blocker verbatim.                                                                                                                                                                                                |
| `SCRIPT_FAILURE`   | `1`  | The script broke                                         | **STOP.** Report the blocker verbatim; do not retry or work around it.                                                                                                                                                                |

In update mode, `PR_BASE` — not an assumed `main` — is the base branch for the
remaining steps. Pass `--state all` only when the user explicitly asks to work
against a closed or merged PR.

The script also prints `HEAD_BRANCH` on every run. That is the pull request
head: the configured upstream branch name when the local branch tracks a
differently named ref, and the local branch name otherwise. Use `HEAD_BRANCH`
— never the local branch name — as the head when creating the PR, so it matches
the ref `push-branch.sh` writes to.

### 3. Mandatory Local Reformat

**CRITICAL:** Before reviewing, committing, or creating a PR, the AI agent
**MUST** invoke and follow the `local-reformat` skill.

Run every formatter and validation required by that skill. Do not substitute a
partial set of formatters or bypass failures. If `local-reformat` cannot
complete successfully, stop PR creation and report the actionable failure to
the user.

### 4. Commit Any Uncommitted PR Scope

After `local-reformat` completes successfully, inspect `git status`. If the
PR-scope changes are uncommitted, invoke and follow the `git-commit` skill to
stage only that scope and create one conventional commit before drafting a PR.

If the caller already created the scoped commit, verify the branch is clean for that scope and do not
create a duplicate or empty commit. If a formatter leaves new tracked changes,
commit those changes before continuing. Do not reimplement the commit-message
or staging workflow inline.

### 5. Branch Sync with the Base Branch

**CRITICAL:** Before PR-body generation, sync the current branch with its base
branch (`PR_BASE` in update mode, otherwise `main`) using the
`/agentdev:update-branch` skill.

The AI agent **MUST** invoke and follow the `/agentdev:update-branch` skill instead of
re-implementing merge logic inline.

If `update-branch` reports unresolved conflicts or requires user input, stop
PR creation and ask the user to resolve or confirm conflict decisions first.

### 6. Post-sync Formatter and Commit Check

Branch synchronization can introduce formatter changes. Run the required
`local-reformat` workflow once more after `update-branch`. If it changes
tracked files, invoke `git-commit` to make one focused formatting commit. Do
not continue with formatter edits left uncommitted.

### 7. Optional Issue Linking

Issue linking is recommended but not required.

**How to find an issue number when available:**

1. Search conversation history for explicit issue references:
   - "for issue #42"
   - "closes #15"
   - "related to #23"
   - GitHub issue URLs containing issue numbers

2. If no issue number is found in conversation:
   - Check if there are recent issues that match this work:
     - Run `gh issue list --limit 10` (add `--repo <owner>/<repo>` when the
       working directory is not the target repository)
     - Start with the default open state
     - If needed, broaden the query with `--state all`

- Ask the user if they want to link an issue: "Would you like to link an issue to this PR?"

3. If no issue is provided:

- Continue PR creation without issue linking
- Use a concise title without issue prefix

In update mode, preserve the existing title's issue prefix (for example `[#42]`)
rather than re-deriving the link.

### 8. PR Draft Construction

**CRITICAL:** Run this only after the branch is synchronized and clean, so the
description reflects the final changes the PR will contain.

Generate the PR description by following the
[pr-gen-description](../pr-gen-description/) skill. That skill performs the
change review; do not review the diff separately here. Give it the base branch
to compare against — `origin/${PR_BASE}` in update mode, `origin/main` in create
mode — and expect it to report any uncommitted working-tree changes as out of PR
scope rather than folding them into the body.

Use the generated output as the PR body, and use one of these title formats:

- If issue is available: `[#issue-number] Brief description`
- If issue is not available: `Brief description`
- Keep the title description concise and outcome-focused

In update mode, keep `PR_TITLE` unchanged when it still describes the branch
accurately — an update should not churn a good title.

### 9. Proceed Without Confirmation

Do **not** pause to ask the user to approve the draft. Once the title and body
are generated, continue directly to the branch push and PR creation or update.
If any later operation changes the branch diff, regenerate the title and body
through `pr-gen-description` first.

- Do not present the draft and wait for a "yes" before creating or updating the PR
- Still stop and surface the issue to the user only when a blocking error
  occurs (e.g. push divergence or a failed PR creation) — these require user
  input to resolve
- Afterwards, report the resulting PR URL/number

### 10. Push the Branch

**CRITICAL:** Before creating or updating the PR, push the branch so the remote
head ref contains every commit the body describes.

Run the bundled helper:

```bash
${CLAUDE_SKILL_DIR}/scripts/push-branch.sh
```

The script handles these cases:

- no upstream branch: pushes with `-u <remote> <branch>` using the configured `--remote` value or the default remote — `SUCCESS`, `ACTION=push-with-upstream`
- local branch ahead of upstream: pushes changes to the configured upstream — `SUCCESS`, `ACTION=push`
- branch up to date: `SUCCESS` with `ACTION=none`, without pushing
- branch behind its upstream: `NOT_FAST_FORWARD` (`3`) with fast-forward recovery instructions
- branch diverged from upstream: `NOT_FAST_FORWARD` (`3`) with merge-based recovery instructions
- push rejected by the remote: `PUSH_REJECTED` (`4`)
- `--remote` conflicts with the configured upstream remote: `PREFLIGHT_ERROR` (`2`) so the user can reconcile the remote selection
- current branch is `main` or `master`: `PROTECTED_BRANCH` (`5`) without pushing

Use `--remote <name>` or `--branch <name>` when the default remote or branch should be overridden.

On any `RESULT` other than `SUCCESS`, display the script's actionable error
output and abort.
Never force-push, and never update the branch ref through a GitHub API or MCP
tool — reconcile locally with `/agentdev:update-branch` and rerun this step.

### 11. Create or Update the Pull Request

In **update mode**, edit the existing PR in place with `gh`. Write the body to a
file under `./.tmp/` (relative to the repository root; create the directory if
missing) so shell quoting cannot corrupt Markdown:

```bash
gh pr edit <PR_NUMBER> --title "<new title>" --body-file ./.tmp/pr-body.md
```

Pass `--title` only when the title actually changed. Leave draft state, base
branch, labels, reviewers, and assignees untouched — an update changes text
only. Report the PR URL, and state whether the title changed, whether the body
changed, and whether the push moved the head ref.

In **create mode**, create the PR with `gh`, writing the body to a file under
`./.tmp/` for the same quoting reason:

```bash
gh pr create --title "<title>" --body-file ./.tmp/pr-body.md \
  --base "<base>" --head "<HEAD_BRANCH>"
```

- `--title` (required): full PR title
- `--body-file` (required): the generated markdown from the
  [pr-gen-description](../pr-gen-description/) skill
- `--base` (required): target branch. If not explicitly provided by user or
  repo policy, use `main`
- `--head` (required): the `HEAD_BRANCH` value reported by `find-branch-pr.sh`,
  which is the configured upstream branch name rather than the local branch
  name whenever the two differ
- `--draft` (optional): pass when the user wants a draft PR
- `--repo <owner>/<repo>` (optional): pass when the working directory is not
  the target repository

**Important:**

- Do not duplicate or re-interpret the prompt's section requirements here
- After successful creation, display the PR URL that `gh pr create` prints
- Confirm: "Pull request created successfully: [URL]"

If `gh` is unavailable or unauthenticated, fall back to the connected GitHub
MCP server's pull-request creation operation with the same title, body, base,
and head values.

### 12. Error Handling

Handle common error scenarios gracefully:

**Issue number not found:**

```
No related issue number found.
Proceeding without issue linking.
```

**No git changes:**

```
Cannot create PR: No changes detected in the working directory.
Please make and commit your changes first.
```

**GitHub authentication/authorization failure:**

```
The GitHub request failed due to authentication or missing permissions.
Run `gh auth status` and verify the token scopes (typically `repo`).
If you are falling back to a GitHub MCP server, verify its authentication and
token scopes instead.
```

**Not on a feature branch** (`find-branch-pr.sh` or `push-branch.sh` reports `PROTECTED_BRANCH`):

```
Cannot continue: you're on the main/master branch.
A pull request head must be a feature branch.

Create one with:
  git checkout -b feature/your-feature-name

Then rerun this skill.
```

**Multiple pull requests share the branch** (`find-branch-pr.sh` reports `MULTIPLE_PRS`):

```
Found several pull requests with this head branch.
Tell me which PR number to update; I will not guess.
```

**No conversation context:**

```
I don't have enough context to create a PR. Could you please provide:
- What changes were made?
- What was tested?
```

**PR creation failed:**

```
Failed to create pull request: [error message]
Please check `gh` connectivity, authentication (`gh auth status`), and token
permissions; check the GitHub MCP server only if it was used as the fallback.
```

**Merge conflict while syncing with `origin/main`:**

```
Cannot continue PR creation: merge conflicts occurred while merging origin/main.
Please resolve conflicts, commit the merge, and retry PR creation.
```

## Ownership

The AI agent **SHALL NOT** claim authorship or co-authorship of the pull request.
The PR is created on behalf of the user, who is **FULLY** responsible for its content.

Do not add any "Created by AI" or similar attributions to the PR body unless
explicitly requested by the user.

## PR Body Guidance

For complete PR-description instructions and examples, use the
[pr-gen-description](../pr-gen-description/) skill.
