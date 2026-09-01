---
name: local-reformat
description: 'Run every formatter and validation from the reformat GitHub Actions workflow locally through Super-Linter. Use when applying repository-wide format fixes, reproducing reformat.yml, or running the Super-Linter ruff, Ansible, clang-format, and Prettier passes. Keywords: reformat, formatter, ruff, ansible-lint, Ansible, Super-Linter, clang-format, prettier.'
---

# Run the Reformat Workflow Locally

Run the local entry point that mirrors the formatter job in the repository's
`.github/workflows/reformat.yml`. Super-Linter owns every formatter — ruff for
Python, plus Ansible, clang-format, and Prettier — so one command reproduces the
whole CI pass. It modifies files; inspect the resulting diff and keep only
intended changes.

## When to Use This Skill

- Investigating a Super-Linter failure locally and reproducing the formatter
  portions of the `Reformat code` GitHub Actions job
- Applying a full local formatting pass across Python, Ansible, Markdown, YAML,
  JSON, JSONC, and GitHub Actions files at once, when you want more than the
  pre-commit hooks that format staged files on every commit

## Prerequisites

- Run commands from the repository root.
- Sync the repository virtual environment before the Python formatter if it is
  missing or stale:

  ```bash
  uv sync --frozen --all-groups --all-extras
  ```

- Install and start Docker or Podman before running Super-Linter. The local
  wrapper uses the image configured in
  [super-linter-defaults.sh](../../bin/super-linter-defaults.sh) unless
  overridden.
- The shared clang-format configuration is `.clang-format` at the repository
  root.

## Codex Managed-Sandbox Execution

The Super-Linter container needs Docker daemon access and the repository mount,
so when this skill runs under Codex, invoke `super-linter-local.sh` with
`sandbox_permissions: "require_escalated"`. The local wrapper's Ansible,
clang-format, and Prettier autofixes run under the same escalated permission.

## Full Workflow

1. Run Super-Linter using the pinned CI image and configuration. This is the
   only formatting command — it includes the ruff format/autofix pass that CI
   runs:

   ```bash
   super-linter-local.sh
   ```

   The wrapper enables every local check and available autofix in one pass.
   CI intentionally separates its autofix and check jobs so it can publish a
   formatting patch before validating the resulting commit; that split is not
   needed for local feedback.

2. Inspect and validate the results:

   ```bash
   git diff --check
   git status --short -- . ':(exclude).tmp'
   git diff -- . ':(exclude).tmp'
   ```

   Triage a Super-Linter failure using the current-run output described in
   [Super-Linter Results](#super-linter-results). Fix any remaining findings,
   then rerun its local wrapper until the check pass exits successfully.

## Super-Linter Results

The wrapper sets `SUPER_LINTER_OUTPUT_DIRECTORY_NAME=log` and saves only the
most recent run. Inspect its output before rerunning the wrapper: a new run
replaces the prior summary and detailed results.

Begin with `log/super-linter-summary.md`.
Its validation-result table identifies the failing language/linters. Do not
treat the summary's embedded diagnostic text as the only source of truth;
use the corresponding language output below for the complete, structured
result.

For each failing `<LANGUAGE>`, inspect these paths under `log/super-linter/`:

| Path                                                 | Purpose                                                                                                                      |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `super-linter-parallel-command-exit-code-<LANGUAGE>` | Final linter command exit code; a nonzero value is a failure.                                                                |
| `super-linter-parallel-stdout-<LANGUAGE>`            | Linter standard output, when present.                                                                                        |
| `super-linter-parallel-stderr-<LANGUAGE>`            | Linter standard error, when present.                                                                                         |
| `super-linter-worker-results-<LANGUAGE>.json`        | JSON Lines job records for the underlying linter commands, including `Command`, `Exitval`, `Signal`, `Stdout`, and `Stderr`. |
| `super-linter-file-arrays/file-array-<LANGUAGE>`     | Repository files selected for that linter, useful for establishing scope.                                                    |

`super-linter-results.json` is also JSON Lines. It records each top-level
`LintCodebase` invocation and is useful for investigating wrapper-level
behavior, but its `Exitval` can be zero even when an underlying linter failed.
Use the per-language exit-code file and worker result to determine the actual
linter outcome. `super-linter-parallel-results-build-file-list.json` records
file discovery and categorization when the expected linter file array is
missing or surprising.

For example, replace `ANSIBLE` with every failed table entry and inspect the
small text outputs first:

```bash
language=ANSIBLE
cat "log/super-linter/super-linter-parallel-command-exit-code-${language}"
sed -n '1,240p' "log/super-linter/super-linter-parallel-stdout-${language}"
sed -n '1,240p' "log/super-linter/super-linter-parallel-stderr-${language}"
sed -n '1,240p' "log/super-linter/super-linter-file-arrays/file-array-${language}"
```

Use `jq -s` for the JSON Lines files. This reports only failed worker commands
without losing multi-line diagnostics:

```bash
language=ANSIBLE
jq -s \
  '.[] | select(.Exitval != 0 or .Signal != 0) |
   {command: .Command, exit_code: .Exitval, signal: .Signal,
    stdout: .Stdout, stderr: .Stderr}' \
  "log/super-linter/super-linter-worker-results-${language}.json"
```

When the summary reports a failure but no worker file exists, inspect the
top-level records for that linter and the discovery result:

```bash
language=ANSIBLE
jq -s --arg language "$language" \
  '.[] | select(.V[]? == $language) |
   {command: .Command, exit_code: .Exitval, signal: .Signal,
    stdout: .Stdout, stderr: .Stderr}' \
  log/super-linter/super-linter-results.json
jq . log/super-linter/super-linter-parallel-results-build-file-list.json
```

Classify the finding before editing: correct repository source diagnostics;
fix configuration or missing tool/collection diagnostics in the matching
workspace configuration; and report container or unavailable dependency
failures with the exact command output rather than suppressing the check.

## Scope and Options

By default Super-Linter checks the changed files, matching the workflow's
default `validate_all_codebase: false` input. Use `--all` when CI is invoked
with full-repository validation:

```bash
super-linter-local.sh --all
```

Use these troubleshooting options only when necessary:

```bash
super-linter-local.sh --log-level DEBUG
super-linter-local.sh --image ghcr.io/super-linter/super-linter:v8.5.0
```

Do not substitute a newer image merely to make a local result pass: keep the
pinned CI image unless the workflow itself is intentionally being updated.

## Related Entry Points

| Entry point                                              | CI-equivalent responsibility                                                                |
| -------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| [super-linter-local.sh](../../bin/super-linter-local.sh) | Run one local pass with all checks enabled and available autofixes applied.                 |
| [super-linter-env.sh](../../bin/super-linter-env.sh)     | Generate the shared Ansible, clang-format, Prettier, and validation settings for each pass. |
