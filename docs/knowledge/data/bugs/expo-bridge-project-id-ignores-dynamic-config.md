---
type: bug
description: The Expo bridge's easProjectId status check reads only app.json, so a project whose app.config.js or app.config.ts sets, adds, or drops extra.eas.projectId gets the wrong answer.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-26T04:20:00Z
sources:
- resource: https://github.com/plume-works/vscode-expo-bridge
- resource: https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/protocol.md
- resource: https://docs.expo.dev/workflow/configuration/
- resource: docs/knowledge/data/architecture/vscode-expo-bridge.md
---

# Bug: the Expo bridge's project ID check ignores dynamic app config

## Symptom

`eas-host status` reports `easProjectId` as failing, with "extra.eas.projectId
not set in app.json", for a project that sets the ID in `app.config.ts` or
`app.config.js`. A project whose `app.json` holds the ID while its dynamic
config drops it reports the check as passing.

## Reproduction

Call the host's `status()` on a Mac-like fixture folder holding `eas.json` and:

1. only `app.config.ts`, exporting `expo.extra.eas.projectId` — the check
   reports `ok: false`;
2. `app.json` without the ID, plus `app.config.js` that adds it to the `config`
   it receives — `ok: false`;
3. `app.json` with the ID, plus `app.config.js` that returns `extra: {}` —
   `ok: true`.

## Root cause

`readProjectId` reads `<folder>/app.json` and looks for
`expo.extra.eas.projectId`; the protocol documents the check the same way. Expo
resolves the app config from `app.json` and then from `app.config.js` or
`app.config.ts`, which receives the static config and may add, change, or drop
any field, so `app.json` alone does not decide the resolved value.

The host cannot simply evaluate the dynamic config: outside a confirmed `build`,
it never evaluates project code ([VS Code Expo
bridge](../architecture/vscode-expo-bridge.md), Security model).

## Fix

Not fixed. `eas-host status` exits by `available` alone, so no build is blocked;
the wrong check line misleads agents and would mislead any diagnostic built on
it. A fix either resolves the ID where evaluating project code crosses no trust
boundary — the container, which can run `bunx expo config --json --type public`
against its own code — or has the host report the check as not statically
checkable when an `app.config.*` file exists.

## Key references

Verified anchor points (line numbers as of 2026-10-26):

In `plume-works/vscode-expo-bridge` at `b10949f`:

- `packages/host/src/status.ts:118` — `status`, the `easProjectId` check; `:140`
  — `readProjectId`
- `packages/protocol/src/index.ts:105` — `StatusResult.checks.easProjectId`
- `docs/protocol.md:152` — the `easProjectId` check's documented meaning
- `packages/workspace/bin/eas-host.ts:102` — the exit code follows `available`
