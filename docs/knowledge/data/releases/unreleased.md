---
type: release
description: The accumulator page for work merged but not yet released.
version: unreleased
stage: unreleased
status: draft
generated:
  by: claude-code/opus-5.5
  at: 2026-10-17T12:00:00Z
---

# Unreleased

*Work that has shipped to main but not yet to users. The ship skill adds an
inclusion link here for every feature or fix as it lands — a new feature under
`## Added`, a released feature that gained behavior under `## Changed`, a bug
under `## Fixed`; cutting a release renames this file to the version number and
starts a fresh one.*

## Added

[Renovate maintains checksum-carrying
pins](../features/renovate-maintains-checksums.md)

[git-new-branch](../features/git-new-branch.md)

[Self-improve plugin in the
catalog](../features/self-improve-plugin-in-catalog.md)

[Fresh codebase map on push](../features/fresh-map-on-push.md)

[Native stacked pull requests](../features/native-stacked-prs.md)

[OpenCode as a catalog host](../features/opencode-catalog-host.md)

[Resume the Remote Control conversation across
restarts](../features/claude-remote-control-resume.md)

[Expo apps build for iOS through EAS](../features/expo-eas-builds.md)

[Docker storage limits](../features/docker-storage-limits.md)

[update-branch pulls the branch's
upstream](../features/update-branch-pulls-upstream.md)

[Remote Control autostart on
Coder](../features/coder-remote-control-autostart.md)

[Agent sign-in without credential
seeding](../features/agent-sign-in-without-seeding.md)

[Codex full-access config](../features/codex-full-access-config.md)

[PR feedback resolution resolves merge
conflicts](../features/pr-feedback-resolves-merge-conflicts.md)

[bun as the only JavaScript runner](../features/bun-only-javascript-runner.md)

[OpenCode web UI autostart on
Coder](../features/opencode-web-coder-autostart.md)

[Automatic CBM indexing for OpenCode
workspaces](../features/opencode-workspace-cbm-indexing.md)

## Changed

[Agentdev IWE workflow skills](../features/agentdev-iwe-workflow-skills.md)

[AI responder workflows](../features/ai-responder-workflows.md)

## Fixed

[Image rebuild lost when a later push to main cancels its
run](../bugs/main-image-rebuild-lost-on-cancel.md)

[HTTPS git push hangs on Coder's askpass when gh's login is only a session
token](../bugs/coder-askpass-push-hang.md)

[Codex never loads the agentdev catalog
agents](../bugs/codex-catalog-agents-not-loaded.md)

[Codex leaves ${CLAUDE_SKILL_DIR} unresolved in agentdev
skills](../bugs/codex-skill-dir-unresolved.md)

[Fixture git inherits the outer commit's
index](../bugs/fixture-git-inherits-commit-index.md)

[The review orchestrator ends its turn while its passes are still
running](../bugs/review-orchestrator-ends-turn-while-passes-run.md)

[Coder workspace Dev Container is lost on
restart](../bugs/coder-devcontainer-lost-on-restart.md)

[Ship's release-link rule is undefined for a plan with no feature or
bug](../bugs/ship-release-link-without-feature.md)
