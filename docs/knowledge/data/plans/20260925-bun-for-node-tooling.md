---
created: 2026-09-25
type: plan
description: Run the npm-backed pre-commit hooks and the Claude Code upgrade hint through bun, move the Renovate pin to the bunx hook entry, and record bun/bunx as the only JavaScript runner in AGENTS.md.
generated:
  by: claude-code/opus-5
  at: 2026-09-26T08:04:24Z
sources:
- resource: .pre-commit-config.yaml
- resource: .github/renovate.json
- resource: .github/workflows/validate-renovate-config.yml
- resource: Makefile
- resource: https://github.com/renovatebot/renovate/blob/main/lib/modules/manager/pre-commit/extract.ts
---

# Run Node tooling through bun instead of npm

## Context

`AGENTS.md` makes `bun` the JavaScript toolchain. The Ansible roles already
follow it: `agentic_tools` and `nodejs` install every global package with
`bun add --global --exact` into `BUN_INSTALL=/usr/local`. Once
[Self-hosted Renovate in the agent-desktop image](20260925-self-hosted-renovate.md)
has shipped, both Renovate workflows already run `bunx` in the agent-desktop
image. Two places still go through npm:

- The `mirrors-prettier` and `renovatebot/pre-commit-hooks` pre-commit hooks use
  pre-commit's `language: node`, which builds a nodeenv and runs `npm install`
  for each hook environment.
- The `validate` target in `Makefile` tells users to upgrade Claude Code with
  `npm install -g`, which is not how the image installs it.

`AGENTS.md` says which toolchain to use but does not rule out the npm-family
commands by name.

Related:
[Renovate config validation](../architecture/renovate-config-validation.md),
[Formatter ownership](../architecture/formatter-ownership.md).

## Approach

Replace both Node-based pre-commit hooks with `language: system` hooks in the
existing `repo: local` block. Each hook runs its tool through `bunx`, and the
package version is pinned in `entry`. The Prettier version still follows the
Super-Linter image: `scripts/validate-super-linter-tool-versions.sh` reads it
with `prettier@v?([0-9.]+)`, and the new entry still matches that pattern.

Renovate's `pre-commit` manager reads a remote repo's `rev` and the
`additional_dependencies` of `node`, `python`, and `golang` hooks; it never
parses a `language: system` hook's `entry`. The Renovate pin therefore moves to
a `custom.regex` manager over `.pre-commit-config.yaml`, with automerge, and the
rules that only existed for the `mirrors-prettier` hook are removed. After the
self-hosted Renovate plan, `renovate.yml` and `validate-renovate-config.yml`
read that pin from the hook's `rev`; this plan points them at the `bunx` entry.

Rejected: keeping `language: node` and pointing pre-commit's nodeenv at bun.
pre-commit has no bun backend, so the hook environments would still be built by
npm.

The standing rule is recorded where agents read it: `AGENTS.md` Best Practice 1
names `bun`/`bunx` as the only JavaScript runners and rules out `npm`, `npx`,
`yarn`, and `pnpm`, with the `product.md` authoring-rules mirror kept in step.

## Implementation Steps

### Task 1: Local bunx hooks for Prettier and the Renovate validator

**Files:** Modify: `.pre-commit-config.yaml`

- [ ] Delete the `https://github.com/pre-commit/mirrors-prettier` repo block and
  the `https://github.com/renovatebot/pre-commit-hooks` repo block.
- [ ] Put the two hooks at the head of the existing `repo: local` block, above
  `zizmor`, exactly as follows:

``` yaml
  - repo: local
    hooks:
      # language: system + bunx: pre-commit's language: node installs hook envs with npm.
      # Prettier's file set matches Super-Linter's; .prettierignore still applies.
      - id: prettier
        name: prettier
        entry: bunx prettier@3.8.1 --write --ignore-unknown
        language: system
        files: '\.(md|markdown|ya?ml|json|jsonc)$'

      # Both flags, and why this pin is also the bot's and the workflow's
      # Renovate version: see architecture/renovate-config-validation.
      - id: renovate-config-validator
        name: renovate-config-validator
        entry: bunx --package renovate@44.106.0 renovate-config-validator --no-global --strict
        language: system
        files: '^\.github/renovate\.json$'

      - id: zizmor
```

### Task 2: Renovate tracks the bunx pin

**Files:** Modify: `.github/renovate.json`

- [ ] Remove `"pre-commit/mirrors-prettier",` from the Super-Linter
  `matchPackageNames` list.
- [ ] Remove the package rule whose description begins "Prettier's
  additional_dependencies pin in the mirrors-prettier hook".
- [ ] Add this custom manager to `customManagers`, before the "Commit pins in
  the Ansible roles' defaults" manager:

``` json
    {
      "description": "npm packages the local pre-commit hooks run through `bunx --package <name>@<version>`. Prettier is excluded: its version follows the Super-Linter image (see the rule above).",
      "customType": "regex",
      "managerFilePatterns": ["/^\\.pre-commit-config\\.yaml$/"],
      "matchStrings": [
        "bunx --package (?<depName>renovate)@(?<currentValue>[0-9][^\\s]*)"
      ],
      "datasourceTemplate": "npm"
    },
```

- [ ] Add a package rule that automerges the `renovate` dependency this manager
  extracts: a bump edits `.pre-commit-config.yaml`, which runs the required
  validation check at the new version.

### Task 3: Renovate workflows read the bunx pin

**Files:** Modify: `.github/workflows/renovate.yml`,
`.github/workflows/validate-renovate-config.yml`

- [ ] Both workflows read the Renovate version from the
  `bunx --package renovate@<version>` entry of the local
  `renovate-config-validator` hook instead of the removed hook's `rev`.

### Task 4: bun upgrade hint in the Makefile

**Files:** Modify: `Makefile`

- [ ] Replace the upgrade hint in the `validate` target with:

``` make
	  echo "Upgrade with: bun add --global @anthropic-ai/claude-code"; \
```

### Task 5: Skill and knowledge docs describe the bunx hooks

**Files:** Modify:
`.agents/plugins/agentdev/skills/sync-super-linter-tool-versions/SKILL.md`,
`docs/knowledge/data/architecture/renovate-config-validation.md`,
`docs/knowledge/data/codebase/flow-pull-request-checks.md`,
`docs/knowledge/data/codebase/github/workflows.md`

- [ ] In the sync skill, step 3 becomes:

``` markdown
3. Update the matching values in the repository's `.pre-commit-config.yaml`:
   the Prettier version in the local hook's `bunx prettier@<version>` entry,
   plus the Clang Format, Ansible Lint, Hadolint, Ruff, ShellCheck, Gitleaks,
   and Actionlint repository revisions. Preserve the `shellcheck-py` wrapper's fourth version
```

The rest of the step is unchanged.

- [ ] In `architecture/renovate-config-validation`, the one Renovate pin is
  described as the hook's `bunx --package renovate@<version>` entry, tracked by
  a custom manager, instead of the hook's `rev`. The decision itself is
  unchanged.
- [ ] In both codebase map docs, point the
  `.github/workflows/validate-renovate-config.yml` citation at the validator's
  `run` step as it stands after Task 3.

### Task 6: Record the bun-only rule for future work

**Files:** Modify: `AGENTS.md`, `docs/knowledge/data/product.md`

- [ ] In `AGENTS.md`, Best Practice 1 becomes:

``` markdown
1. **Use `uv` for Python and `bun` for JavaScript.** Run project commands through `uv run`; sync with `.devcontainer/scripts/uv-sync.sh` (or `uv sync`) after changing dependencies. Never install packages globally. Every JavaScript invocation — scripts, pre-commit hooks, CI workflows, Ansible roles, Makefile targets, and hints printed to users — goes through `bun` or `bunx`, never `npm`, `npx`, `yarn`, or `pnpm`.
```

- [ ] In `data/product.md` `## Authoring rules`, the matching bullet becomes:

``` markdown
- Use `uv` for Python and `bun` for JavaScript; run through `uv run`; never
  install globally. JavaScript runs through `bun`/`bunx` everywhere — never
  `npm`, `npx`, `yarn`, or `pnpm`.
```

### Task 7: CI green on the pull request

- [ ] `Validate Renovate config` and the reformat workflow's
  `Validate pre-commit and local tool versions` step pass on the PR.

## Spec changes

None — no behavioral change. This is developer tooling; no `data/spec/` document
describes these hooks.

## Depends on

[Self-hosted Renovate in the agent-desktop image](20260925-self-hosted-renovate.md)
ships first: it moves both Renovate workflows onto `bunx` in the agent-desktop
image and rewrites `architecture/renovate-config-validation`, so this plan only
relocates the Renovate pin.

## Verification

- `uv run pre-commit validate-config .pre-commit-config.yaml`
- `uv run pre-commit run --files .pre-commit-config.yaml .github/renovate.json .github/workflows/validate-renovate-config.yml Makefile .agents/plugins/agentdev/skills/sync-super-linter-tool-versions/SKILL.md docs/knowledge/data/architecture/renovate-config-validation.md`
  — `prettier` and `renovate-config-validator` both report Passed.
- `grep -rnE 'npx|npm install|mirrors-prettier|additional_dependencies' .pre-commit-config.yaml .github Makefile`
  prints nothing.
- `sed -nE 's/.*prettier@v?([0-9.]+).*/\1/p' .pre-commit-config.yaml | head -n 1`
  prints `3.8.1`.
- `grep -rnwE 'npm|npx|yarn|pnpm' .pre-commit-config.yaml .github Makefile scripts .devcontainer/scripts`
  shows no invocation of those commands; remaining hits are names in Renovate
  datasources, firewall allowlist entries, or prose.
- `iwe normalize && iwe schema validate` from the repo root.

## Out of scope

- The Ansible roles: they already install every global package with bun.
- Removing Node.js or its bundled `npm` from the image. The NodeSource install
  in the `nodejs` role stays.
- Removing Yarn from the image. The `nodejs` role installs it with bun as a tool
  for the image's users; the rule governs how this repository runs JavaScript,
  not what the image ships.
- Refreshing `source_digest` on the codebase map docs whose sources change. That
  belongs to the `/agentdev:iwe-map` refresh.

## Key references

Verified anchor points (line numbers as of 2026-09-26):

- `.pre-commit-config.yaml:11` — `mirrors-prettier` repo block
- `.pre-commit-config.yaml:68` — `renovatebot/pre-commit-hooks` repo block
- `.pre-commit-config.yaml:79` — existing `repo: local` block
- `.github/renovate.json:36` — `pre-commit/mirrors-prettier` in the Super-Linter
  rule
- `.github/renovate.json:49` — Prettier `additional_dependencies` rule
- `.github/renovate.json:83` — "Commit pins in the Ansible roles' defaults"
  custom manager
- `.github/workflows/validate-renovate-config.yml:42` — validator call; the
  self-hosted Renovate plan rewrites it to read the hook `rev`
- `Makefile:157` — `npm install -g` upgrade hint
- `AGENTS.md:11` — Best Practice 1, `uv` and `bun` toolchain rule
- `docs/knowledge/data/product.md:125` — authoring-rules mirror of Best Practice
  1
- `.agents/plugins/agentdev/skills/sync-super-linter-tool-versions/SKILL.md:29`
  — Prettier `additional_dependencies` wording
- `docs/knowledge/data/architecture/renovate-config-validation.md:20` — pin
  wording; the self-hosted Renovate plan rewrites this decision
- `scripts/validate-super-linter-tool-versions.sh:158` — Prettier version
  extraction regex
- `docs/knowledge/data/codebase/flow-pull-request-checks.md:54` — validator line
  citation
- `docs/knowledge/data/codebase/github/workflows.md:106` — validator line
  citation
