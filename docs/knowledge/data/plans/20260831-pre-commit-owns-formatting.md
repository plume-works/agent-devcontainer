---
type: plan
created: 2026-08-31
description: Remove the skill-level formatting mandates so the pre-commit git hooks are the only local formatting path, and extend those hooks to merge commits.
generated:
  by: claude-code/opus-5
  at: 2026-08-31T00:00:00Z
---

# Let pre-commit own formatting

## Context

`.pre-commit-config.yaml` now wires every linter that Super-Linter runs. Each
`VALIDATE_*` flag emitted by `.agents/plugins/agentdev/bin/super-linter-env.sh`
has a matching hook, at a revision that
`scripts/validate-super-linter-tool-versions.sh` checks against the pinned image
on every CI run:

| Super-Linter flag                   | pre-commit hook       |
| ----------------------------------- | --------------------- |
| `PYTHON_RUFF`, `PYTHON_RUFF_FORMAT` | `ruff`, `ruff-format` |
| `MARKDOWN/YAML/JSON/JSONC_PRETTIER` | `prettier`            |
| `CLANG_FORMAT`                      | `clang-format`        |
| `ANSIBLE`                           | `ansible-lint`        |
| `BASH`                              | `shellcheck`          |
| `DOCKERFILE_HADOLINT`               | `hadolint-docker`     |
| `GITHUB_ACTIONS`                    | `actionlint`          |
| `GITHUB_ACTIONS_ZIZMOR`             | `zizmor`              |
| `GITLEAKS`                          | `gitleaks`            |

pre-commit is a superset: it also runs `validate-agent-files`,
`plan-checkboxes`, and the whitespace fixers, which Super-Linter never ran.

The hooks are installed by `.devcontainer/scripts/setup-pre-commit.sh` and fire
on `git commit`, so a skill that instructs an agent to format before committing
describes work that is about to happen anyway. Those instructions are the
slower, Docker-dependent path presented as the mandatory one.

This repository supports devcontainer workflows only (`data/product.md`
`## Platforms`: "no non-container/bare-metal install path"), so pre-commit and
Super-Linter always run in the same environment with the same tool versions.
There is no environment in which pre-commit is the weaker check.

Two gaps remain. `setup-pre-commit.sh` installs the `pre-commit` and `pre-push`
hook types only, so a non-conflicted `git merge` creates its commit with no
hooks at all. And `spec/template-consumption.md` §5.5 tells consuming projects
to swap the `zizmor` hook for a portable one so `pre-commit run --all-files`
works on a bare host — advice for a platform this product does not support.

## Approach

Delete the formatting mandates from the skills and agents that carry them, and
add `--hook-type pre-merge-commit` to the hook installation so merge commits are
covered by the same gate.

`local-reformat` is kept for manual use — Super-Linter still runs in CI, and its
log-triage reference is the way to read a failing `reformat.yml` job — but its
own internal obligation language is softened, because the callers that made it
mandatory are being removed.

`python-format-lint` is deleted. Under hook-driven formatting its autofix loop
is redundant, and the rest is policy that belongs with the other Python
conventions. Its two pieces of unique knowledge — the `noqa` rule and the
isort-in-`.ruff.toml` rule — move into the `AGENTS.md` Python section, which
`pr-review` already treats as always applying. The `python-lint-check.sh` script
is unaffected: `tdd-refactor` and `principal-engineer` invoke it directly.

Rejected: replacing Super-Linter in CI with `pre-commit run --all-files`. That
would make the config the single source of truth and retire both the sync script
and `local-reformat`, but `reformat.yml` carries autofix-patch machinery — patch
artifact, three-way apply, recursion guard — that works and would have to be
rebuilt. This plan does not foreclose that change.

Also rejected: adding hook-failure guidance to `git-commit`. A commit that a
formatter modifies exits non-zero, leaving the file fixed on disk and staged as
`AM`, needing `git add` before a retry. Agents already handle this correctly
without extra prose.

## Implementation Steps

### Task 1: Extend the hooks to merge commits

**Files:** Modify: `.devcontainer/scripts/setup-pre-commit.sh`

- [x] Add `--hook-type pre-merge-commit` to the `pre-commit install` invocation
  at line 20, keeping the existing `pre-commit` and `pre-push` types and the
  surrounding failure-logging behavior.
  - **Evidence:** `bash -n .devcontainer/scripts/setup-pre-commit.sh` passed and
    the installation command retains both existing hook types and failure
    logging.
- [ ] Update the comment above the call so it names all three hook types rather
  than "both staged-file and pre-push checks".

### Task 2: Remove the formatting mandate from pr-open

**Files:** Modify: `.agents/plugins/agentdev/skills/pr-open/SKILL.md`

- [ ] Delete the responsibility bullet at line 52 ("delegating mandatory
  formatting and validation to the `local-reformat` skill").
- [ ] Delete the `### 3. Mandatory Local Reformat` section (lines 121-130) in
  full, renumbering the sections that follow.
- [ ] Rewrite the opening of `### 4. Commit Any Uncommitted PR Scope` so it no
  longer depends on a completed reformat: it currently begins "After
  `local-reformat` completes successfully, inspect `git status`."
- [ ] Delete the `### 6. Post-sync Formatter and Commit Check` section (lines
  155-160), whose premise is that a formatter must be re-run after
  `update-branch`.

### Task 3: Remove the post-merge reformat from git-merge-resolve

**Files:** Modify: `.agents/plugins/agentdev/skills/git-merge-resolve/SKILL.md`

- [ ] Delete step 2 of `## Workflow 4` (lines 169-171), which invokes
  `local-reformat`, and renumber the remaining steps. The merge commit created
  by step 1 now runs the hooks itself via `pre-merge-commit`.
- [ ] Delete the completion criterion at line 206 ("The mandatory local reformat
  workflow completed successfully after a merge").
- [ ] Check the `SUCCESS` row of the exit-code table at line 88, which sends the
  reader to "Workflow 4 for the required reformat and validation", and restate
  it in terms of the validation that remains.

### Task 4: Remove the formatting routes from the agents

**Files:** Modify:
`.agents/plugins/agentdev/agents/principal-engineer.agent.md`,
`.agents/plugins/agentdev/agents/tdd-refactor.agent.md`

- [ ] Delete the `**Repo-wide formatting**` bullet at
  `principal-engineer.agent.md:74`.
- [ ] Rewrite the `**Python style**` bullet at
  `principal-engineer.agent.md:72-73` so it no longer links the deleted skill,
  keeping the `python-lint-check.sh` reference.
- [ ] Remove the `python-format-lint` link from the `**Python**` bullet at
  `tdd-refactor.agent.md:40-43`, keeping the `python-lint-check.sh` verification
  and the existing pre-commit sentence. The checklist item at line 61 is
  unaffected.

### Task 5: Delete the python-format-lint skill and move its policy

**Files:** Delete: `.agents/plugins/agentdev/skills/python-format-lint/`;
Modify: `AGENTS.md`

- [ ] Delete the `.agents/plugins/agentdev/skills/python-format-lint/`
  directory.

- [ ] Replace the ruff bullet at `AGENTS.md:75` so it drops the
  `/agentdev:python-format-lint` pointer and absorbs the skill's two unique
  rules. Use this text verbatim:

  ````
  ```markdown
  - Formatting and autofixes are applied by **ruff**, via the pre-commit hooks that run on every commit; Super-Linter runs the same tools in CI. Verify with `python-lint-check.sh` for a fast, Docker-free check. Never judge style with stock `flake8` or `black`: their defaults (79-char limit, double quotes, different isort grouping) produce false positives that do not match this repo and do not fail CI. Import sorting needs no separate pass — `I` is in `.ruff.toml`'s `select` list, so the ruff hook sorts imports too. Use a targeted `# noqa: <rule>` only for a formatter-required incompatibility (for example `E203` on a slice); never disable a rule for a whole file or package, and fix import-group disagreements in `.ruff.toml`'s `lint.isort` rather than with `noqa`
  ```
  ````

### Task 6: Update the remaining references to the deleted skill

**Files:** Modify: `.agents/plugins/agentdev/README.md`,
`.agents/plugins/agentdev/skills/pr-review/SKILL.md`,
`.agents/plugins/agentdev/skills/semantic-refactor-audit/SKILL.md`,
`.agents/plugins/agentdev/skills/local-reformat/SKILL.md`

- [ ] Delete the `/agentdev:python-format-lint` row from the skill table at
  `README.md:95`.
- [ ] In `pr-review/SKILL.md:80`, drop the clause adding the
  `/agentdev:python-format-lint` skill for Python diffs. The same sentence
  already states that the Coding Conventions section of `AGENTS.md` always
  applies, which is where Task 5 puts the policy.
- [ ] In `semantic-refactor-audit/SKILL.md:3`, remove
  `/agentdev:python-format-lint` from the `description` frontmatter, leaving
  `/agentdev:local-reformat` as the routing target for formatting and lint
  fixes. This field drives skill discovery, so keep the sentence well-formed
  rather than leaving a dangling conjunction.
- [ ] Delete the closing cross-reference at `local-reformat/SKILL.md:175-176`
  that points at the deleted skill.

### Task 7: Soften local-reformat's internal obligation language

**Files:** Modify: `.agents/plugins/agentdev/skills/local-reformat/SKILL.md`

- [ ] Rewrite the `## Codex Managed-Sandbox Execution` section (lines 39-48) so
  the escalated permission is described as what the skill needs when it is
  invoked, not as a required step. Drop "approved, required local validation
  action", "Do not omit this step or substitute a partial lint command when
  opening a pull request", and "must run with the same elevated sandbox
  permission".
- [ ] Reword the `## When to Use This Skill` list so the first entry no longer
  reads as a pre-commit/pre-PR obligation, and the skill presents as CI-failure
  triage plus an optional full local pass.

### Task 8: Drop the bare-host zizmor advice from the consumption spec

**Files:** Modify: `docs/knowledge/data/spec/template-consumption.md`

- [ ] Rewrite item 5 of `## 5. Adapt pre-commit and lint configuration` (lines
  160-164) so it states that the `zizmor` hook is `language: system` and expects
  `zizmor` on `PATH`, which the development image provides — matching the
  `validate-agent-files` hook directly above it. Remove the
  `zizmorcore/zizmor-pre-commit` substitution, which exists to make
  `pre-commit run --all-files` work on a bare host and would add a second
  version pin outside the sync script's coverage.

### Task 9: Correct the lint description in product.md

**Files:** Modify: `docs/knowledge/data/product.md`

- [ ] Update the `**Lint/format**` bullet in `## Stack`, which currently reads
  "orchestrated through Super-Linter locally (`agentdev:local-reformat`) and in
  CI …; pre-commit hooks wire the same tools in locally". State that the
  pre-commit hooks are the local path and Super-Linter is the CI gate, with
  `local-reformat` available for manual runs.
- [ ] Add a `## Changelog` entry dated 2026-08-31 recording the change.

## Spec changes

[Template consumption](../spec/template-consumption.md) — §5 item 5 SHALL direct
a consuming project to keep the `zizmor` pre-commit hook as `language: system`,
resolved from the development image's `PATH`, rather than substituting the
portable `zizmorcore/zizmor-pre-commit` repository. No requirement or scenario
changes: §5 is procedural adoption guidance, and the removed sentence describes
a bare-host workflow this product does not support (`data/product.md`
`## Platforms`).

The skill, agent, and hook changes are behavioral for agents but are not
described by any `data/spec/` document; `template-consumption.md` is the only
spec this plan touches.

## Verification

- `pre-commit run --all-files` passes.
- `uv run pytest` passes — `validate_agent_files` runs over the catalog, so a
  malformed frontmatter edit in Task 6 surfaces here.
- `pre-commit install --install-hooks --hook-type pre-commit --hook-type pre-push --hook-type pre-merge-commit`
  succeeds, and `.git/hooks/pre-merge-commit` exists afterward.
- A non-conflicted merge into a scratch branch, containing a deliberately
  misformatted tracked file, is reformatted by the hooks rather than committed
  as-is. Delete the scratch branch afterward.
- `grep -rn "python-format-lint" --include="*.md" --include="*.json" .` returns
  no hits outside `docs/knowledge/data/plans/` and `docs/knowledge/data/log.md`,
  where historical plan records legitimately name it.
- `grep -rn "local-reformat" .agents/plugins/agentdev/skills/pr-open/SKILL.md .agents/plugins/agentdev/skills/git-merge-resolve/SKILL.md`
  returns no hits.
- `iwe normalize` and `iwe schema validate` pass.

## Out of scope

- Replacing the Super-Linter action in `.github/workflows/reformat.yml` with a
  `pre-commit run --all-files` job. Evaluated in `## Approach` and deliberately
  deferred; this plan leaves CI unchanged.
- Deleting `local-reformat`, `super-linter-local.sh`, `super-linter-env.sh`, or
  `scripts/validate-super-linter-tool-versions.sh`. Super-Linter remains the CI
  formatter, so all four stay.
- Deleting `python-lint-check.sh` or its `.claude/settings.json:36` permission.
  Only the skill that documented it is removed.
- Adding hook-failure guidance to `git-commit`. Considered and rejected in
  `## Approach`.
- Re-installing hooks in existing devcontainers. Task 1 changes the setup
  script, so containers created before it runs need one manual
  `pre-commit install --hook-type pre-merge-commit`; this plan does not automate
  that migration.

## Key references

Verified anchor points (line numbers as of 2026-08-31):

- `.devcontainer/scripts/setup-pre-commit.sh:18-20` — the comment and the
  `pre-commit install --install-hooks` call listing hook types
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:52` — the mandatory
  formatting responsibility bullet
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:121-130` —
  `### 3. Mandatory Local Reformat`
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:132-134` — the `### 4.`
  opening that depends on it
- `.agents/plugins/agentdev/skills/pr-open/SKILL.md:155-160` —
  `### 6. Post-sync Formatter and Commit Check`
- `.agents/plugins/agentdev/skills/git-merge-resolve/SKILL.md:88` — the
  `SUCCESS` exit-code row pointing at "the required reformat"
- `.agents/plugins/agentdev/skills/git-merge-resolve/SKILL.md:169-171` —
  Workflow 4 step 2, the `local-reformat` invocation
- `.agents/plugins/agentdev/skills/git-merge-resolve/SKILL.md:206` — the
  reformat completion criterion
- `.agents/plugins/agentdev/agents/principal-engineer.agent.md:72-74` — the
  Python style and repo-wide formatting bullets
- `.agents/plugins/agentdev/agents/tdd-refactor.agent.md:40-43` — the Python
  format/lint gate bullet
- `AGENTS.md:75` — the ruff formatting bullet in `### Python`
- `.agents/plugins/agentdev/README.md:95` — the `python-format-lint` skill-table
  row
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md:80` — the
  convention-source sentence naming the skill
- `.agents/plugins/agentdev/skills/semantic-refactor-audit/SKILL.md:3` — the
  `description` frontmatter naming the skill
- `.agents/plugins/agentdev/skills/local-reformat/SKILL.md:39-48` —
  `## Codex Managed-Sandbox Execution`
- `.agents/plugins/agentdev/skills/local-reformat/SKILL.md:175-176` — the
  closing cross-reference to `python-format-lint`
- `docs/knowledge/data/spec/template-consumption.md:160-164` — §5 item 5, the
  bare-host zizmor substitution
- `.agents/plugins/agentdev/bin/super-linter-env.sh:47-66` — the `VALIDATE_*`
  flags the pre-commit hooks mirror
- `scripts/validate-super-linter-tool-versions.sh:158-166` — the per-tool
  version comparison that keeps the two runners equal
