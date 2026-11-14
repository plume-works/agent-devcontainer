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

- A `custom.regex` manager in `.github/renovate.json` finds new releases for the
  pin. A change to the pin merges only after the workflow passes at the new
  release.
- The workflow runs in `agentdev-devcontainer` at the digest that
  `devcontainer-compose-pins.yml` pins. Renovate moves each copy of that digest
  in one pull request, so the required check runs in a new image before that
  image can merge.
- `Renovate config validation finished` is the required check, and it reports on
  each pull request. A paths filter skips the validation job when a pull request
  does not change the config, the hook pins, or the image pin.
- `--no-global` is necessary. Without it, the validator applies the global
  schema, which accepts a different set of options than the repository schema.
  For example, a repository config with the global option `allowedCommands`
  passes without the flag.
- `--strict` also fails on warnings and on a config that needs migration.
- The bot reads its global options only from `RENOVATE_*` variables, never from
  a config file in the repository.
- Neither gate checks that the `matchStrings` of a custom manager find a match.
