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
tests for 7 of the other 13. The 5 other requirements get no test, because each
one is configuration, a rule, or a guard against a possible future edit, and not
logic. The last one is [a deploy runtime that reuses a checkout does not
configure the git credential
helper](../bugs/reused-checkout-gets-no-credential-helper.md).

The 2 `user-doc` requirements are in a README already. The requirement about the
GitHub ruleset goes to the consumption guide of the `template-consume` skill,
because the ruleset is a repository setting that each adopter sets. The 2 other
`no-home` requirements are the bugs about the consumption guide that an earlier
plan filed.

Then `data/spec/` and each thing that exists only for it are deleted. The
glossary loses each term that no prose uses after the specs are gone. The audit
data in `docs/spec-audit/` is deleted last, because each plan in the series
reads it.

## Implementation Steps

### Task 1: Add the missing tests

**Files:** Create and Modify: the test files that each `fate_note` names

Each test shows what the `fate_note` of its row says.

- [x] A test runs `agent-file-discovery` "Git failures do not abort discovery".
  - **Evidence:**
    `py_packages/validate_agent_files/tests/test_gitignore_discovery.py` runs
    discovery with a `git` that fails `check-ignore` and with no `git` on
    `PATH`; 21 passed.
- [x] A test runs `agentdev-runtime-images` "image builds contact no Launchpad
  host".
  - **Evidence:** `scripts/tests/test_cache_git_ppa_release.py` runs the script
    against a locally signed fake PPA: release with `--latest=false`, no
    replacement, and nothing published on a wrong key or a broken hash chain; 5
    passed.
- [x] A test runs `agentdev-runtime-images` "the bootstrap trusts an extra CA
  bundle".
  - **Evidence:** `scripts/tests/test_devcontainer_init.py` runs the init
    script: an empty `.extra-ca.crt` with no CA, the named bundle over the Node
    one, the Node fallback, a skipped unreadable Node bundle, and exit 1 on an
    unreadable named bundle; 7 passed.
- [x] A test runs `catalog-lifecycle` "registering a catalog root replaces
  earlier registrations".
  - **Evidence:**
    `py_packages/agentdev_runtime/tests/test_catalog_claude_register.py` runs
    `catalog.claude` with the recording `claude` stub: each marketplace from the
    same root is swept in every scope before the add, an absent plugin does not
    stop it, and a failed add raises; 3 passed.
- [x] A test runs `devcontainer-git-credentials` "gh authenticates from the git
  credential helper".
  - **Evidence:** `scripts/tests/test_gh_wrapper.py` runs the wrapper with a
    stand-in real gh and a real git credential helper: the helper token, no
    helper, a set token, and exit 127 with no real gh on `PATH`; 4 passed.
- [x] A test runs `devcontainer-state` "the create phase re-owns the sibling
  checkout volume".
  - **Evidence:** The Docker tests in
    `scripts/tests/test_agentdev_devcontainer_lifecycle.py` cover the re-own, an
    owned volume, and the open workspace;
    `py_packages/agentdev_runtime/tests/test_claim_project.py` adds a root
    account and no mount; 2 passed.
- [x] A test runs `update-branch` "update-branch brings in the branch's upstream
  before the base" for a branch that has no upstream.
  - **Evidence:** `.agents/plugins/agentdev/tests/test_update_branch.py` adds a
    branch with no upstream (`untracked`), a failed `ls-remote` (`FETCH_FAILED`,
    not `gone`), and a local upstream (`remote = .`); 14 passed.

### Task 2: Move the last spec text to its home

**Files:** Modify:
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`,
`AGENTS.md`

- [x] `ansible/roles/playwright_browser/README.md` says that the Playwright
  dependencies of a project stay with the project.
  - **Evidence:** Already true: `ansible/roles/playwright_browser/README.md`
    says the browser path stays writable for "a project-owned Playwright"; no
    edit.
- [x] `README.md` gives the scope of the standalone OpenCode image.
  - **Evidence:** Already true: `README.md#standalone-opencode-runtime` states
    the image scope; no edit.
- [x] The consumption guide of the `template-consume` skill gives the GitHub
  ruleset that blocks a merge into a dependent branch, and how to set it.
  - **Evidence:** `consumption-guide.md#the-ruleset-on-dependent-branches` gives
    the rule and the `gh api` call, copied from the live ruleset; Workflow B
    links it.
- [x] The rule about stacked pull requests in `AGENTS.md` links no spec.
  - **Evidence:** Already true: the rule links
    `adr/0068-stack-dependent-work-with-merges-only.md`; no edit.

### Task 3: Delete `data/spec/` and what exists only for it

**Files:** Delete: `docs/knowledge/data/spec/`, `docs/knowledge/data/spec.md`,
`.iwe/schemas/spec.yaml`, and their copies under
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/`; Modify:
`.iwe/config.toml`, `docs/knowledge/data/index.md`, `docs/knowledge/SCHEMA.md`,
`docs/knowledge/STRUCTURE.md`, `docs/knowledge/AGENTS.md`,
`docs/knowledge/README.md`, `README.md`,
`.agents/plugins/agentdev/skills/iwe-audit/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-explore/SKILL.md`, and the seed copies

- [x] `docs/knowledge/data/spec/` and `docs/knowledge/data/spec.md` do not
  exist.
  - **Evidence:** `iwe delete` removed the 15 specs and the hub and cleaned 93
    linking documents.
- [x] `.iwe/config.toml` has no `[schemas.spec]`, and
  `.iwe/config.toml#schemas.hub` does not match `data/spec`.
  - **Evidence:** Both entries are gone from `.iwe/config.toml`;
    `iwe schema validate` passes.
- [x] `.iwe/schemas/spec.yaml` does not exist.
  - **Evidence:** `git rm` of the schema.
- [x] `docs/knowledge/data/index.md#reference` has no link to a spec hub.
  - **Evidence:** The Spec bullet is gone from `data/index.md`.
- [ ] `docs/knowledge/SCHEMA.md`, `docs/knowledge/STRUCTURE.md`,
  `docs/knowledge/AGENTS.md`, and `docs/knowledge/README.md` describe no spec
  type and no spec folder.
- [x] `README.md` links no spec.
  - **Evidence:** Already true: `grep data/spec README.md` finds nothing.
- [x] No skill and no agent rulebook under `.agents/plugins/agentdev/` names
  `data/spec/`.
  - **Evidence:** `iwe-audit/SKILL.md` no longer names `data/spec/`;
    `grep -rn data/spec .agents/` finds nothing.
- [x] No docstring and no comment outside `docs/` names a spec.
  - **Evidence:** The `test_check_anchors.py` spec fixture and its docstring are
    gone; the remaining "spec" words name the self-improve research specs or the
    archived Ship review items.
- [x] The seed under the `iwe-bootstrap` assets has no spec hub and no spec
  schema, and its support files agree with the workspace.
  - **Evidence:** The seed lost `spec.md`, `spec.yaml`, its config entries, and
    its index bullet; `test_iwe_seed.py` passes, 6 tests.
- [x] No document outside `data/archive/` links a spec.
  - **Evidence:** No live link or `sources` entry names a spec file;
    `check-anchors` passes, and `docs/research` and `docs/user-stories` lost
    their spec links.

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
