---
type: feature
stage: implemented
description: bun and bunx are the only JavaScript runners — the Prettier and Renovate pre-commit hooks run through bunx and AGENTS.md rules out npm, npx, yarn, and pnpm.
generated:
  by: claude-code/opus-5.5
  at: 2026-11-01T04:32:17Z
sources:
- resource: docs/knowledge/data/plans/20260925-bun-for-node-tooling.md
- resource: .pre-commit-config.yaml
- resource: AGENTS.md
---

# bun as the only JavaScript runner

## Purpose

The image installs JavaScript tools with bun only, so hooks, scripts, and
instructions must run them through `bun`/`bunx`, never through an npm-family
runner.

## Behaviour

**Hooks run through bunx.** The Prettier and Renovate config validator
pre-commit hooks are `language: system` hooks that run their tool through
`bunx`, with the package version pinned in the hook's `entry`. Renovate keeps
that pin current.

**The rule is stated.** `AGENTS.md` names `bun` and `bunx` as the only
JavaScript runners for scripts, hooks, CI, Ansible, Makefile targets, and hints
printed to users, and rules out `npm`, `npx`, `yarn`, and `pnpm`.

## Edge cases

- **The Prettier version** is pinned in its `bunx prettier@<version>` hook
  entry, which Renovate's npm regex manager bumps.

## Open questions

None — the design is settled.

## References

- Plan: [bun for Node tooling](../plans/20260925-bun-for-node-tooling.md)
