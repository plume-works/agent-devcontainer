---
type: bug
description: Replay could raise an uncaught metadata error while preparing an early refresh verdict or collecting evidence.
generated:
  by: codex/gpt-5
  at: 2026-10-21T06:23:54Z
sources:
- resource: .agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py
- resource: .agents/plugins/agentdev/tests/test_stale_map_docs_replay.py
- resource: https://github.com/plume-works/agent-devcontainer/pull/412#discussion_r4333349274
---

# Bug: Replay leaks broken metadata as a traceback

## Symptom

Replay could terminate with `SCRIPT_FAILURE` and a traceback instead of a
`BROKEN` verdict and `RESULT=BROKEN_METADATA`.

## Reproduction

Give a map document no recorded digest, place one of its existing sources under
malformed metadata, and run `--replay`. The early refresh path previously
reached evidence preparation without containing the metadata exception.

## Root cause

Metadata validation happened after early refresh conditions, and evidence
preparation could resolve masks outside the exception boundary that translates
`BrokenMetadata` into the script's public result contract.

## Fix

Replay validates both working-tree and committed metadata before every early
refresh verdict. Broken designations are converted to `BROKEN` inside the
per-document exception boundary, so the run exits with code 5.

## Key references

Verified anchor points (line numbers as of 2026-10-21):

- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:646` —
  metadata validation in `replay_verdict`
- `.agents/plugins/agentdev/skills/iwe-map/agent-code/stale-map-docs.py:676` —
  per-document exception boundary
- `.agents/plugins/agentdev/tests/test_stale_map_docs_replay.py:234` —
  `test_malformed_metadata_is_broken_when_missing_digest_would_refresh`
