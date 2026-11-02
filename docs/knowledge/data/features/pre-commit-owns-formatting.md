---
type: feature
stage: implemented
description: The pre-commit git hooks are the single local formatting path, extended to merge commits, with the skill- and agent-level formatting mandates removed and the redundant python-format-lint skill retired into AGENTS.md.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T05:09:26Z
sources:
- resource: .devcontainer/scripts/setup-pre-commit.sh
- resource: .pre-commit-config.yaml
- resource: AGENTS.md
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/skills/git-merge-resolve/SKILL.md
---

# Let pre-commit own formatting

## Purpose

`.pre-commit-config.yaml` wires every linter and formatter the repository uses,
and the hooks fire on `git commit`. A skill that tells an agent to format before
committing describes work the hooks are about to do anyway. CI runs the same
hooks with the same tools (see [pre-commit is the CI
gate](pre-commit-ci-gate.md)), so there is no environment in which the local
hooks are the weaker check.

## Behaviour

**The pre-commit hooks are the local formatting path.** They run on every commit
and are the only local step an agent needs; the CI gate is [pre-commit is the CI
gate](pre-commit-ci-gate.md).

**Merge commits are covered.** `.devcontainer/scripts/setup-pre-commit.sh`
installs the `pre-merge-commit` hook type alongside `pre-commit` and `pre-push`,
so a non-conflicted `git merge` runs the same gate that a normal commit does
rather than committing merged files unformatted.

**No skill or agent mandates formatting.** `pr-open` and `git-merge-resolve`
leave formatting to the hooks, and the `principal-engineer` and `tdd-refactor`
agents route Python formatting through them, verifying with
`python_lint_check.py` rather than a formatting skill.

**`python-format-lint` is retired.** Under hook-driven formatting its autofix
loop was redundant. Its two unique rules — the targeted-`noqa` policy and isort
living in `.ruff.toml` — moved into the `AGENTS.md` Python section, which
`pr-review` already treats as always applying. `python_lint_check.py` is
unaffected.

## Scope

The CI gate belongs to [pre-commit is the CI gate](pre-commit-ci-gate.md).
Existing devcontainers created before this change need one manual
`pre-commit install --hook-type pre-merge-commit`; the change is not
retroactively automated.

## Edge cases

- **A conflicted merge.** `pre-merge-commit` runs only for a merge that commits
  on its own; a conflicted merge is concluded with `git commit`, which runs the
  `pre-commit` hook.
- **A hook rewrites a staged file.** The commit stops; the rewritten file is
  re-staged and the commit retried.
- **The hooks are bypassed.** A commit made with `--no-verify` is not checked
  locally, and the `pre-commit` job in CI still is.
- **A devcontainer created before the change.** It lacks the `pre-merge-commit`
  hook until `pre-commit install --hook-type pre-merge-commit` is run once.

## Open questions

None — every design question this feature raised is settled.

## References

- Plan: [Let pre-commit own
  formatting](../plans/20260831-pre-commit-owns-formatting.md)
- Spec touched: [Template consumption](../spec/template-consumption.md) §5 item
  5
