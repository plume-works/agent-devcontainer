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

[Bug: an AI re-review that comments leaves its own change request blocking
merge](bugs/ai-rereview-comment-keeps-changes-requested.md)

[Bug: firewalled Docker Hub pulls fail at the CloudFront
CDN](bugs/firewall-docker-hub-cloudfront.md)

[Bug: git-new-branch worktree mode fails on a standalone deployment's root-owned
/workspaces](bugs/git-new-branch-worktree-unwritable-workspaces.md)

[Bug: the Remote Control watcher restarts a session that never comes up on every
tick](bugs/remote-control-watcher-start-loop.md)

[Bug: plan tasks edit spec documents that only Ship may
change](bugs/plan-tasks-edit-specs.md)

[Bug: Plan tasks bundle independent
observations](bugs/plan-tasks-bundle-independent-observations.md)

[Bug: a workspace on a pre-pin image has no gitleaks or actionlint and nothing
says so](bugs/workspace-image-lacks-hook-binaries.md)

[Bug: a CBM daemon start failure latches the standalone runtime
degraded](bugs/cbm-start-failure-latches-degraded.md)

[Bug: Codex login stops being shared between standalone
projects](bugs/standalone-codex-auth-unshared.md)

[~/.claude.json stops being the volume
symlink](bugs/claude-json-symlink-replaced.md)

[Unstageable routing option in the improve
skill](bugs/self-improve-unstageable-routing-option.md)

[Reviewer decline asymmetry](bugs/self-improve-reviewer-decline-asymmetry.md)

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

[Bug: xpra_setup installs Ubuntu's xpra
3.1.5](bugs/xpra-setup-installs-ubuntu-xpra.md)

[Bug: CI/CD publishes images before testing
them](bugs/ci-publishes-images-before-acceptance.md)

[Bug: the Remote Control pin ignores
/clear](bugs/remote-control-pin-ignores-clear.md)

[Bug: PR updates skip the re-review
evaluation](bugs/pr-update-skips-review-eval.md)

[Bug: every gh call in the devcontainer leaks a D-Bus session and a
keyring](bugs/devcontainer-dbus-autolaunch-leak.md)

[Orphan-kill supervision test fails
intermittently](bugs/supervision-orphan-kill-test-flaky.md)

[Bug: a comment-requested review's gate does not count toward
merge](bugs/dispatched-review-gate-not-counted.md)

[Command-result evidence is judged
inconsistently](bugs/command-result-evidence-ambiguous.md)

[Bug: a client is recovered on its own budget before its dependency's failure is
confirmed](bugs/supervisor-client-recovered-before-dependency.md)

[Bug: CBM cache under a checkout another UID owns stops the Dev
Container](bugs/cbm-cache-under-foreign-owned-checkout.md)

[Bug: body-shape schema tests share one scratch graph across concurrent
runs](bugs/body-shape-schemas-shared-scratch.md)
