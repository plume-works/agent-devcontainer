---
type: bug
description: When git-new-branch cannot find the default branch, it prints a git remote set-head command with the remote name not quoted by bash_quote.
stage: pending
severity: low
sources:
- resource: .agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.py
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
- resource: docs/spec-audit/requirements.jsonl
---

# Bug: a git-new-branch hint puts the remote name into a command line without quotes

## Symptom

Each command line that a catalog script gives to a shell must quote its values
with `bash_quote`. `git-new-branch.py` prints
`run: git remote set-head <remote> --auto` with the remote name as it is. A
remote name with a space or a shell metacharacter gives a command that does not
work when you copy it, or that does a different thing.

## Reproduction

1. Add a remote whose name holds a shell metacharacter, with no `HEAD` set.
2. Run `git-new-branch.py` with that remote and no `--base`, so that the base
   cannot be found.
3. The hint shows the remote name without quotes.

## Root cause

`.agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.py::resolve_base`
writes `f'Pass --base <branch>, or run: git remote set-head {remote} --auto'`
without `bash_quote`.
