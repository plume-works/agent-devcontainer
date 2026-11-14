---
type: plan
created: 2026-11-13
release: internal
description: Add a test for each behaviour that only a spec states, move the last spec text to its home, and delete data/spec/ with its schema, its hub, and every reference to it.
sources:
- resource: docs/spec-audit/requirements.jsonl
- resource: .iwe/config.toml
- resource: .iwe/schemas/spec.yaml
---

# Add the missing tests and delete the specs

## Context

After the two removal steps, `data/spec/` holds only the requirements that [the
spec usefulness audit](../findings/spec-usefulness-audit.md) labelled
`needs-test` (18), `user-doc` (2), and `no-home` (3). The labels are in
`docs/spec-audit/requirements.jsonl`. Each `needs-test` row has a `fate_note`
that says what the test must show.

This plan is the last step of [Shrink the knowledge base to an issue tracker and
decision records](../backlog/shrink-knowledge-base-to-issues-and-adrs.md). After
it, the repository has no spec.

## Approach

Each `needs-test` requirement gets a test that runs the behaviour, as the test
rules in `AGENTS.md#tests` require. Five of the 18 are decisions in workflow
files, and [Test the decisions that the workflows
make](20261113-test-the-workflow-decisions.md) adds their tests. This plan adds
the other 13.

The 2 `user-doc` requirements are in a README already. The requirement about the
GitHub ruleset goes to a guide, because the ruleset is a repository setting and
not code. The 2 other `no-home` requirements are the bugs about the consumption
guide that an earlier plan filed.

Then `data/spec/` and each thing that exists only for it are deleted. The
glossary loses each term that no prose uses after the specs are gone. The audit
data in `docs/spec-audit/` is deleted last, because each plan in the series
reads it.

## Implementation Steps

### Task 1: Add the missing tests

**Files:** Create and Modify: the test files that each `fate_note` names

Each test shows what the `fate_note` of its row says.

- [ ] A test runs `agent-file-discovery` "Git failures do not abort discovery".
- [ ] A test runs `agentdev-runtime-images` "image builds contact no Launchpad
  host".
- [ ] A test runs `agentdev-runtime-images` "gh resolves to the image's
  wrapper".
- [ ] A test runs `agentdev-runtime-images` "the bootstrap trusts an extra CA
  bundle".
- [ ] A test runs `catalog-lifecycle` "the catalog is installed at image build
  time and again by postCreateCommand".
- [ ] A test runs `catalog-lifecycle` "registering a catalog root replaces
  earlier registrations".
- [ ] A test runs `catalog-scripts` "catalog scripts are standard-library
  Python".
- [ ] A test runs `devcontainer-docker-storage` "the host-side init runs without
  HOME".
- [ ] A test runs `devcontainer-git-credentials` "gh authenticates from the git
  credential helper".
- [ ] A test runs `devcontainer-state` "the create phase re-owns the sibling
  checkout volume".
- [ ] A test runs `pre-commit-gate` "every commit path runs the hooks, merges
  included".
- [ ] A test runs `standalone-opencode-runtime` "startup prepares or reuses one
  workspace" on a reused checkout.
- [ ] A test runs `update-branch` "update-branch brings in the branch's upstream
  before the base" for a branch that has no upstream.

### Task 2: Move the last spec text to its home

**Files:** Create: `docs/knowledge/data/guides/repository-settings.md`; Modify:
`docs/knowledge/data/guides.md`, `AGENTS.md`

- [ ] `ansible/roles/playwright_browser/README.md` says that the Playwright
  dependencies of a project stay with the project.
- [ ] `README.md` gives the scope of the standalone OpenCode image.
- [ ] `data/guides/repository-settings` gives the GitHub ruleset that blocks a
  merge into a dependent branch, and how to set it.
- [ ] `data/guides.md` links the guide.
- [ ] The rule about stacked pull requests in `AGENTS.md` links no spec.

### Task 3: Delete `data/spec/` and what exists only for it

**Files:** Delete: `docs/knowledge/data/spec/`, `docs/knowledge/data/spec.md`,
`.iwe/schemas/spec.yaml`, and their copies under
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/`; Modify:
`.iwe/config.toml`, `docs/knowledge/data/index.md`, `docs/knowledge/SCHEMA.md`,
`docs/knowledge/STRUCTURE.md`, `docs/knowledge/AGENTS.md`,
`docs/knowledge/README.md`, `README.md`,
`.agents/plugins/agentdev/skills/iwe-audit/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-explore/SKILL.md`, and the seed copies

- [ ] `docs/knowledge/data/spec/` and `docs/knowledge/data/spec.md` do not
  exist.
- [ ] `.iwe/config.toml` has no `[schemas.spec]`, and
  `.iwe/config.toml#schemas.hub` does not match `data/spec`.
- [ ] `.iwe/schemas/spec.yaml` does not exist.
- [ ] `docs/knowledge/data/index.md#reference` has no link to a spec hub.
- [ ] `docs/knowledge/SCHEMA.md`, `docs/knowledge/STRUCTURE.md`,
  `docs/knowledge/AGENTS.md`, and `docs/knowledge/README.md` describe no spec
  type and no spec folder.
- [ ] `README.md` links no spec.
- [ ] No skill and no agent rulebook under `.agents/plugins/agentdev/` names
  `data/spec/`.
- [ ] No docstring and no comment outside `docs/` names a spec.
- [ ] The seed under the `iwe-bootstrap` assets has no spec hub and no spec
  schema, and its support files agree with the workspace.
- [ ] No document outside `data/archive/` links a spec.

### Task 4: Prune the glossary

**Files:** Modify: `docs/knowledge/data/glossary.md`

- [ ] Each term in the glossary is used in prose outside `data/archive/`.

### Task 5: Delete the audit data

**Files:** Delete: `docs/spec-audit/`; Modify:
`docs/knowledge/data/findings/spec-usefulness-audit.md`

- [ ] `docs/spec-audit/` does not exist.
- [ ] `findings/spec-usefulness-audit` names no file under `docs/spec-audit/`.

### Task 6: Close the backlog task

**Files:** Modify:
`docs/knowledge/data/backlog/shrink-knowledge-base-to-issues-and-adrs.md`,
`docs/knowledge/data/backlog.md`

- [ ] `backlog/shrink-knowledge-base-to-issues-and-adrs` is at `stage: done`
  with `completed`, is in `data/archive/next-release/backlog/`, and has no link
  in `data/backlog.md`.

## Acceptance

None — no behavioral change

## Depends on

[Move the decisions from the specs into
ADRs](../archive/next-release/plans/20261113-move-decisions-into-adrs.md)

[Make ASD-STE100 the rule for all
prose](../archive/next-release/plans/20261113-ste100-prose-rule.md)

[Test the decisions that the workflows
make](20261113-test-the-workflow-decisions.md)

## Verification

``` bash
iwe normalize && iwe schema validate
uv run scripts/check-anchors.py
uv run pytest docs/knowledge/tests
uv run pytest .agents/plugins/agentdev/tests/test_iwe_seed.py
uv run validate_agent_files --recommend . --require-marketplace claude
```

## Out of scope

- A fix for a defect that a new test finds. `/agentdev:iwe-capture bug` files
  it.
- The archived plans and their `## Spec changes` sections.

## Key references

- `docs/spec-audit/requirements.jsonl` — the rows whose `fate` is `needs-test`,
  `user-doc`, or `no-home`, with `fate_note`.
- `AGENTS.md#tests` — the rules that each new test follows.
- `.iwe/config.toml#schemas.hub` — the hub binding that loses `data/spec`.
- `.iwe/schemas/spec.yaml` — the schema that is deleted.
- `docs/knowledge/data/index.md#reference` — the section that links the spec
  hub.
- `.agents/plugins/agentdev/tests/test_iwe_seed.py::test_scaffold_support_files_match_the_publisher_workspace`
  — the test that compares the seed with the workspace.
