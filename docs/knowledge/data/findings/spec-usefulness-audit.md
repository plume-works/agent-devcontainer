---
type: finding
description: Every requirement and rationale entry in data/spec/ compared with the code — most requirements repeat a test or a rulebook, the rationale is the part found nowhere else, and one requirement in eight is not fully true.
sources:
- resource: docs/knowledge/data/spec
- resource: docs/spec-audit
- resource: docs/knowledge/data/backlog/shrink-knowledge-base-to-issues-and-adrs.md
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: scripts/check-ship-records.py
- resource: AGENTS.md
---

# What the specs state that code, tests, and decision records would not

## Question

[Shrink the knowledge base to an issue tracker and decision
records](../backlog/shrink-knowledge-base-to-issues-and-adrs.md) proposes
deleting `data/spec/` and keeping source code with its tests as the only
statement of behaviour, a registry of decision records for the reasons, and a
glossary for project terms. What would that lose, and what has to exist before
the specs go?

## Measurement

The checkout at commit `c81efa7e`: 40 specs, 10,964 lines, holding 264
requirements, 616 scenarios, and 189 `## Rationale` entries that list 382
rejected alternatives. For scale, the repository holds 18,249 lines of Python
outside tests, 31,590 lines of tests, 7,237 lines of skill and agent rulebooks,
and 2,673 lines of workflow YAML.

Every requirement and every rationale entry was read against the code, rulebook,
or configuration it describes. No test suite was run. Each requirement was
labelled for whether it is true, whether something executable enforces it, what
it tells a reader that the implementation does not, and where its content would
go if the spec were deleted. The specs were consolidated one commit earlier
(`05a5aa7d` added 5,854 lines to `data/spec/` and removed 1,010), so the
accuracy figures are measured at the specs' best.

The row for each requirement, rationale entry, and spec is in
`docs/spec-audit/`, with the meaning of every label in
`docs/spec-audit/README.md`.

### Requirements

| Measure                                                             | Count | Share |
| ------------------------------------------------------------------- | ----- | ----- |
| Every clause true                                                   | 230   | 87%   |
| At least one clause contradicted or unimplemented                   | 32    | 12%   |
| Central claim contradicted                                          | 1     | 0.4%  |
| Not checkable from the repository                                   | 1     | 0.4%  |
| A test asserts the behaviour                                        | 94    | 36%   |
| Tests cover some clauses or scenarios                               | 71    | 27%   |
| A schema, linter, or CI step enforces it, or a test only reaches it | 14    | 5%    |
| Nothing executable                                                  | 85    | 32%   |
| Tells a reader nothing the implementation and tests do not          | 143   | 54%   |
| Gathers behaviour spread over several files                         | 41    | 16%   |
| States a guarantee the code meets without announcing                | 61    | 23%   |
| Records a fact about a third-party system                           | 10    | 4%    |
| Its distinctive content is a reason                                 | 9     | 3%    |

Twenty of the 40 specs hold at least one requirement that is not fully true.

Scenario coverage follows what implements the behaviour:

| Implemented by                   | Requirements | Scenarios | Scenarios a test exercises |
| -------------------------------- | ------------ | --------- | -------------------------- |
| Python                           | 80           | 191       | 173 (91%)                  |
| Code and prose together          | 73           | 178       | 98 (55%)                   |
| A skill or agent rulebook        | 58           | 155       | 7 (5%)                     |
| Workflow YAML                    | 18           | 42        | 3 (7%)                     |
| Configuration                    | 14           | 18        | 2 (11%)                    |
| Shell                            | 11           | 20        | 13 (65%)                   |
| Dockerfile or Compose            | 9            | 10        | 5 (50%)                    |
| A setting outside the repository | 1            | 2         | 0                          |

Where each requirement's content would go:

| Destination                                               | Count |
| --------------------------------------------------------- | ----- |
| Deleted: a test already states it                         | 118   |
| Deleted: a second prose copy of a skill or agent rulebook | 67    |
| Deleted: restates configuration that reads plainly        | 22    |
| A decision record                                         | 21    |
| A test that does not exist yet                            | 18    |
| A comment at the implementation                           | 13    |
| A README                                                  | 2     |
| None of the above                                         | 3     |

### Rationale

| Measure                                                | Count |
| ------------------------------------------------------ | ----- |
| Entries                                                | 189   |
| Name what was rejected and why                         | 171   |
| Still match the code                                   | 184   |
| Contradicted by the code                               | 4     |
| Would stand as a decision record a new developer needs | 151   |

The four contradicted entries are `agent-file-discovery` "Agent metadata is a
colocated file with one key per consumer" (no implementation exists),
`claude-remote-control` "Session mode resumes one pinned conversation per
volume" (names a volume no descriptor declares), `iwe-workflow-skills` "Revision
and spec synchronization belong to Plan and Ship" (Explore, Implement, and Setup
also write specs), and `self-improve-learning-loop` "The plugin lives in this
repository as a second catalog plugin" (the plugin is enabled by default).

### Requirements that are not fully true

In 17 the spec is behind the code or says more than the code was built to do:

- `agentdev-runtime-images`: "the base image is lifecycle-neutral" (no default
  policy is installed in the base), "lifecycle phases remain distinct" (the
  create phase runs under PID 1's supervisor, as another requirement of the same
  spec says).
- `ai-review-gate`: "the responder only acts for authorized same-repository
  requests" (`.github/workflows/ai-responder.yml#jobs.trusted-bot-approval`
  checks no actor permission).
- `catalog-lifecycle`: "standalone startup selects and reconciles the runtime
  catalog"
  (`py_packages/agentdev_runtime/agentdev_runtime/workspace.py::Workspace.catalog`
  reinstalls on every start).
- `ci-python-environment`: "one action provisions the environment and activates
  nothing" (the `macos-bootstrap` job does not use the action).
- `claude-remote-control`: "Remote Control autostarts only on a live claude.ai
  login" (omits the Dev Container's supervised watcher), "every container
  pre-approves first-run Claude state" (the symlink it names is removed first).
- `iwe-workflow-skills`: "Plans express spec impact at risk-appropriate
  fidelity" (two of its scenarios disagree), "Plans record intent, not the path
  taken to it" (omits two destinations the implementer rulebook uses), "Workflow
  improvements preserve the IWE and OKF model" (archived architecture notes are
  outside the `okf` schema).
- `plan-checkbox-evidence`: "Plans record narrative verification evidence" (the
  implementer rulebook never names the section), "The checkbox format is
  mechanically gated" (the gate reads `data/plans/` only, and closed plans live
  in the archive).
- `pre-commit-gate`: "every hook runs a tool from one version owner" (the
  `link-venv` hook runs an image binary).
- `self-improve-learning-loop`: "The plugin is published but not enabled by
  default" (the image stages it and
  `py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py::created` installs
  it; the test
  `py_packages/agentdev_runtime/tests/test_attach_catalog_scope.py::test_attach_installs_the_checkout_catalog_at_user_scope`
  asserts that).
- `standalone-opencode-runtime`: "state survives replacement without
  cross-project session sharing" (no credential link exists to repair),
  "services have supervised bounded recovery" (two further non-zero exits),
  "runtime state is reported, persisted, and retried explicitly"
  (`py_packages/agentdev_runtime/agentdev_runtime/health.py::status` prints only
  failed and blocked components).

In 16 the spec states a guarantee the implementation does not deliver, and no
test fails:

- `agentdev-runtime-images` "the runtime is one CLI installed as a uv tool": two
  dependencies in
  `py_packages/agentdev_runtime/pyproject.toml#project.dependencies` are ranges.
- `firewall` "enabled firewall default-DROPs IPv4 and blocks IPv6 entirely":
  `py_packages/agentdev_runtime/agentdev_runtime/firewall.py::block_ipv6` leaves
  IPv6 open when `ip6tables` is missing.
- `pre-commit-gate` "every commit path runs the hooks, merges included":
  `end-of-file-fixer` and `trailing-whitespace` in `.pre-commit-config.yaml`
  omit the `pre-merge-commit` stage.
- `image-pinning` "published tags name only tested images": the `ubuntu-ansible`
  image is built without the revision label the promote guard reads.
- `standalone-opencode-runtime` "startup prepares or reuses one workspace":
  `py_packages/agentdev_runtime/agentdev_runtime/git.py::credential_helper` runs
  only from
  `py_packages/agentdev_runtime/agentdev_runtime/workspace.py::Workspace.clone`,
  so a reused checkout gets no helper.
- `devcontainer-git-credentials` "HTTPS git uses the gh login":
  `py_packages/agentdev_runtime/agentdev_runtime/coder.py::start` does not wait
  for the keyring session.
- `devcontainer-state` "the home volume starts empty and the bootstrap claims
  it": the `fish_setup` role writes `dev.fish` into the build user's home.
- `devcontainer-state` "root-only tests run through a launcher": the
  unmarked-test guard cannot fire, because `scripts/run-root-tests` deselects
  unmarked tests first.
- `dependency-updates` "derived files are regenerated with the bump":
  `.github/renovate.json#postUpgradeTasks.fileFilters` omits
  `py_packages/agentdev_runtime/uv.lock`.
- `line-free-anchors` "Live anchors resolve": bare paths are not checked, as
  [bare-path-anchors](../backlog/bare-path-anchors.md) records.
- `catalog-scripts` "command lines handed to a shell are quoted by bash_quote":
  one hint in
  `.agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.py`
  interpolates the remote name unquoted.
- `self-improve-learning-loop` "The mutator enforces a normative path
  allowlist": `.agents/plugins/self-improve/selfimprove/allowlist.py::_kind_of`
  accepts a rule at any depth.
- `git-new-branch` "The git-commit skill never commits on the default branch":
  the detached-`HEAD` refusal names no skill.
- `template-consumption` "publisher-only source never survives adoption", "every
  template path has one class", "a retained custom-image bundle builds from an
  explicit choice":
  `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`
  lags the template tree in each.

The one requirement not checkable from the repository is `stacked-prs` "Merges
into dependent branches are blocked", the desired state of a GitHub ruleset.

### Requirements whose only statement is the spec

Eighteen describe executable behaviour no test covers:

- `ai-review-gate`: "PRs are blocked until an AI review exists", "the responder
  only acts for authorized same-repository requests", "a review runs on first
  push and on explicit request", "trusted-bot pull requests are approved without
  an AI review". All four are inline JavaScript in workflow YAML;
  [test-responder-workflow-js](../backlog/test-responder-workflow-js.md) records
  the gap.
- `agentdev-runtime-images`: "image builds contact no Launchpad host", "gh
  resolves to the image's wrapper", "the bootstrap trusts an extra CA bundle".
- `catalog-lifecycle`: "the catalog is installed at image build time and again
  by postCreateCommand", "registering a catalog root replaces earlier
  registrations".
- `agent-file-discovery` "Git failures do not abort discovery".
- `catalog-scripts` "catalog scripts are standard-library Python".
- `devcontainer-docker-storage` "the host-side init runs without HOME".
- `devcontainer-git-credentials` "gh authenticates from the git credential
  helper".
- `devcontainer-state` "the create phase re-owns the sibling checkout volume".
- `image-pinning` "published tags name only tested images".
- `pre-commit-gate` "every commit path runs the hooks, merges included".
- `standalone-opencode-runtime` "startup prepares or reuses one workspace".
- `update-branch` "update-branch brings in the branch's upstream before the
  base".

Three fit no destination: the `stacked-prs` ruleset requirement, and
`template-consumption` "publisher-only source never survives adoption" and
"every template path has one class", which are completeness criteria for a prose
guide that `AGENTS.md#tests` allows no test to check.

### How the specs are used and kept

- Code points at specs for its reasons. About 60 comments and docstrings outside
  tests cite a spec by key, as `AGENTS.md#comments` rule 3 requires, and most
  give no reason of their own. No skill or agent definition depends on reading
  any one spec; the readers are `iwe-verifier`, `iwe-shipper`, and
  `iwe-ship-reviewer`, which read the specs a plan names.
- Specs follow the code about one time in five. Of 736 commits that changed a
  file a spec lists under `sources`, dependency bumps excluded, 134 also changed
  that spec.
- 119 of the 755 commits since the first spec touched `data/spec/`.
- `iwe-workflow-skills` is 1,931 lines describing 2,302 lines of rulebook.
- 126 plans carry `## Spec changes`: 104 as a linked spec and outcome, 16 as
  `None`, 5 as a delta.
- The specs define or lean on about 230 project terms. No glossary exists.

### Per spec

| Spec                           | Requirements | Not fully true | No executable check | Deletable as is | Needs a test first | Rationale entries worth a decision record |
| ------------------------------ | ------------ | -------------- | ------------------- | --------------- | ------------------ | ----------------------------------------- |
| `agent-file-discovery`         | 8            | 0              | 0                   | 6               | 1                  | 2 of 4                                    |
| `agentdev-runtime-images`      | 21           | 3              | 3                   | 14              | 3                  | 11 of 15                                  |
| `ai-review-gate`               | 8            | 1              | 8                   | 1               | 4                  | 6 of 7                                    |
| `ai-review-refresh`            | 3            | 0              | 2                   | 3               | 0                  | 4 of 4                                    |
| `catalog-lifecycle`            | 9            | 1              | 0                   | 6               | 2                  | 4 of 4                                    |
| `catalog-scripts`              | 6            | 1              | 1                   | 5               | 1                  | 2 of 3                                    |
| `ci-python-environment`        | 2            | 1              | 2                   | 2               | 0                  | 1 of 2                                    |
| `ci-workflows`                 | 3            | 0              | 1                   | 1               | 0                  | 3 of 3                                    |
| `claude-remote-control`        | 7            | 2              | 1                   | 6               | 0                  | 6 of 9                                    |
| `cloud-session-host`           | 4            | 0              | 1                   | 4               | 0                  | 2 of 2                                    |
| `coder-ide-baseline`           | 2            | 0              | 0                   | 0               | 0                  | 0 of 1                                    |
| `dependency-updates`           | 6            | 1              | 4                   | 2               | 0                  | 5 of 6                                    |
| `devcontainer-docker-storage`  | 5            | 0              | 1                   | 3               | 1                  | 2 of 2                                    |
| `devcontainer-git-credentials` | 4            | 1              | 3                   | 1               | 1                  | 2 of 2                                    |
| `devcontainer-opencode-policy` | 2            | 0              | 0                   | 1               | 0                  | 2 of 2                                    |
| `devcontainer-state`           | 6            | 2              | 2                   | 5               | 1                  | 4 of 4                                    |
| `firewall`                     | 3            | 1              | 0                   | 3               | 0                  | 1 of 1                                    |
| `git-new-branch`               | 6            | 1              | 0                   | 6               | 0                  | 1 of 2                                    |
| `image-pinning`                | 8            | 1              | 7                   | 7               | 1                  | 5 of 5                                    |
| `iwe-bootstrap`                | 3            | 0              | 0                   | 3               | 0                  | 0 of 1                                    |
| `iwe-branch-name`              | 4            | 0              | 0                   | 4               | 0                  | 2 of 3                                    |
| `iwe-workflow-skills`          | 31           | 3              | 11                  | 28              | 0                  | 26 of 34                                  |
| `line-free-anchors`            | 3            | 1              | 0                   | 3               | 0                  | 1 of 1                                    |
| `macos-native-bootstrap`       | 6            | 0              | 0                   | 5               | 0                  | 1 of 2                                    |
| `nested-agent-dispatch`        | 2            | 0              | 1                   | 2               | 0                  | 2 of 2                                    |
| `opencode-catalog-bridge`      | 8            | 0              | 0                   | 7               | 0                  | 7 of 8                                    |
| `opencode-web`                 | 3            | 0              | 0                   | 2               | 0                  | 2 of 5                                    |
| `plan-checkbox-evidence`       | 5            | 2              | 3                   | 5               | 0                  | 3 of 4                                    |
| `playwright-browser`           | 2            | 0              | 1                   | 1               | 0                  | 2 of 3                                    |
| `pr-description`               | 3            | 0              | 3                   | 3               | 0                  | 2 of 2                                    |
| `pr-merge-conflicts`           | 3            | 0              | 2                   | 3               | 0                  | 1 of 2                                    |
| `pr-review`                    | 5            | 0              | 5                   | 5               | 0                  | 4 of 4                                    |
| `pre-commit-gate`              | 10           | 2              | 2                   | 8               | 1                  | 6 of 8                                    |
| `self-improve-learning-loop`   | 16           | 2              | 2                   | 15              | 0                  | 4 of 5                                    |
| `stacked-prs`                  | 9            | 1              | 5                   | 8               | 0                  | 1 of 1                                    |
| `standalone-opencode-runtime`  | 10           | 4              | 0                   | 8               | 1                  | 11 of 12                                  |
| `supported-harnesses`          | 3            | 0              | 0                   | 1               | 0                  | 1 of 1                                    |
| `template-consumption`         | 21           | 3              | 13                  | 18              | 0                  | 10 of 11                                  |
| `update-branch`                | 2            | 0              | 0                   | 1               | 1                  | 1 of 1                                    |
| `xpra-port-forwarding`         | 2            | 0              | 1                   | 1               | 0                  | 1 of 1                                    |
| **Total**                      | 264          | 34             | 85                  | 207             | 18                 | 151 of 189                                |

## What is known

- **Four requirements in five can be deleted with nothing written in their
  place.** 207 of 264 repeat a test, a rulebook, or configuration that reads
  plainly.
- **The rationale is the content found nowhere else.** 151 entries would each
  stand as a decision record, and 97% still match the code.
- **A spec cannot be trusted without checking the code.** Half the specs hold a
  statement that is not fully true, one day after a consolidation pass.
- **A spec says more than the tests do, and nothing reads the difference.** The
  16 undelivered guarantees were visible only by comparing spec to code, and
  they stood until this comparison. Ship-time Verify reads the specs a plan
  names, not the rest.
- **A requirement about a rulebook is a second copy of the rulebook.** 58
  requirements describe prose an agent follows, and 5% of their scenarios have a
  test, because `AGENTS.md#tests` forbids tests that read text or drive an agent
  session. The spec is the only thing `iwe-verifier` checks a rulebook edit
  against.
- **Workflow YAML is the executable code with the least cover.** 7% of its
  scenarios have a test, and five of the 18 untested contracts are there.
- **Four kinds of content have no home in code, tests, decision records, or a
  glossary as proposed:**
  - facts about third-party systems the code depends on (Renovate, Claude Code,
    OpenCode, GitHub), which go stale with the third party and not with a
    decision;
  - deliberate absences and accepted limits ("no `openssh-server`", "nothing
    authenticates who typed a message");
  - configuration held outside the repository (rulesets, the review
    environment's secrets);
  - acceptance criteria for a prose procedure.
- **Other parts of the repository assume specs exist:** `AGENTS.md#comments`
  rule 3 and the comments written under it; a plan's `## Spec changes`;
  `iwe-verifier`'s effective contract; `iwe-shipper` steps for spec merge,
  rationale distillation, and the release page written from the spec diff; three
  of the items in `scripts/check-ship-records.py::SHIP_REVIEW_ITEMS`;
  `.iwe/schemas/spec.yaml`; the `iwe-setup` skill; and the `iwe-bootstrap`
  assets every template consumer receives. Seven requirements of
  `iwe-workflow-skills` have no subject once `data/spec/` is gone.
- **A decision registry was retired one commit earlier.** `05a5aa7d` folded
  `data/architecture/` into `## Rationale`, and the `iwe-workflow-skills` entry
  "Each kind of knowledge has one home, and finished work is archived by
  release" lists "`data/architecture/` kept for decisions only" as rejected,
  because no script can check that a note states no behaviour and no workflow
  step maintains a note.

## Eliminated

- **Specs are mostly wrong.** Eliminated: 87% of requirements and 97% of
  rationale entries match the code.
- **Deleting specs loses the statement of behaviour.** Eliminated for 207 of 264
  requirements, which a test, a rulebook, or the configuration already states.
- **Tests already cover what the specs promise.** Eliminated: 18 requirements
  have no test, and 16 state a guarantee the code does not deliver while every
  test passes.
- **The spec process keeps specs true.** Eliminated: 18% of commits to a spec's
  source files touch the spec, and half the specs hold a wrong statement.
- **Code, tests, decision records, and a glossary carry everything.** Eliminated
  by the four kinds of content listed above.

## What would settle the rest

- Whether a decision record stays true without upkeep. The four contradicted
  rationale entries were all edited in place as "the decision in force"; a
  record that is superseded by a new record and never edited has nothing to keep
  current. Counting the contradicted entries again after a release under each
  rule answers it.
- Whether `iwe-verifier` finds rulebook defects without a spec to compare
  against. Running it on one rulebook plan with only the plan's own scenarios as
  the contract answers it.
- What the release cut reads in place of the spec diff. Writing one release page
  from the release's decision records and closed bugs shows whether that input
  is enough.

## Closing

The measurement supports deleting the requirements and keeping the rationale,
which is the repository owner's proposal, on four conditions it makes concrete:

- each of the 18 untested contracts gets a test or a recorded decision that it
  goes unstated;
- the 151 rationale entries move to decision records before the specs are
  deleted, and `AGENTS.md#comments` rule 3 and the comments under it point at
  them;
- the decision-record format has a place for third-party facts, deliberate
  absences, and accepted limits, and repository settings get a page of their
  own;
- the workflow rulebooks, `scripts/check-ship-records.py`, and the
  `iwe-bootstrap` assets stop assuming `data/spec/`.

The 16 undelivered guarantees are defects or wording to settle whether or not
the specs go. This finding closes when the plan for [Shrink the knowledge base
to an issue tracker and decision
records](../backlog/shrink-knowledge-base-to-issues-and-adrs.md) is written, or
when the repository owner decides to keep the specs.
