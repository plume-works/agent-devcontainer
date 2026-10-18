---
type: feature
stage: accepted
description: OpenCode sessions in the devcontainer allow every action and every filesystem path, with the approved policy restored in opencode.json on every container start.
generated:
  by: codex/gpt-5
  at: 2026-10-18T18:54:34Z
sources:
- resource: docs/knowledge/data/plans/20261018-opencode-full-access-config.md
---

# OpenCode full-access config

## Purpose

The devcontainer is the isolation boundary, so OpenCode inside it should not
stop for its own action or external-directory permission prompts.

## Behaviour

On every container start, a devcontainer-owned script will patch OpenCode's
`opencode.json` so the wildcard action permission and every external directory
are allowed. The patch will preserve catalog registration and unrelated user
settings, and restore changed managed values on the next start.

## Edge cases

- A malformed config will fail visibly and remain unchanged.
- Catalog subagents' deny rules remain in force independently of the global user
  policy.

## Open questions

None — the maintainer approved the exact policy object.

## References

- Plan: [Configure devcontainer OpenCode for full
  access](../plans/20261018-opencode-full-access-config.md)
