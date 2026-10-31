---
type: codebase
description: 'Helpers on PATH while the plugin is enabled: the shared Python modules every skill script imports (result contract, common helpers, default branch, GitHub issues), the Super-Linter entry points, the ruff and ShellCheck checks, and the Codex agent installer.'
source: .agents/plugins/agentdev/bin
source_digest: sha256:e89b30528e83d5dc8efe42e079476f64ca0dc212349b31bed2c98a18df7068d0
verified:
  by: claude-code/opus-5.5
  at: 2026-10-31T00:03:28Z
stale_after: 2027-01-29
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T00:03:28Z
sources:
- id: code
  resource: .agents/plugins/agentdev/bin
---

# Catalog bin helpers

Eight Python files, all standard-library only. Four are modules a skill script
imports after putting this directory on `sys.path`; the rest are commands a
user, a workflow, or a skill runs directly. Each importable module also has a
command line.

## Public surface

- `result_codes.py` — the reserved code-to-name table, `install()` (exit hook,
  exception hook, HUP/INT/TERM handlers), `run(main)` (runs a script body and
  exits naming the status it produced), `quit_by_code`, and `emit_result`
- `skill_common.py` — `Stop` (a declared result raised from deep in a script),
  `print_error`, `bash_quote` (bash's `printf %q`), `run_tool` (captured),
  `run_to_stderr` (tool stdout sent to stderr), `run_inherited`,
  `require_git_repo`, `current_branch`, `main_checkout_dir`, `skill_root`, and
  `help_header`
- `git_default_branch.py` — `is_default_branch` (`main` or `master`) and
  `remote_default_branch`, which returns the branch `refs/remotes/<remote>/HEAD`
  names, else the default `gh repo view` reports for the remote's URL, else
  `None`; command line `is-default <branch>` / `remote <remote>`
- `github_issue.py` — `parse_issue_ref` (URL, `OWNER/REPO#N`, `#N`, or `N`),
  `require_gh`, `resolve_current_repo`, `close_issue_with_comment`, and
  `run_close` with `CloseCommand`, the whole close-issue flow both closing
  skills run with their own wording; command line `parse` / `close`
- `super_linter.py` — `SUPER_LINTER_DEFAULT_IMAGE`;
  `env [--autofix] [--enable_all_checks]` prints the `GITHUB_ENV` lines the
  reformat workflow appends; `local [--all] [--image] [--log-level]` runs one
  local pass with every check and available autofix
- `python_lint_check.py [PATH ...]` — non-mutating ruff format check then lint,
  with ruff from `uv run --no-sync`, an in-tree `.venv`, or `PATH`
- `shellcheck_fix.py` — applies `shellcheck -f diff` to every `*.sh` below the
  working directory outside `vendor`, `.venv*`, and `.tmp`
- `install-codex-agents.py [--plugin-root <dir>]` — writes
  `${CODEX_HOME:-~/.codex}/agents/agentdev-<stem>.toml` for each
  `agents/<stem>.agent.md` of the plugin shipping it, then deletes every other
  `agentdev-*.toml` there; `INVALID_AGENT` (3) when an agent lacks a
  description, before anything is written

## How it works

A skill script returns a declared code from `main`, or raises `Stop` from a
helper; `run` prints `RESULT=` as the last stdout line and exits with that code.
The hooks keep the line total: `atexit` and `sys.excepthook` name an unhandled
failure `SCRIPT_FAILURE`, and the signal handlers emit `SIGNAL_*`, restore
`SIG_DFL`, and re-raise, so a shell caller still sees `128+N`. Because
`SystemExit` bypasses `sys.excepthook`, `run` catches it to recover the status a
bare `sys.exit` asked for. The subprocess runners never raise on a non-zero
status, and the two that let a child write flush the script's stdout first.

## Depends on

`git`, `gh`, Docker or Podman (`super_linter.py local`), `uv`/`ruff`,
`shellcheck`. Nothing beyond the standard library, so every file runs from a
plugin cache with no environment of its own.

## Invariants & gotchas

- The target repository is resolved from the working directory, never from this
  directory's location: these files run from a plugin cache.
- `close_issue_with_comment` returns `3` (gh failed), `4` (no such issue), or
  `5` (already closed) — the result codes both closing scripts declare.
- `1` is never a workflow outcome; script-specific codes start at `3`.
- The Super-Linter image pin here is one of the versions
  `/agentdev:sync-super-linter-tool-versions` keeps aligned with
  `.pre-commit-config.yaml`, and the publisher's
  `scripts/validate-super-linter-tool-versions.py` imports it.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `.agents/plugins/agentdev/bin/result_codes.py:23` — the reserved codes
- `.agents/plugins/agentdev/bin/result_codes.py:88` — `run`
- `.agents/plugins/agentdev/bin/result_codes.py:105` — `install`
- `.agents/plugins/agentdev/bin/skill_common.py:19` — `Stop`
- `.agents/plugins/agentdev/bin/skill_common.py:33` — `bash_quote`
- `.agents/plugins/agentdev/bin/skill_common.py:68` — `run_to_stderr`
- `.agents/plugins/agentdev/bin/git_default_branch.py:36` —
  `remote_default_branch`
- `.agents/plugins/agentdev/bin/github_issue.py:96` — `close_issue_with_comment`
- `.agents/plugins/agentdev/bin/github_issue.py:186` — `run_close`
- `.agents/plugins/agentdev/bin/super_linter.py:23` — image pin
- `.agents/plugins/agentdev/bin/super_linter.py:89` — `env_lines`
- `.agents/plugins/agentdev/bin/install-codex-agents.py:73` — `render_agent`,
  the field and `sandbox_mode` mapping
- `.agents/plugins/agentdev/bin/install-codex-agents.py:100` — `main`, write
  then prune by the `agentdev-` prefix
