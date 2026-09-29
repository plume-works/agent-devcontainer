---
name: git-commit
description: Generate conventional commit messages automatically. Use when user runs git commit, stages changes, or asks for commit message help. Analyzes git diff to create clear, descriptive conventional commit messages. Triggers on git commit, staged changes, commit message requests.
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/*)
---

# Git Commit Skill

Generate conventional commit messages from the relevant git diff.

## When to Use This Skill

- ✅ `git commit` without message
- ✅ User asks "what should my commit message be?"
- ✅ Staged changes exist
- ✅ User mentions a commit or conventional commit
- ✅ Before creating commits

## Prerequisites

- A git repository with staged or unstaged changes to summarize
- Access to the relevant diff, status, or commit context

## Create the Commit Through the Script

Create every commit with [git-commit.sh](scripts/git-commit.sh); never run
`git commit` directly. It refuses — before `git commit` runs — on `main`,
`master`, the remote's default branch, a detached `HEAD`, and — when the
remote exists — a remote whose default branch cannot be determined. Pass the
`git commit` arguments after `--`:

```bash
${CLAUDE_SKILL_DIR}/scripts/git-commit.sh -- -m "<subject>" -m "<body>"
${CLAUDE_SKILL_DIR}/scripts/git-commit.sh -- -F .tmp/commit-message.txt
```

`--remote <name>` selects the remote whose default branch is protected
(default: `origin`). The last line of stdout is always `RESULT=<NAME>`; match
on that name, not on a bare number.

| RESULT             | Exit                | Meaning                                                    | Action                                                                                                                                |
| ------------------ | ------------------- | ---------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`          | `0`                 | The commit was created                                     | Report the commit.                                                                                                                    |
| `PROTECTED_BRANCH` | `3`                 | The current branch is a default branch; nothing ran        | **STOP.** Tell the user work must go on a feature branch and offer `/agentdev:git-new-branch`, which carries the uncommitted changes. |
| `COMMIT_FAILED`    | `4`                 | `git commit` ran and failed; its status is `GIT_EXIT_CODE` | Read `git commit`'s output: stage changes if nothing was staged, or fix what a hook reported, then rerun.                             |
| `DEFAULT_UNKNOWN`  | `5`                 | The remote exists but its default branch is unknown        | **STOP.** Report the error. Ask the user to run `git remote set-head <remote> --auto` or authenticate `gh`, then rerun.               |
| `PREFLIGHT_ERROR`  | `2`                 | Bad usage, not a repository, or a detached `HEAD`          | **STOP.** Report the error verbatim.                                                                                                  |
| `SCRIPT_FAILURE`   | `1`                 | The script broke                                           | **STOP.** Report the blocker verbatim; do not fall back to `git commit`.                                                              |
| `SIGNAL_*`         | `129`, `130`, `143` | Interrupted by HUP, INT, or TERM                           | **STOP.** Check `git status` before rerunning.                                                                                        |

Never bypass a `PROTECTED_BRANCH` refusal by running `git commit` yourself.

## What I Generate

### Conventional Commit Format

```text
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**

| Type       | Use when                                     |
| ---------- | -------------------------------------------- |
| `feat`     | Adding new functionality or a new workflow   |
| `fix`      | Correcting broken or incorrect behavior      |
| `docs`     | Changing documentation only                  |
| `style`    | Formatting-only changes                      |
| `refactor` | Restructuring code without changing behavior |
| `perf`     | Improving runtime performance                |
| `test`     | Adding or correcting tests                   |
| `build`    | Changing build or packaging behavior         |
| `ci`       | Changing CI or CD automation                 |
| `chore`    | Maintenance outside product behavior         |
| `revert`   | Reverting an earlier commit                  |

## Step-by-Step Workflows

### Workflow: Turn a Diff Into a Conventional Commit

1. Review the staged changes first.
   - Prefer the staged diff because it reflects exactly what will be committed.
   - If nothing is staged yet, review the working tree and either stage a coherent subset or tell the user the message is based on unstaged changes.
   - Identify the primary outcome of the change rather than listing files.

2. Choose the commit `type` from the behavior change.
   - Use `feat` for new user-facing capability or workflow.
   - Use `fix` for corrected behavior or bug resolution.
   - Use `refactor`, `perf`, `test`, `docs`, `build`, `ci`, `style`, or `chore` only when that is the main purpose of the diff.
   - If the diff mixes unrelated purposes, recommend splitting the commit instead of forcing a vague type.

3. Choose an optional `scope` only when it adds real context.
   - Use a stable subsystem, package, feature area, or component name such as `serial`, `brain`, or `docs`.
   - Skip the scope when the change spans multiple areas or no single label improves clarity.
   - Do not invent broad scopes like `misc` or `updates`.

4. Write the subject line as the smallest accurate summary.
   - Use imperative mood and lowercase after the colon, for example `fix(serial): handle reconnect timeout`.
   - Describe the visible outcome or intent, not the implementation detail.
   - Keep it concise and specific (normally 72 characters or fewer); avoid
     filler like `update stuff` or `fix bug`.

5. Decide whether the commit needs a body.
   - Add a body when the diff is non-trivial, the reason is not obvious from the subject, or there are important constraints, side effects, or follow-up implications.
   - Skip the body for small, self-explanatory changes.
   - In the body, explain what changed and why it was needed; do not restate the diff line-by-line.

6. Decide whether the commit needs a footer.
   - Add footers for issue references, co-authors, or other structured metadata.
   - Prefer issue references such as `Closes #123` or `Refs #123` when the repository uses them.
   - Skip the footer when there is no structured metadata to record.

7. Mark breaking changes explicitly when behavior or interfaces are no longer backward compatible.
   - Use `type(scope)!: subject` or `type!: subject` when the breaking change should be visible in the header.
   - Also add a `BREAKING CHANGE:` footer describing what changed and what callers or operators must do.
   - Treat API removals, incompatible parameter changes, config format changes, and changed operational assumptions as breaking unless proven otherwise.

### Workflow Output Checklist

1. Confirm the subject matches the main outcome of the staged diff.
2. Confirm the chosen type is specific and not a fallback for mixed changes.
3. Confirm the scope is useful or omit it.
4. Add body text only when it improves reviewer understanding.
5. Add footer lines only for structured metadata.
6. Add `!` and `BREAKING CHANGE:` when compatibility is intentionally broken.

## Tips for Best Messages

1. **Be specific**: "fix login button" not "fix bug"
2. **Use imperative mood**: "add" not "added" or "adds"
3. **Include context**: Why this change was needed
4. **Reference issues**: Include issue numbers when they are relevant
5. **Breaking changes**: Mark them in the header and footer
