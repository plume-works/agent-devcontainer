---
type: codebase
description: 'The command-line contract of the validator: arguments, flags, discovery rules, and exit codes, as consumed by pre-commit, CI, and the image.'
source: py_packages/validate_agent_files/validate_agent_files/cli.py
commit: eb60f60450c6009b076bc51993b49a924653eaa4
verified:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:09:00Z
stale_after: 2026-12-02
generated:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:09:00Z
sources:
- id: code
  resource: py_packages/validate_agent_files/validate_agent_files/cli.py
  title: the code this map describes, read at commit eb60f60
---

# Interface: validate_agent_files CLI

The one entry point of the
[validator package](py_packages/validate_agent_files.md). Three callers depend
on it: the `validate-agent-files` pre-commit hook, the
`validate-agent-files.yml` workflow, and consumers of the image, where it is
installed as a uv tool.

## Invocation

``` text
validate_agent_files [paths...] [--kind all|skills|agents|prompts]
                     [--mode files|plugin] [--require-marketplace ECOSYSTEM...]
                     [--recommend] [--ci] [--no-warnings] [--errors-only]
                     [--format text|json|csv] [-q] [-v] [--json] [--csv]
```

- `paths` default to the current directory. Every path must exist and hold
  something validatable; a missing or empty path is a failure, so a run that
  validated nothing can never pass.
- `--mode plugin` adds plugin packaging discovered through the two marketplace
  manifests; `--require-marketplace claude codex` implies it and makes each
  named ecosystem's manifest mandatory.
- `--recommend` shows warnings; `--no-warnings` and `--errors-only` hide them.
  `--ci` prints only on failure unless `-v`.

## Exit codes

- `0` — every result valid
- `1` — at least one invalid result (`main.py:33`); warnings alone never fail

## Discovery

`SKILL.md`, `*.agent.md`, and `*.prompt.md` under the requested paths, skipping
gitignored entries when inside a work tree. A requested path inside a plugin
always brings that plugin's manifests and bundled Markdown into the run.

## Consumers

- `.pre-commit-config.yaml:81` — the local hook
- `.github/workflows/validate-agent-files.yml:74` —
  `--recommend . --require-marketplace claude codex`
- The image, via [its role](ansible/roles/validate_agent_files.md)
