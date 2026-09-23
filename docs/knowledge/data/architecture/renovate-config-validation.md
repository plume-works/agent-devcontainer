---
type: architecture
description: Why .github/renovate.json is validated twice — a pre-commit hook at a pinned Renovate and a workflow at the current one — and why both pass --no-global.
generated:
  by: claude-code/opus-5
  at: 2026-09-23T00:00:00Z
sources:
- resource: .pre-commit-config.yaml
- resource: .github/workflows/validate-renovate-config.yml
- resource: https://docs.renovatebot.com/config-validation/
---

# Renovate config validation

## Decision

`.github/renovate.json` is validated by
`renovate-config-validator --no-global --strict`, from a pre-commit hook and
from `validate-renovate-config.yml`. The hook runs a Renovate pinned by its hook
revision; the workflow runs whatever `npx renovate` resolves to that day. The
divergence is the point, not an oversight.

Nothing checked the config before it reached the bot. A mistyped option or an
unparseable regex in a custom manager does not fail anything — it presents as
updates that quietly stop arriving, which is indistinguishable from having no
updates to make.

## Why `--no-global`

Without it the validator applies the self-hosted **global** schema, which
accepts and rejects a different set of options than the repository schema
Renovate actually reads for this file. A repository config carrying a
global-only option such as `allowedCommands` passes the default invocation and
fails under `--no-global`. The upstream pre-commit hook's default invocation has
exactly that problem, so the flag is passed explicitly in both places.
`--strict` additionally fails on warnings and on a config needing migration.

## Why one side is pinned and the other is not

The hosted Mend app always runs the current Renovate. A gate that only ever
validated against a pinned version could stay green while the bot that reads the
file breaks. The workflow therefore tracks the moving target: a failure there,
with the hook still green, is the signal that the live bot is about to break.

The hook is the other half of that trade — a fast, deterministic local check
whose result does not change because upstream published overnight.

## Scope

Both gates check that the configuration is *valid*. Neither checks that a custom
manager's `matchStrings` matches anything, so a regex that silently extracts
zero dependencies passes both. That remains a manual check.
