---
type: hub
description: Architecture decision records — each one decision, its context, and the reason for it.
stage: living
---

# 🏛️ ADRs

*One decision per document in `adr/NNNN-<slug>.md`, `type: adr`: a short title,
then 1 to 3 sentences that give the context, the decision, and the reason. This
hub lists each ADR at `stage: proposed` or `stage: accepted`. Nobody edits an
accepted ADR; a new ADR supersedes it.*

[Code and tests are the only statement of
behaviour](adr/0001-code-and-tests-state-behaviour.md)

[Each decision is a short ADR in the
graph](adr/0002-decisions-are-adrs-in-the-graph.md)

[Adversarial review is a separate agent, not part of
Verify](adr/0003-adversarial-review-is-a-separate-agent.md)

[Agents use the iwe CLI, not an IWE MCP
server](adr/0004-agents-use-the-iwe-cli.md)

[A bug records its own correction](adr/0005-bug-records-its-own-fix.md)

[A CRITICAL result stops Ship with no
override](adr/0006-critical-blocks-ship-with-no-override.md)

[The durable-knowledge audit runs in an isolated
agent](adr/0007-durable-knowledge-audit-is-an-isolated-agent.md)

[The graph is different from OKF only where OKF causes merge
work](adr/0008-graph-diverges-from-okf-only-for-merge-cost.md)

[The graph layout keeps parallel pull requests free of merge
conflicts](adr/0009-graph-layout-avoids-merge-conflicts.md)

[Implement can stack on a dependency in review; Ship
cannot](adr/0010-implement-stacks-on-a-dependency-in-review.md)

[The IWE workflow skills are in agentdev, with an iwe-
prefix](adr/0011-iwe-skills-in-agentdev-with-iwe-prefix.md)

[Each kind of knowledge has one home, and the archive is by
release](adr/0012-one-home-per-kind-and-archive-by-release.md)

[The release impact of a plan is a frontmatter
field](adr/0013-release-impact-is-a-plan-frontmatter-field.md)

[A plan revision is evaluated after its audit, then
committed](adr/0014-revision-is-evaluated-after-its-audit.md)

[The workflow rulebooks are catalog
agents](adr/0015-rulebooks-live-in-catalog-agents.md)

[The saved Verify report is keyed by commit and catalog
hash](adr/0016-saved-verify-report-keyed-by-commit-and-catalog.md)

[Only the Ship and Plan entry skills are
explicit-only](adr/0017-ship-and-plan-skills-are-explicit-only.md)

[Ship and Verify start from a prompt without the conversation; Implement runs in
place](adr/0018-ship-and-verify-run-from-a-conversation-free-prompt.md)

[Verify checks only what the plan
promised](adr/0019-verify-checks-only-the-plan-contract.md)

[Skills keep their bare names, and commands have a
namespace](adr/0020-bare-skill-names-namespaced-commands.md)

[Configuration is documented variables, never shell
code](adr/0021-configuration-is-documented-variables.md)

[The standalone runtime shares functions, not lifecycle
commands](adr/0022-deploy-image-reuses-runtime-helpers.md)

[Each service authenticates on its own](adr/0023-every-service-authenticates.md)

[Extra CA trust goes through the system
store](adr/0024-extra-ca-through-system-store.md)

[The session bus address is an image
ENV](adr/0025-fixed-session-bus-address-in-image-env.md)

[A latch waits for a retry in deploy and ends a Dev
Container](adr/0026-latch-waits-for-retry-or-ends-devcontainer.md)

[One bridge module serves OpenCode v1 and
v2](adr/0027-one-bridge-module-for-opencode-v1-and-v2.md)

[OpenCode starts first, and optional work does not stop
it](adr/0028-opencode-first-optional-work-after.md)

[OpenCode reads the catalog through a bridge
plugin](adr/0029-opencode-reads-catalog-through-bridge.md)

[Image builds get no package from
Launchpad](adr/0030-packages-avoid-launchpad.md)

[PID 1 runs the create phase, and the image label declares the lifecycle
commands](adr/0031-pid1-runs-the-create-phase.md)

[The wheel RECORD is the integrity record of the
runtime](adr/0032-runtime-integrity-from-wheel-record.md)

[The runtime is one Python package that the base image does not
contain](adr/0033-runtime-is-one-python-package.md)

[supervisord runs in the PID 1 process, and a controller owns the
order](adr/0034-supervisord-in-process-as-pid1.md)

[On OpenCode v2, hooks apply the tool limits of a catalog
agent](adr/0035-v2-tool-limits-in-hooks.md)

[validate_agent_files comes from the build
context](adr/0036-validator-built-from-build-context.md)

[The AI review gate trusts only named
bots](adr/0037-ai-review-trusts-named-bots.md)

[apt packages have no fixed version within a fixed Ubuntu
release](adr/0038-apt-packages-float-within-base-release.md)

[Bundled code is relative to the skill, under
agent-code/](adr/0039-bundled-code-under-agent-code.md)

[Catalog scripts are standard-library
Python](adr/0040-catalog-scripts-are-standard-library-python.md)

[CI agent jobs run the lifecycle commands against their
checkout](adr/0041-ci-agent-jobs-run-lifecycle-commands.md)

[The Expo bridge keeps its record in its own
repository](adr/0042-expo-bridge-record-in-its-own-repository.md)

[The Expo bundle prepares EAS builds and leaves the workflow to
Expo](adr/0043-expo-bundle-leaves-the-workflow-to-expo-plugin.md)

[The image installs the catalog, and the create phase installs it
again](adr/0044-image-and-create-phase-both-install-catalog.md)

[Knowledge data is never a template
path](adr/0045-knowledge-data-is-never-a-template-path.md)

[Pushes to main build after a cooldown that a newer push
cancels](adr/0046-main-builds-after-cancellable-cooldown.md)

[The runtime ships no code-graph index](adr/0047-no-code-graph-index.md)

[The graph keeps no codebase map](adr/0048-no-codebase-map.md)

[One catalog tree, installed and not
copied](adr/0049-one-catalog-tree-installed-not-copied.md)

[One post-upgrade task behind one
script](adr/0050-one-post-upgrade-task-behind-one-script.md)

[Pull request description guidance is a separate
file](adr/0051-pr-description-guidance-separate-file.md)

[The Renovate version that reads the config also validates
it](adr/0052-renovate-config-validated-at-bot-version.md)

[Renovate runs self-hosted as a GitHub
App](adr/0053-renovate-self-hosted-as-github-app.md)

[Setup progress is a root file and the Git reference of the consumed commit
stays in JSON](adr/0054-setup-progress-in-root-file.md)

[A run promotes only the images it built and
accepted](adr/0055-tags-move-only-to-accepted-images-of-the-run.md)

[validate_agent_files ships on its
own](adr/0056-validate-agent-files-ships-on-its-own.md)

[Each worktree loads its catalog from a marketplace in the
worktree](adr/0057-worktree-catalog-from-in-worktree-marketplace.md)

[The AI review verdict follows severity
alone](adr/0058-ai-review-verdict-follows-severity.md)

[A label requests an AI review and a label stops
it](adr/0059-ai-reviews-requested-and-held-by-label.md)

[Push checks on main start at the last passing
run](adr/0060-checks-start-at-last-passing-run.md)

[CI provisions the Python environment and never activates
it](adr/0061-ci-python-through-uv-run.md)

[The CI image build always publishes](adr/0062-image-build-always-publishes.md)

[Plan work branches share one iteration
counter](adr/0063-plan-branches-share-one-iteration-counter.md)

[The pre-commit hooks own each formatter and the CI
check](adr/0064-pre-commit-hooks-own-formatters-and-ci-gate.md)

[The review responder workflow runs only on pull request
events](adr/0065-responder-runs-only-on-pull-request-events.md)

[The AI review posts as a GitHub App of the
organization](adr/0066-review-app-is-own-github-app.md)

[Local actions use the self-repository
syntax](adr/0067-self-repository-syntax-for-local-actions.md)

[Dependent pull requests stack with merges
only](adr/0068-stack-dependent-work-with-merges-only.md)

[The trusted-bot approval checks the full push
history](adr/0069-trusted-bot-approval-checks-push-history.md)

[Containers share only the Claude credentials, on one auth volume for each
UID/GID pair](adr/0070-claude-credentials-shared-other-state-per-instance.md)

[A cloud session works on its host, not in a Dev
Container](adr/0071-cloud-sessions-work-on-the-host.md)

[Setup that needs Coder user secrets runs from the agent
start](adr/0072-coder-secrets-only-in-the-agent-start.md)

[Docker garbage collection is a supervised hourly service with a list of the
volumes that it can
remove](adr/0073-docker-gc-removes-only-disposable-volumes.md)

[Only the gh wrapper of the image authenticates
gh](adr/0074-image-gh-wrapper-is-the-only-gh-shim.md)

[The agent account has one empty home volume for each
instance](adr/0075-one-empty-home-volume.md)

[OpenCode runs with full access, merged into its configuration at each
start](adr/0076-opencode-full-access-merged-at-each-start.md)

[Server mode is an opt-in next to session
mode](adr/0077-remote-control-server-mode-is-opt-in.md)

[No Dev Container lifecycle command starts Remote
Control](adr/0078-remote-control-starts-from-the-agent-start.md)

[The runtime supervises the Dev Container engine, and the image has no SSH
server](adr/0079-runtime-supervises-the-nested-engine.md)

[Session mode resumes one pinned
conversation](adr/0080-session-mode-pins-one-conversation.md)

[Each checkout links .venv to its own environment on the home
volume](adr/0081-venv-link-to-the-home-volume.md)

[Each tool reads only its own key in
`.agent.metadata.json`](adr/0082-agent-metadata-key-per-tool.md)

[Committed text names places by anchors, not by line
numbers](adr/0083-anchors-not-line-numbers.md)

[Claude Code and OpenCode are the only
harnesses](adr/0084-claude-code-and-opencode-only.md)

[Git decides which paths agent file discovery
ignores](adr/0085-git-is-the-ignore-authority.md)

[A ticked plan task needs an evidence line that only a shape test
checks](adr/0086-plan-ticks-need-evidence-lines.md)

[Only a command that the user types authorizes a self-improve
change](adr/0087-self-improve-authorization-from-typed-commands.md)

[The self-improve plugin lives in this
repository](adr/0088-self-improve-lives-in-this-repository.md)

[The self-improve reviewer holds no
tools](adr/0089-self-improve-reviewer-holds-no-tools.md)

[The self-improve runtime uses only the standard
library](adr/0090-self-improve-runtime-uses-only-the-standard-library.md)

[Both harnesses permit a subagent depth of 5 in the
containers](adr/0091-subagent-nesting-depth-five.md)
