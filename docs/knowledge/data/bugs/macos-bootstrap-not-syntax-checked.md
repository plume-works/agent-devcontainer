---
type: bug
description: The macOS bootstrap is excluded from shellcheck on the grounds that it is checked with zsh -n, but no hook, workflow, or test runs zsh -n on it.
stage: pending
severity: low
sources:
- resource: .pre-commit-config.yaml
- resource: AGENTS.md
- resource: .agents/plugins/agentdev/bin/macos-bootstrap.zsh
- resource: .github/workflows/validate-agent-files.yml
---

# Bug: Nothing runs `zsh -n` on the macOS bootstrap that shellcheck skips

## Symptom

`.agents/plugins/agentdev/bin/macos-bootstrap.zsh` is excluded from the
`shellcheck` pre-commit hook on the stated grounds that it is checked with
`zsh -n` instead, but no hook, workflow, or test runs `zsh -n` on it. A syntax
error in the bootstrap passes every pre-commit hook and every Linux CI job; only
the macOS job, which executes the script, can catch it.

## Reproduction

1. Introduce a zsh syntax error into
   `.agents/plugins/agentdev/bin/macos-bootstrap.zsh`, such as an unclosed `if`.
2. Run `uv run pre-commit run --all-files`: every hook passes.
3. `git grep -n 'zsh -n' -- ':!docs/knowledge'` finds only the comment in
   `.pre-commit-config.yaml` and the rule in `AGENTS.md`.

## Root cause

`.pre-commit-config.yaml#repos` › `id: shellcheck` excludes the bootstrap with
the comment "the macOS bootstrap is checked with `zsh -n`", and
`AGENTS.md#shell` makes the same claim, but no local hook runs `zsh -n`.
`.github/workflows/validate-agent-files.yml#jobs.macos-bootstrap` runs the
script on a macOS runner, which is a functional check, not the syntax gate the
comment names.
