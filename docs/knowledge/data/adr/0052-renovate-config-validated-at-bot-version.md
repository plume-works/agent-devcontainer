---
type: adr
stage: accepted
description: renovate-config-validator --no-global --strict validates the Renovate config at the one Renovate version that the hook, the validation workflow, and the bot share.
---

# The Renovate version that reads the config also validates it

Nothing else checks `.github/renovate.json` before it reaches the bot, and a
mistyped option or an unparseable custom-manager regex presents as updates that
quietly stop arriving, which looks the same as having no updates to make. The
`renovate-config-validator` pre-commit hook and
`.github/workflows/validate-renovate-config.yml` validate the config with
`--no-global --strict`, at the release that the hook pins. The bot runs at that
release too, so one pin serves the hook, the workflow, and the bot.

## Considered Options

- Install Renovate in the `agentdev-devcontainer` image. Rejected: it is still
  one pin, but it brings a large Node dependency tree into every developer's
  image for the rare commit that touches `.github/renovate.json`. `bunx` fetches
  the pinned release for each run instead.

## Consequences

- `Renovate config validation finished` is the required check, and it reports on
  each pull request. A paths filter skips the validation job when a pull request
  does not change the config, the hook pins, or the image pin.
- `--no-global` is necessary. Without it, the validator applies the global
  schema, which accepts and rejects a different set of options than the
  repository schema that Renovate reads for this file. For example, a repository
  config with the global option `allowedCommands` passes without the flag.
- The bot reads its global options only from `RENOVATE_*` variables, never from
  a config file in the repository.
- Both gates check that the config is valid. Neither checks that the
  `matchStrings` of a custom manager find a match, so a regex that silently
  extracts zero dependencies passes both.
