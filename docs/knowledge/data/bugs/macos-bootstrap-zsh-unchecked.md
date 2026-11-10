---
type: bug
stage: pending
severity: low
description: Nothing runs `zsh -n` on bin/macos-bootstrap.zsh, although the pre-commit config and AGENTS.md say it is checked that way in place of shellcheck.
sources:
- resource: .pre-commit-config.yaml
- resource: AGENTS.md
- resource: .agents/plugins/agentdev/bin/macos-bootstrap.zsh
---

# Bug: the macOS bootstrap's zsh syntax is never checked

## Symptom

`bin/macos-bootstrap.zsh` is excluded from the `shellcheck` hook, and both the
hook's comment and `AGENTS.md#shell` say the script is checked with `zsh -n`
instead. No pre-commit hook, workflow, or test runs `zsh -n`, so a syntax error
reaches a user's Mac unless the `macos-bootstrap` job in
`validate-agent-files.yml` happens to run the broken branch.

## Reproduction

1. Add an unbalanced `if` to `bin/macos-bootstrap.zsh`.
2. Run `uv run pre-commit run --all-files`.
3. Every hook passes.

## Root cause

The `shellcheck` hook's `exclude` was added with a comment naming `zsh -n` as
the replacement check, but no hook running it was added.

## Potential solution

Add a local `language: system` pre-commit hook with `entry: zsh -n` matching
`^\.agents/plugins/agentdev/bin/macos-bootstrap\.zsh$`.
