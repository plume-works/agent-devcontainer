---
type: codebase
description: 'Shell helpers on PATH while the plugin is enabled: the shared result-code and GitHub-issue libraries, the Super-Linter wrappers, and the ruff and shellcheck checks.'
source: .agents/plugins/agentdev/bin
commit: eb60f60450c6009b076bc51993b49a924653eaa4
verified:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:07:17Z
stale_after: 2026-12-02
generated:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:07:17Z
sources:
- id: code
  resource: .agents/plugins/agentdev/bin
  title: the code this map describes, read at commit eb60f60
---

# Catalog bin helpers

Eight scripts. Two are libraries sourced by skill scripts; the rest are commands
a user or skill runs directly.

## Public surface

- `result-codes.sh` — `RESULT_CODES`, `quit_by_code`, `emit_result`, and the
  `EXIT`/`HUP`/`INT`/`TERM` traps every skill script inherits
- `github-issue.sh` — `parse_issue_ref`, `require_gh`, `resolve_current_repo`,
  `gh_output_says_not_found`
- `super-linter-local.sh [--all] [--image] [--log-level]` — one local
  Super-Linter pass with autofixes; `super-linter-env.sh` emits the
  `VALIDATE_*`/`FIX_*` environment; `super-linter-defaults.sh` pins the image
- `python-lint-check.sh` — non-mutating ruff check, resolved through
  `uv run --no-sync` in a uv project
- `shellcheck-fix.sh` — applies `shellcheck -f diff` to the tracked scripts
- `__utils.sh` — sets `root_dir` from `git rev-parse --show-toplevel`

## How it works

Libraries return non-zero and let the caller pick the declared result; a script
calls `quit_by_code` on every terminal path so `RESULT=` is always the last
stdout line, and the `EXIT` trap names an unhandled failure `SCRIPT_FAILURE`.
Signal traps emit `SIGNAL_*`, restore the default action, and re-raise, so a
shell caller still sees `128+N`.

## Depends on

`git`, `gh`, Docker (Super-Linter), `uv`/`ruff`, `shellcheck`.

## Invariants & gotchas

- The target repository is resolved from the working directory, never from
  `BASH_SOURCE`: these scripts run from a plugin cache.
- `1` is never a workflow outcome; script-specific codes start at `3`.
- The Super-Linter image pin here is one of the versions
  `/agentdev:sync-super-linter-tool-versions` keeps aligned with
  `.pre-commit-config.yaml`.

## Key references

Verified anchor points (line numbers as of 2026-09-03):

- `.agents/plugins/agentdev/bin/result-codes.sh:15-22` — the reserved codes
- `.agents/plugins/agentdev/bin/result-codes.sh:43` — `quit_by_code`
- `.agents/plugins/agentdev/bin/result-codes.sh:51` — `report_unhandled_exit`
- `.agents/plugins/agentdev/bin/github-issue.sh:10,29,41,46` — the four helpers
- `.agents/plugins/agentdev/bin/__utils.sh:6` — `root_dir`
- `.agents/plugins/agentdev/bin/super-linter-defaults.sh:6` — image pin
