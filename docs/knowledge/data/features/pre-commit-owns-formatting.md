---
type: feature
stage: implemented
description: The pre-commit git hooks are the single local formatting path, extended to merge commits, with the skill- and agent-level formatting mandates removed and the redundant python-format-lint skill retired into AGENTS.md.
generated:
  by: claude-code/opus-5
  at: 2026-08-31T00:00:00Z
sources:
- resource: .devcontainer/scripts/setup-pre-commit.sh
- resource: .pre-commit-config.yaml
- resource: AGENTS.md
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/skills/git-merge-resolve/SKILL.md
- resource: .agents/plugins/agentdev/skills/local-reformat/SKILL.md
---

# Let pre-commit own formatting

## Purpose

`.pre-commit-config.yaml` wires every linter Super-Linter runs, at revisions
`scripts/validate-super-linter-tool-versions.sh` keeps pinned to the image, and
the hooks fire on `git commit`. A skill that told an agent to format before
committing therefore described work the hooks were about to do anyway — and did
so through the slower, Docker-dependent Super-Linter path presented as
mandatory. This repository supports devcontainer workflows only, so pre-commit
and Super-Linter always run the same tools at the same versions in the same
environment; there is no environment in which pre-commit is the weaker check.

## Behaviour

**The pre-commit hooks are the local formatting path.** They run on every commit
and are the only local step an agent needs. Super-Linter remains the CI gate;
`agentdev:local-reformat` remains available for a manual full local pass but
carries no mandate.

**Merge commits are covered.** `.devcontainer/scripts/setup-pre-commit.sh`
installs the `pre-merge-commit` hook type alongside `pre-commit` and `pre-push`,
so a non-conflicted `git merge` runs the same gate that a normal commit does
rather than committing merged files unformatted.

**The formatting mandates are gone.** `pr-open` no longer requires a
`local-reformat` pass before committing or after branch sync;
`git-merge-resolve` no longer re-runs `local-reformat` after a merge; and the
`principal-engineer` and `tdd-refactor` agents route Python formatting through
the hooks, verifying with `python-lint-check.sh` rather than a formatting skill.

**`local-reformat` presents as triage, not obligation.** Its own internal
"required / must / do not omit" language is softened; it is described as
CI-failure triage plus an optional full local pass.

**`python-format-lint` is retired.** Under hook-driven formatting its autofix
loop was redundant. Its two unique rules — the targeted-`noqa` policy and isort
living in `.ruff.toml` — moved into the `AGENTS.md` Python section, which
`pr-review` already treats as always applying. `python-lint-check.sh` is
unaffected.

## Scope

CI is unchanged: `reformat.yml` still runs Super-Linter, and
`super-linter-env.sh`, `super-linter-local.sh`, and the version-sync script all
stay. Existing devcontainers created before this change need one manual
`pre-commit install --hook-type pre-merge-commit`; the change is not
retroactively automated.

## References

- Plan:
  [Let pre-commit own formatting](../plans/20260831-pre-commit-owns-formatting.md)
- Spec touched: [Template consumption](../spec/template-consumption.md) §5 item
  5
