---
type: adr
stage: accepted
description: One bridge module exports both the v1 server entry and the v2 effect entry, and both read the catalog through one parser.
---

# One bridge module serves OpenCode v1 and v2

The default export of the OpenCode bridge has the v1 `server` entry and the v2
`effect` entry. v1 does not use `effect`, and v2 runs only `effect` when it gets
both. Both entries read the catalog through one parser.

## Considered Options

- A bridge for v2 only. Rejected: a v1 installation, such as a consumer image or
  a Mac that still uses v1, then loses the catalog.
- One plugin directory for each major version. Rejected: the configuration must
  then know the installed major version, and two copies of the catalog parser
  are necessary.
- A `setup` export next to `effect`. Rejected: v2 runs only `effect`, so `setup`
  never runs.
- Run the v2 setup through `console` reports or through `Effect.runPromise` of
  the plugin. Rejected: neither sends failures to `opencode.log`.
- A log file of the bridge for v2 failures. Rejected: the file is outside the
  log of OpenCode.

## Consequences

- `v2Effect` runs the v2 setup through the `fromPromise` adapter of the host, so
  its failures go to `opencode.log`. The bridge loads the adapter only when v2
  calls `effect`, so v1 never loads it.
- The bridge has no runtime dependencies. It uses only type imports and the
  built-in modules of Bun. Root owns the staged catalog and it is read-only, so
  no `node_modules` can be next to it.
- The v2 setup waits for no registration, because v2 holds each request until
  the setup of a plugin is complete.
