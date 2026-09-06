---
type: codebase
description: 'Helpers on PATH while the plugin is enabled: the shared result-code libraries for bash and Python, the GitHub-issue library, the Super-Linter wrappers, and the ruff and shellcheck checks.'
source: .agents/plugins/agentdev/bin
source_digest: sha256:17f474a42b38d1c8f97ed8bd396281058c10e4e867d7e4d42e74179c09d22963
verified:
  by: claude-code/opus-5
  at: 2026-09-06T00:00:00Z
stale_after: 2026-12-05
generated:
  by: claude-code/opus-5
  at: 2026-09-06T00:00:00Z
sources:
- id: code
  resource: .agents/plugins/agentdev/bin
---

# Catalog bin helpers

Nine files. Three are libraries a skill script pulls in — two of them the same
result contract in bash and in Python; the rest are commands a user or skill
runs directly.

## Public surface

- `result-codes.sh` — `RESULT_CODES`, `quit_by_code`, `emit_result`, and the
  `EXIT`/`HUP`/`INT`/`TERM` traps every bash skill script inherits
- `result_codes.py` — the same code-to-name table for Python skill scripts, plus
  `install()` (exit hook, exception hook, signal handlers), `run(main)` (the
  entry point that runs a script body and names the status it produced),
  `quit_by_code`, and `emit_result`
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
shell caller still sees `128+N`. The Python library reproduces each of those
pieces with the interpreter's own hooks: `atexit` for the `EXIT` trap,
`sys.excepthook` for an escaping exception, and `signal.signal` handlers that
re-raise after restoring `SIG_DFL`. Because `SystemExit` bypasses
`sys.excepthook`, `run` catches it to recover the status a bare `sys.exit` asked
for, which is what `$?` gives the bash helper for free.

## Depends on

`git`, `gh`, Docker (Super-Linter), `uv`/`ruff`, `shellcheck`. `result_codes.py`
imports only the standard library, so it resolves from a plugin cache with no
environment of its own.

## Invariants & gotchas

- The target repository is resolved from the working directory, never from
  `BASH_SOURCE`: these scripts run from a plugin cache.
- `1` is never a workflow outcome; script-specific codes start at `3`, and both
  result libraries carry the same reserved names for `0`, `1`, `2`, `129`,
  `130`, and `143`.
- The Super-Linter image pin here is one of the versions
  `/agentdev:sync-super-linter-tool-versions` keeps aligned with
  `.pre-commit-config.yaml`.

## Key references

Verified anchor points (line numbers as of 2026-09-06):

- `.agents/plugins/agentdev/bin/result-codes.sh:15-22` — the reserved codes
- `.agents/plugins/agentdev/bin/result-codes.sh:43` — `quit_by_code`
- `.agents/plugins/agentdev/bin/result-codes.sh:51` — `report_unhandled_exit`
- `.agents/plugins/agentdev/bin/result_codes.py:29-36` — the same reserved codes
- `.agents/plugins/agentdev/bin/result_codes.py:94` — `run`
- `.agents/plugins/agentdev/bin/result_codes.py:111` — `install`
- `.agents/plugins/agentdev/bin/github-issue.sh:10,29,41,46` — the four helpers
- `.agents/plugins/agentdev/bin/__utils.sh:6` — `root_dir`
- `.agents/plugins/agentdev/bin/super-linter-defaults.sh:6` — image pin
