---
type: adr
stage: accepted
description: renovate-config-validator --no-global --strict validates the Renovate config at the one Renovate version that the hook, the validation workflow, and the bot share.
---

# The Renovate version that reads the config also validates it

No other check reads `.github/renovate.json` before the bot. A wrong option or a
bad custom-manager regex only stops updates, and nothing shows it. The
`renovate-config-validator` pre-commit hook and
`.github/workflows/validate-renovate-config.yml` validate the config with
`--no-global --strict`, at the release that the hook pins. The bot runs at that
release too.

## Considered Options

- Install Renovate in the `agentdev-devcontainer` image. Rejected: it is still
  one pin, but it adds a large Node dependency tree to the image of each
  developer. `bunx` downloads the pinned release for each run.

## Consequences

- `--no-global` is necessary. Without it, the validator applies the global
  schema, which accepts a different set of options than the repository schema.
- `--strict` also fails on warnings and on a config that needs migration.
- The bot reads its global options only from `RENOVATE_*` variables, never from
  a config file in the repository.
- Neither gate checks that the `matchStrings` of a custom manager find a match.
