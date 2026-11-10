# Tasks

`openspec` below means `bunx @fission-ai/openspec@1.17.0` on any host where the
`agentic_tools` role has not installed it. A task that deletes an architecture
document also repoints every link to it in the same commit, so `iwe normalize`
followed by `iwe schema validate` passes after every task.

## 1. Conventions

- [x] 1.1 Add to `openspec/config.yaml`:
  - a `specs` rule: rationale goes only in a `## Rationale` section after
    `## Requirements` and states why, never behavior;
  - a `design` rule: each decision names the capability it shapes;
  - `operations.archive.guidance`: fold every lasting `design.md` decision into
    that capability's `## Rationale` in the archive commit.

  Verify with `openspec instructions design --change specs-sole-source-of-truth --json`,
  which returns the new rule.

- [x] 1.2 Update `AGENTS.md`: `#comments` rule 3 names a spec as
      `openspec/specs/<slug>`, and `#project-memory` sends behavior and rationale to
      `openspec/specs/` and findings to `data/findings/`. Verify that
      `grep -nE 'data/(spec|architecture)|spec/ or|architecture/' AGENTS.md` prints
      nothing.

## 2. Migrate the KB specs

- [x] 2.1 Copy the 16 KB specs that already have `## Purpose` to
      `openspec/specs/<slug>/spec.md`. Drop their frontmatter and title each one
      `# <Title> Specification`. Verify that
      `openspec validate --specs` reports no ERROR for them, and that a script
      comparing requirement and scenario headings shows each copy has the same
      names as its source.
- [x] 2.2 Migrate the other 16 specs the same way. Add `## Purpose` from the KB
      `description`, wrap the requirements in `## Requirements`, and demote each
      `## Requirement:` to `### Requirement:`. `template-consumption`'s
      `## Pull request description guidance` goes to its `## Rationale`. Verify
      that `openspec validate --specs` reports zero failed specs and that the same
      heading comparison matches for all 32.

## 3. Fold architecture documents into existing specs

For each task in this group: check every behavior statement against the code at
the anchors the document names. A statement the code confirms and the spec
lacks becomes a requirement with a scenario. A statement the code contradicts
becomes a bug under `data/bugs/` and is not migrated. The decision, who made
it, and the rejected alternatives go into `## Rationale`. Measurement history
and provenance sections are dropped. Then delete the architecture document.
Every task verifies with `openspec validate <slug> --type spec` and
`iwe schema validate`.

- [x] 3.1 Fold into `ai-review-gate`: actions-approval-permission,
      ai-review-event-selection, dispatched-review-identity, label-review-triggers,
      pr-review-effort-tiers, pr-review-scenario-validation,
      pull-request-only-responder, and responder-app-identity. Fold
      assignee-review-trigger in as an alternative that label-review-triggers
      rejected.
- [x] 3.2 Fold into `iwe-workflow-skills`: adversarial-review,
      autonomous-implement-loop, explicit-only-workflow-agents,
      fresh-context-verify, iwe-cli-over-mcp, and kb-conflict-free-layout.
- [x] 3.3 Fold into `agentdev-runtime-images`: agentdev-runtime-package,
      devcontainer-runtime, extra-ca-trust, no-launchpad-ppas, and
      validator-image-install.
- [x] 3.4 Fold into `dependency-updates`: ansible-apt-pins,
      renovate-config-validation, and renovate-post-upgrade.
- [x] 3.5 Fold into `catalog-lifecycle`: ci-agent-plugin-availability,
      no-code-graph, and supported-harnesses.
- [x] 3.6 Fold into `claude-remote-control`: claude-remote-control-resume,
      -server-mode, -server-continue, and -spawn-mode-switch.
- [x] 3.7 Make these one-to-one folds:
  - agent-metadata-files → `agent-file-discovery`
  - evidence-without-commit-ids → `plan-checkbox-evidence`
  - formatter-ownership → `pre-commit-gate`
  - gh-authentication-shim and gh-wrapper-image-only →
    `devcontainer-git-credentials`
  - line-free-anchors → `line-free-anchors`
  - manual-stacked-prs → `stacked-prs`
  - nested-docker-provisioning → `devcontainer-docker-storage`
  - opencode-full-access-in-devcontainer → `devcontainer-opencode-policy`
  - self-improve-consolidation and self-improve-runtime →
    `self-improve-learning-loop`
- [x] 3.8 Fold these larger behavior documents:
  - module-layout and template-boundary → `template-consumption`
  - opencode-catalog-bridge → `opencode-catalog-bridge`
  - standalone-opencode-runtime → `standalone-opencode-runtime`
  - nested-subagent-dispatch → `nested-agent-dispatch` (its `## Fixture`
    section is held for task 5.3)

  Verify that each destination's requirement count grows by the statements the
  code confirmed, as listed in the commit message.

## 4. New specs from architecture-only behavior

- [x] 4.1 Create these specs from the behavior the code confirms, each with its
      `## Rationale`, and delete the source documents:
  - `catalog-scripts` from catalog-script-language
  - `cloud-session-devcontainer` from cloud-session-devcontainer
  - `devcontainer-state` from agent-auth-persistence and uv-environment-location
  - `ci-workflows` from fork-pull-request-builds and self-repository-uses
  - `pr-description` from pr-verification-sections

  Verify with `openspec validate --specs`.

- [x] 4.2 Move architecture/devcontainer-home-volume's decision, constraints,
      rejected alternatives, and accepted risk into
      `data/features/devcontainer-home-volume.md`, whose plan is still active, and
      delete the architecture document. Verify with `iwe schema validate`.

## 5. Findings and guides

- [ ] 5.1 Add `.iwe/schemas/finding.yaml`, bind it to `data/findings/*` in
      `.iwe/config.toml`, add the `data/findings.md` hub, and link it from
      `data/index.md`. Verify with `iwe schema validate`.
- [ ] 5.2 Move these to `data/findings/<slug>.md` with `type: finding`, link
      them from the hub, and repoint their links:
  - claude-remote-control-archived-pre-created-session
  - claude-remote-control-expired-session-recovery
  - claude-remote-control-pointerless-server-start
  - claude-remote-control-server-restart-resume
  - claude-remote-control-worktree-restart-resume
  - cloud-session-host-restarts
  - pr-review-correctness-bar
  - rereview-gate-pending
  - verify-versus-pr-review

  Each one's settled decision gets a link to the owning spec. Verify with
  `iwe schema validate`.

- [ ] 5.3 Move drqp-devcontainer-testing, sibling-devcontainer-testing,
      skill-rehearsal-runs (merged with nested-subagent-dispatch's fixture), and
      worktree-hooks to `docs/guides/<slug>.md`, without frontmatter, and repoint
      their links. Verify that `ls docs/knowledge/data/architecture/` is empty.

## 6. Retire the KB spec and architecture types

- [ ] 6.1 Delete `docs/knowledge/data/spec/`, `data/spec.md`,
      `data/architecture/`, `data/architecture.md`, `.iwe/schemas/spec.yaml`, and
      `.iwe/schemas/architecture.yaml`. Remove their bindings in
      `.iwe/config.toml` and their `data/index.md` entries. Verify that
      `iwe normalize` followed by `iwe schema validate` passes.
- [ ] 6.2 Forbid `type: spec` and `type: architecture` in `.iwe/schemas/okf.yaml`.
      Add a pytest under `docs/knowledge/tests/` that runs `iwe schema validate` on
      a scratch graph under `/tmp` holding such a document and expects it to fail
      naming the document. Verify with
      `uv run pytest docs/knowledge/tests/<new test file>`.
- [ ] 6.3 Rewrite every remaining Markdown link under `docs/knowledge/data/` that
      points into the removed folders, so it points to the owning
      `openspec/specs/<slug>/spec.md`, finding, or guide. Verify that
      `grep -rnE '\]\([^)]*(spec|architecture)/[a-z0-9-]+\.md' docs/knowledge/data`
      prints nothing and that `iwe schema validate` passes.
- [ ] 6.4 Update `docs/knowledge/AGENTS.md`, `SCHEMA.md`, `STRUCTURE.md`, and
      `README.md`: no spec or architecture type, findings added, and behavior and
      rationale sent to `openspec/specs/`. Verify that a grep for `data/spec` and
      `data/architecture` in those files prints nothing.
- [ ] 6.5 Rewrite every code comment and docstring that cites `spec/<slug>` or
      `architecture/<slug>` (workflows, actions, scripts, Ansible, `py_packages/`,
      `.claude/`, `.devcontainer/`, `docs/knowledge/tests/`) to
      `openspec/specs/<slug>`. Verify that
      `grep -rnE '(^|[^/])(spec|architecture)/[a-z0-9-]+' --include=*.py --include=*.sh --include=*.ts --include=*.yml --include=*.yaml . | grep -v openspec/`
      prints nothing outside `.tmp/`.

## 7. Anchor gate

- [ ] 7.1 Extend `scripts/check-anchors.py`: `SCAN_GLOBS` gains `openspec/**/*.md`,
      and `resolver_spans` resolves every anchor in `openspec/specs/**/spec.md` and
      none in `data/findings/` or `openspec/changes/`. Its docstring cites
      `openspec/specs/line-free-anchors`. Add tests to
      `scripts/tests/test_check_anchors.py` for these cases:
  - a line number in a spec fails;
  - an unresolved anchor in a spec fails;
  - an unresolved anchor in an OpenSpec change passes.

  Verify with `uv run pytest scripts/tests/test_check_anchors.py` and
  `uv run scripts/check-anchors.py`.

## 8. Catalog spec handling

- [ ] 8.1 Remove `## Spec changes` authoring and its risk-scaled delta rules from
      `iwe-planner.agent.md`. A plan whose work changes behavior links its OpenSpec
      change. Verify that `grep -n 'Spec changes' .agents/plugins/agentdev/agents/iwe-planner.agent.md`
      prints nothing.
- [ ] 8.2 Remove the spec merge and its spec-retirement step from
      `iwe-shipper.agent.md`. Make `iwe-verifier.agent.md` check the plan against
      the specs its linked OpenSpec change touches. Drop the `## Spec changes`
      references in `iwe-implementer`, `iwe-revision-evaluator`, and
      `iwe-adversarial-reviewer`. Verify that
      `grep -rn 'Spec changes\|data/spec\|data/architecture' .agents/plugins/agentdev/agents/iwe-*.agent.md`
      prints nothing.
- [ ] 8.3 Repoint `iwe-explore`, `iwe-audit`, and `iwe-setup` from
      `data/spec`/`data/architecture` to `openspec/specs/` and `data/findings/`, and
      run `validate_agent_files` on the catalog. Verify the same grep across
      `.agents/plugins/agentdev/skills/iwe-{explore,audit,setup}/` prints nothing.
- [ ] 8.4 File a backlog item for the iwe-bootstrap scaffold and template-consume
      follow-up named in design.md Non-Goals. Verify with `iwe schema validate`.

## 9. Integration

- [ ] 9.1 Run `openspec validate --specs`, `openspec validate specs-sole-source-of-truth`,
      `iwe schema validate`, and `pre-commit run --all-files`. All of them pass,
      and the validate output no longer carries the "target spec does not exist"
      INFO for `iwe-workflow-skills` or `line-free-anchors`.

## Workflow follow-up

- Archive the change so the `project-knowledge`, `iwe-workflow-skills`, and
  `line-free-anchors` deltas apply, and fold design.md's lasting decisions into
  the `## Rationale` of `project-knowledge` and `line-free-anchors`.
