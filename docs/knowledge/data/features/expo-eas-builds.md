---
type: feature
stage: implemented
description: The template devcontainer passes EXPO_TOKEN to every consumer, and template-consume's opt-in Expo profile prepares an adopted Expo app for EAS cloud iOS builds driven from the Linux devcontainer.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-16T00:00:00Z
sources:
- resource: .devcontainer/devcontainer.json
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
- resource: docs/knowledge/data/architecture/template-boundary.md
---

# Expo apps build for iOS through EAS

## Purpose

An Expo app that needs native iOS builds can be developed entirely in the Linux
devcontainer: EAS Build runs the native build on Expo's cloud Macs, and Expo's
official Claude plugin supplies the agent skills that drive it. The template
supplies only the environment those skills need.

## Behaviour

**Every consumer gets the token passthrough.** `.devcontainer/devcontainer.json`
sets `"EXPO_TOKEN": "${localEnv:EXPO_TOKEN}"` in `containerEnv`. The token lives
in the host environment or the hosting platform's secret store, never in the
repository or a volume; a consumer that never sets it gets an empty, inert
variable.

**An Expo consumer opts into the Expo profile.** Setup in
`/agentdev:template-consume` asks whether the consumer is an Expo app. On yes it
records `"expo"` in the marker's `optional_bundles`, adds no `tracked_paths`,
and applies the guide's Optional Expo setup:

- the Expo hosts join `.devcontainer/firewall-allowlist.txt`;
- `.env.eas-simulator` is ignored by git;
- every `eas.json` build profile pins `bun` to the devcontainer's bun version;
- the root `AGENTS.md` keeps the template's content and holds the Expo
  template's `AGENTS.md` body under `## Expo`, with `npx` translated to `bunx`;
  the separate Expo `AGENTS.md` is deleted and the root one recorded as
  customized;
- `.claude/settings.json` keeps `expo@claude-plugins-official` enabled.

**Update mode keeps the bun pin current.** When an update changes
`devcontainer-compose-pins.yml` for an Expo consumer, it compares
`bun --version` in the rebuilt container with each `eas.json` build profile and
updates the pin.

The contract is [Template consumption](../spec/template-consumption.md); the
Template-class and consumer-owned split is [Template
boundary](../architecture/template-boundary.md).

## Edge cases

- **A non-Expo consumer.** Setup makes none of the Expo edits and
  `optional_bundles` omits `"expo"`; `EXPO_TOKEN` is still passed, empty.
- **A Coder workspace.** The token is a Coder user secret. It reaches the
  processes the Dev Container's sub-agent starts — terminals, IDE sessions,
  agents — while `${localEnv:EXPO_TOKEN}` resolves empty in the container's base
  environment and lifecycle hooks ([Coder IDE baseline
  template](../spec/coder-ide-baseline.md)).
- **A local Docker host.** The token comes from the environment that runs
  `devcontainer up`.
- **The app lives under an ignored path.** EAS archives the project with a
  `git clone` of the enclosing repository, so the app must be tracked.

## Open questions

- The Expo firewall host list has not been exercised with the firewall enabled.

## References

- Plan: [Expo profile for template
  adoption](../plans/20261014-expo-eas-template-profile.md)
