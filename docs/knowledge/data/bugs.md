---
type: hub
description: Bug reports, investigations, and repro notes.
stage: living
generated:
  by: human:author
  at: 2026-08-01T00:00:00Z
---

# 🐛 Bugs

*One document per bug in `bugs/<slug>.md`, listed here whether open or closed.
Its title, body sections, and stages are defined under Bugs in `SCHEMA.md` and
enforced by `.iwe/schemas/bug.yaml`.*

[~/.claude.json stops being the volume
symlink](bugs/claude-json-symlink-replaced.md)

[A capitalized @Claude mention was admitted, then
misrouted](bugs/responder-mention-case-sensitivity.md)

[The review orchestrator ends its turn while its passes are still
running](bugs/review-orchestrator-ends-turn-while-passes-run.md)

[Validator warning visibility](bugs/validator-warning-visibility.md)

[Missing map skill](bugs/missing-map-skill.md)

[Plan checkbox over-claiming](bugs/plan-checkbox-over-claiming.md)

[Pin bumps invalidate map docs](bugs/pin-bumps-invalidate-map-docs.md)

[Self-test unwritable-root check assumes a non-root
user](bugs/self-test-unwritable-root-check.md)

[Fixture git inherits the outer commit's
index](bugs/fixture-git-inherits-commit-index.md)

[Reviewer decline asymmetry](bugs/self-improve-reviewer-decline-asymmetry.md)

[Unstageable routing option in the improve
skill](bugs/self-improve-unstageable-routing-option.md)

[AI review gate was self-waivable from the PR
body](bugs/ai-review-gate-self-waivable.md)

[The review opt-out marker fired too
broadly](bugs/skip-ai-review-marker-overreach.md)

[Fisher install over untracked
plugins](bugs/fisher-install-over-untracked-plugins.md)

[Runner label bump ahead of
actionlint](bugs/runner-label-ahead-of-actionlint.md)

[Codex leaves ${CLAUDE_SKILL_DIR} unresolved in agentdev
skills](bugs/codex-skill-dir-unresolved.md)

[Codex never loads the agentdev catalog
agents](bugs/codex-catalog-agents-not-loaded.md)

[Codex tables inside cbm hooks block break cbm
install](bugs/cbm-codex-hooks-block-foreign-tables.md)

[Bug: HTTPS git push hangs on Coder's askpass when gh's login is only a session
token](bugs/coder-askpass-push-hang.md)

[Bug: Ship's release-link rule is undefined for a plan with no feature or
bug](bugs/ship-release-link-without-feature.md)

[Bug: gh-stack extension install needs a token the image build
lacks](bugs/gh-stack-install-needs-token.md)

[Bug: Coder workspace Dev Container is lost on
restart](bugs/coder-devcontainer-lost-on-restart.md)

[Bug: Image rebuild lost when a later push to main cancels its
run](bugs/main-image-rebuild-lost-on-cancel.md)

[Bug: gh stack push overwrites a stack layer whose remote is
ahead](bugs/gh-stack-push-overwrites-remote-layer.md)

[Bug: firewalled Docker Hub pulls fail at the CloudFront
CDN](bugs/firewall-docker-hub-cloudfront.md)

[Bug: xpra_setup installs Ubuntu's xpra
3.1.5](bugs/xpra-setup-installs-ubuntu-xpra.md)

[Bug: CI/CD publishes images before testing
them](bugs/ci-publishes-images-before-acceptance.md)

[Bug: Plan tasks bundle independent
observations](bugs/plan-tasks-bundle-independent-observations.md)

[Bug: the Remote Control pin ignores
/clear](bugs/remote-control-pin-ignores-clear.md)

[Bug: the Expo bridge's fix terminal launches the container's shell on the
Mac](bugs/expo-bridge-fix-terminal-remote-shell.md)

[Bug: PR updates skip the re-review
evaluation](bugs/pr-update-skips-review-eval.md)

[Bug: the Expo bridge builds only the devcontainer window's root
folder](bugs/expo-bridge-builds-only-window-root.md)

[Bug: Expo bridge windows sharing a container break each other's
socket](bugs/expo-bridge-shared-socket-across-windows.md)

[Bug: the Expo bridge's bun fix upgrades a bun the check never
runs](bugs/expo-bridge-bun-fix-misses-path-bun.md)

[Bug: every gh call in the devcontainer leaks a D-Bus session and a
keyring](bugs/devcontainer-dbus-autolaunch-leak.md)

[Bug: Codex login stops being shared between standalone
projects](bugs/standalone-codex-auth-unshared.md)

[Bug: the Expo bridge's project ID check ignores dynamic app
config](bugs/expo-bridge-project-id-ignores-dynamic-config.md)

[Bug: git-new-branch worktree mode fails on a standalone deployment's root-owned
/workspaces](bugs/git-new-branch-worktree-unwritable-workspaces.md)

[Bug: plan tasks edit spec documents that only Ship may
change](bugs/plan-tasks-edit-specs.md)

[Bug: the Expo bridge's build log tail drops
lines](bugs/expo-bridge-build-log-tail-drops-lines.md)

[Bug: the container sees the Expo bridge's build log only after the build
ends](bugs/expo-bridge-build-log-invisible-until-close.md)

[Bug: the Expo bridge's project ID diagnostic stays stale after a config
edit](bugs/expo-bridge-project-id-diagnostic-stale-after-config-edit.md)

[Bug: the Expo bridge's CocoaPods fix does not repair an unlinked
keg](bugs/expo-bridge-cocoapods-fix-misses-unlinked-keg.md)

[Bug: the Expo bridge's simulator profile quick fix omits the bun
pin](bugs/expo-bridge-simulator-profile-quick-fix-omits-bun.md)
