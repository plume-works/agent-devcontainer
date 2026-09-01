---
name: extract-github-actions-logs
description: 'Extract logs from a GitHub Actions run or job with the GitHub CLI. Use when asked to fetch failing CI logs, inspect a GitHub Actions run, or pull logs from a run or job URL. Keywords: github actions logs, failing ci logs, workflow run logs, job logs, gh run view.'
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/*)
---

# Extract GitHub Actions Logs

Use this skill to pull GitHub Actions logs with `gh`.

## When to Use This Skill

- Fetch logs for a failing GitHub Actions run or job
- Inspect CI from a GitHub Actions URL
- Pull the log for a specific run ID or job ID

## Prerequisites

- `gh` must be installed
- `gh` authentication is required

Use the bundled helper script to parse GitHub Actions URLs:

- [parse-actions-url.sh](./scripts/parse-actions-url.sh)

The last line of its stdout is always `RESULT=<NAME>`; match on that name, not on
a bare number.

Always verify authentication first:

```bash
gh auth status
```

If that command fails or shows no authenticated account, stop immediately and tell the user to authenticate first with:

```bash
gh auth login
```

Do not continue until `gh auth status` succeeds.

## Workflow

1. Verify `gh` authentication with `gh auth status`.
2. If the user provides a GitHub Actions URL, parse it with the helper script.
3. Read the helper's `RESULT` line and handle it with the table below.
4. On `SUCCESS`, identify the repository, run ID, and optional job ID from the helper's shell-safe `REPO=`, `RUN_ID=`, and `JOB_ID=` output.
5. Fetch logs with `gh`.

Use these commands:

```bash
gh run view <run-id> --repo <owner>/<repo>
gh run view <run-id> --repo <owner>/<repo> --log
gh run view <run-id> --repo <owner>/<repo> --job <job-id> --log
```

Use the helper script when the input is a GitHub Actions URL:

```bash
${CLAUDE_SKILL_DIR}/scripts/parse-actions-url.sh --url '<github-actions-url>'
${CLAUDE_SKILL_DIR}/scripts/parse-actions-url.sh --url '<github-actions-url>' --format command --log
```

Handle its result:

| RESULT            | Exit | Meaning                                                                                            | Action                                                                                                                                            |
| ----------------- | ---- | -------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`         | `0`  | The URL was parsed                                                                                 | Continue with the printed `REPO`, `RUN_ID`, and — when present — `JOB_ID`, or with the generated command.                                         |
| `UNSUPPORTED_URL` | `3`  | The input is not a GitHub Actions run or job URL                                                   | Do not retry the same URL. Ask the user for a run or job URL, or locate the run with `gh run list --repo <owner>/<repo>` and use its ID directly. |
| `PREFLIGHT_ERROR` | `2`  | Bad usage: missing or unknown option, bad `--format`, `--grep-failures` without `--format command` | Fix the invocation reported on stderr and retry.                                                                                                  |
| `SCRIPT_FAILURE`  | `1`  | The script broke                                                                                   | **STOP.** Report the blocker verbatim; do not retry or work around it.                                                                            |

If the parsed URL is a run URL (no `JOB_ID`), fetch the whole run log.

If it is a job URL (`JOB_ID` present), fetch the job log.

If the user wants only the failure lines, filter the job log:

```bash
gh run view <run-id> --repo <owner>/<repo> --job <job-id> --log | grep -nE "FAILED|FAILURES|AssertionError|ERROR:|Segmentation fault|test_"
```

Or generate that command from the helper script:

```bash
${CLAUDE_SKILL_DIR}/scripts/parse-actions-url.sh --url '<github-actions-job-url>' --format command --log --grep-failures
```

If the user needs artifacts the run uploaded (test reports, coverage, build logs), download them with `gh run download`.

Discover the exact artifact names for a run first — they are workflow-specific:

```bash
gh api repos/<owner>/<repo>/actions/runs/<run-id>/artifacts --jq '.artifacts[].name'
```

Then download one, or several at once:

```bash
gh run download <run-id> --repo <owner>/<repo> -n <artifact-name> -D ./.tmp/actions-run-<run-id>
gh run download <run-id> --repo <owner>/<repo> -n <artifact-a> -n <artifact-b> -D ./.tmp/actions-run-<run-id>
```

Omit `-n` entirely to fetch every artifact from the run.

## Example

Given this workflow run URL:

`https://github.com/<owner>/<repo>/actions/runs/12345678901`

Run:

```bash
gh auth status
${CLAUDE_SKILL_DIR}/scripts/parse-actions-url.sh --url 'https://github.com/<owner>/<repo>/actions/runs/12345678901' --format command --log
```

Then run the emitted `gh run view ... --log` command to fetch the whole run log.

To inspect and download the artifacts for the same run:

```bash
gh api repos/<owner>/<repo>/actions/runs/12345678901/artifacts --jq '.artifacts[].name'
gh run download 12345678901 --repo <owner>/<repo> -n <artifact-name> -D ./.tmp/actions-run-12345678901
```

List the artifacts and choose the one matching the failing matrix job. Suffixes
such as `-amd64` and `-arm64` are hints, not evidence.

Given this failing CI job URL:

`https://github.com/<owner>/<repo>/actions/runs/12345678901/job/23456789012?pr=42`

Extract:

- repo: `<owner>/<repo>`
- run ID: `12345678901`
- job ID: `23456789012`

Then run:

```bash
gh auth status
gh run view 12345678901 --repo <owner>/<repo> --job 23456789012 --log
```

Or, to focus on the likely failure lines:

```bash
gh run view 12345678901 --repo <owner>/<repo> --job 23456789012 --log | grep -nE "FAILED|FAILURES|AssertionError|ERROR:|Segmentation fault|test_" | tail -n 200
```

The same job URL can be parsed with:

```bash
${CLAUDE_SKILL_DIR}/scripts/parse-actions-url.sh --url 'https://github.com/<owner>/<repo>/actions/runs/12345678901/job/23456789012?pr=42'
```
