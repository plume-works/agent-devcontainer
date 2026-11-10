# Design

## Context

The IWE knowledge graph holds 32 specs in `docs/knowledge/data/spec/` and 67
architecture documents in `docs/knowledge/data/architecture/`. `openspec/specs/`
is empty. The KB specs already use `### Requirement:` and `#### Scenario:`, but
16 of them have no `## Purpose` and put requirements at `##` level, so
`openspec validate --specs` rejects them as they stand. The other 16 pass, with
warnings for requirement text over 500 characters.

The architecture documents fall into five kinds:

- decision records (a decision plus the alternatives it rejected);
- behavior written as design prose;
- findings (measurements, hypotheses eliminated, closing);
- how-to procedures;
- facts about host tools that a decision relies on.

Most of them mix more than one kind.

OpenSpec 1.17.0's archive rewrites only a spec's `## Requirements` section. It
keeps the text before and after that section byte for byte, and its parser reads
only `## Purpose` and `## Requirements` (`dist/core/specs-apply.js`,
`dist/core/parsers/markdown-parser.js` in `@fission-ai/openspec`).

## Goals / Non-Goals

**Goals:**

- Every behavior is stated once, as a requirement in `openspec/specs/`.
- The rationale that is still in force sits in the same file as the behavior it
  explains.
- Nothing under `docs/knowledge/data/` can again hold a `spec` or
  `architecture` document.

**Non-Goals:**

- Rewriting the migrated requirements. Long requirements are not split, and
  redundancy inside a spec stays as it is; `backlog/deduplicate-spec-requirements`
  keeps that work.
- The `iwe-bootstrap` assets and the `template-consume` guidance that a
  consuming repository receives. They keep their `spec/` and `architecture/`
  scaffold until a follow-up change decides how a consumer adopts OpenSpec.
- Any change to the IWE plan, bug, backlog, feature, release, concept, or
  someday types beyond removing their spec handling.

## Decisions

### Migrated specs are written straight into `openspec/specs/`

Each KB spec becomes `openspec/specs/<slug>/spec.md` with the same slug. It is
normalized to `# <Title> Specification`, `## Purpose` (taken from the KB
`description` when the document has no Purpose), `## Requirements`,
`### Requirement:`, and `#### Scenario:`, and its frontmatter is dropped. This
moves existing behavior without changing it, so the main specs are authored
directly. This change's deltas carry only the behavior it actually changes, and
they apply at archive on top of the migrated specs.

_Rejected:_ writing every migrated spec as an ADDED delta. A capability cannot
take both ADDED and MODIFIED in one change, so `iwe-workflow-skills` and
`line-free-anchors` would need a second change. It would also copy 32 specs
through delta files only to land them unchanged.

### Rationale is a `## Rationale` section after `## Requirements`

It holds the decision in force, who made it, and the alternatives it rejected.
Archive keeps it, and validate ignores it. A delta cannot edit it, so the person
archiving a change folds that change's lasting `design.md` decisions in by hand.
`openspec/config.yaml` states this as archive guidance and as a rule for the
`design` artifact, which must name the capability each decision shapes.

_Rejected:_

- **Rationale only in archived `design.md`.** Rejected alternatives would be
  spread across dated folders, and a planner would not find them by topic.
- **`architecture/` kept as a "why only" folder.** That is the arrangement that
  drifted into duplication, and "no behavior here" cannot be checked by a script.

### Each architecture statement goes where its kind belongs

A behavior statement becomes a requirement only after it is checked against the
code. A decision whose plan is still active is not yet behavior. It moves into
the feature or plan document that owns that work, not into a spec. Facts about
host tools go into the spec's Rationale beside the decision they support.

| Architecture document                                                                                                                                                                                                                                              | Destination                                                                    |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| actions-approval-permission, ai-review-event-selection, dispatched-review-identity, label-review-triggers, pr-review-effort-tiers, pr-review-scenario-validation, pull-request-only-responder, responder-app-identity                                              | `ai-review-gate`                                                               |
| assignee-review-trigger                                                                                                                                                                                                                                            | `ai-review-gate` Rationale, as an alternative `label-review-triggers` rejected |
| adversarial-review, autonomous-implement-loop, explicit-only-workflow-agents, fresh-context-verify, iwe-cli-over-mcp, kb-conflict-free-layout                                                                                                                      | `iwe-workflow-skills`                                                          |
| agentdev-runtime-package, devcontainer-runtime, extra-ca-trust, no-launchpad-ppas, validator-image-install                                                                                                                                                         | `agentdev-runtime-images`                                                      |
| agent-metadata-files                                                                                                                                                                                                                                               | `agent-file-discovery`                                                         |
| ansible-apt-pins, renovate-config-validation, renovate-post-upgrade                                                                                                                                                                                                | `dependency-updates`                                                           |
| catalog-script-language                                                                                                                                                                                                                                            | new `catalog-scripts`                                                          |
| ci-agent-plugin-availability, no-code-graph, supported-harnesses                                                                                                                                                                                                   | `catalog-lifecycle`                                                            |
| claude-remote-control-resume, claude-remote-control-server-mode, claude-remote-control-server-continue, claude-remote-control-spawn-mode-switch                                                                                                                    | `claude-remote-control`                                                        |
| cloud-session-devcontainer                                                                                                                                                                                                                                         | new `cloud-session-devcontainer`                                               |
| agent-auth-persistence, uv-environment-location                                                                                                                                                                                                                    | new `devcontainer-state`                                                       |
| devcontainer-home-volume                                                                                                                                                                                                                                           | `features/devcontainer-home-volume` (its plan is still active)                 |
| evidence-without-commit-ids                                                                                                                                                                                                                                        | `plan-checkbox-evidence`                                                       |
| fork-pull-request-builds, self-repository-uses                                                                                                                                                                                                                     | new `ci-workflows`                                                             |
| formatter-ownership                                                                                                                                                                                                                                                | `pre-commit-gate`                                                              |
| gh-authentication-shim, gh-wrapper-image-only                                                                                                                                                                                                                      | `devcontainer-git-credentials`                                                 |
| line-free-anchors                                                                                                                                                                                                                                                  | `line-free-anchors`                                                            |
| manual-stacked-prs                                                                                                                                                                                                                                                 | `stacked-prs`                                                                  |
| module-layout, template-boundary                                                                                                                                                                                                                                   | `template-consumption`                                                         |
| nested-docker-provisioning                                                                                                                                                                                                                                         | `devcontainer-docker-storage`                                                  |
| nested-subagent-dispatch                                                                                                                                                                                                                                           | `nested-agent-dispatch`; its fixture goes to the `skill-rehearsal-runs` guide  |
| opencode-catalog-bridge                                                                                                                                                                                                                                            | `opencode-catalog-bridge`                                                      |
| opencode-full-access-in-devcontainer                                                                                                                                                                                                                               | `devcontainer-opencode-policy`                                                 |
| pr-verification-sections                                                                                                                                                                                                                                           | new `pr-description`                                                           |
| self-improve-consolidation, self-improve-runtime                                                                                                                                                                                                                   | `self-improve-learning-loop`                                                   |
| standalone-opencode-runtime                                                                                                                                                                                                                                        | `standalone-opencode-runtime`                                                  |
| claude-remote-control-archived-pre-created-session, -expired-session-recovery, -pointerless-server-start, -server-restart-resume, -worktree-restart-resume; cloud-session-host-restarts; pr-review-correctness-bar; rereview-gate-pending; verify-versus-pr-review | `data/findings/`                                                               |
| drqp-devcontainer-testing, sibling-devcontainer-testing, skill-rehearsal-runs, worktree-hooks                                                                                                                                                                      | `docs/guides/`                                                                 |

A new spec takes only the behavior its architecture document states and the
code confirms. It is authored directly, like the migrated specs.

### Findings are a graph type without a stage

`type: finding`, with `.iwe/schemas/finding.yaml` and a `findings` hub listed in
`data/index.md`. A finding's `## Closing` section says whether it is open. Its
anchors are not resolved, because a measurement describes the code it measured.

_Rejected:_ a finding as an open OpenSpec change. Most findings close without a
change to behavior, and an open change would have no tasks to apply.

### References name a spec by its path

Code comments and graph documents name a spec as `openspec/specs/<slug>`. A
specific spot is `openspec/specs/<slug>/spec.md#<heading-slug>`. The rule in
`AGENTS.md#comments` changes from "`spec/` or `architecture/` key" to this
form. Graph links become relative Markdown links that leave `docs/knowledge/`,
which the graph already uses for code paths.

### IWE agents lose their spec steps rather than being repointed

`iwe-planner` drops `## Spec changes`. `iwe-shipper` drops its spec merge.
`iwe-verifier` checks a plan against its tasks and against the specs the linked
OpenSpec change touches. `iwe-implementer`, `iwe-revision-evaluator`, and
`iwe-adversarial-reviewer` drop their `## Spec changes` references.

## Risks / Trade-offs

- [A behavior statement is copied into a spec that the code no longer matches]
  → each one is checked against the code before it becomes a requirement. A
  mismatch is filed as a bug instead of being migrated.
- [Rationale goes stale because archive cannot update it] → the archive guidance
  in `openspec/config.yaml` makes folding it in part of every archive.
- [Consumers bootstrapped from the catalog keep a `spec/` hub that no IWE skill
  maintains any more] → recorded as a backlog item for the follow-up change
  named in Non-Goals.
- [`openspec` is installed by the `agentic_tools` role but missing from a host]
  → tasks run it as `bunx @fission-ai/openspec@<pinned version>`.

## Migration Plan

1. Migrate the 32 specs, and validate with `openspec validate --specs`.
2. Fold the architecture documents in by the table above, one destination spec
   per commit.
3. Add the finding type, move findings and guides, and remove the `spec/` and
   `architecture/` folders, hubs, and schemas.
4. Rewrite links and comments, update the gate and the catalog, and then archive
   this change so its deltas apply to the migrated specs.

Rollback before archive is a revert of the branch. The KB folders are removed
only after every destination exists.
