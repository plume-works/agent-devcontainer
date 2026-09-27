---
type: architecture
description: Why .github/renovate.json is validated by a pre-commit hook and a workflow at the one Renovate version the self-hosted bot runs, why both pass --no-global, and why the workflow runs in the pinned agent-desktop image.
generated:
  by: claude-code/opus-5
  at: 2026-09-26T12:00:00Z
sources:
- resource: .pre-commit-config.yaml
- resource: .github/workflows/validate-renovate-config.yml
- resource: .github/workflows/renovate.yml
- resource: https://docs.renovatebot.com/config-validation/
---

# Renovate config validation

## Decision

`.github/renovate.json` is validated by
`renovate-config-validator --no-global --strict`, from a pre-commit hook and
from `validate-renovate-config.yml`. Both run the Renovate release that the
`renovate-config-validator` hook's `rev` in `.pre-commit-config.yaml` names, and
`renovate.yml` runs the bot at that same release. One pin serves hook, workflow,
and bot, so the version that validates the config is the version that reads it.
Renovate bumps that `rev` like any other hook, and the bump merges only once the
workflow passes at the new version.

Nothing else checks the config before it reaches the bot. A mistyped option or
an unparseable regex in a custom manager does not fail anything — it presents as
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

The self-hosted bot's global options therefore never live in a checked-in
Renovate config file: `renovate.yml` passes them as `RENOVATE_*` environment
variables.

## The workflow is the image canary

The validation job runs in `ghcr.io/plume-works/agent-desktop` at the digest
`devcontainer-compose-pins.yml` pins, and Renovate moves every copy of that
digest in one pull request — the workflow's own among them. A digest bump
therefore runs this required check inside the new image before it can automerge,
so an image that cannot run the bot's toolchain fails there rather than in the
next bot run.

`Renovate config validation finished` is the required check. It reports on every
pull request, and a paths filter skips the validation job itself on a pull
request that touches none of the config, the hook pins, the image pin, or the
image's sources.

## Scope

Both gates check that the configuration is *valid*. Neither checks that a custom
manager's `matchStrings` matches anything, so a regex that silently extracts
zero dependencies passes both. That remains a manual check.
