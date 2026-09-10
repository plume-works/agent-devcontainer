---
type: plan
created: 2026-09-09
description: Merge the agent-self-improvement repository into this one as a second catalog plugin, published but not enabled.
generated:
  by: claude-code/opus-5
  at: 2026-09-09T00:00:00Z
sources:
- resource: https://github.com/plume-works/agent-self-improvement
  title: agent-self-improvement at e94031a, the merge source
stage: done
completed: 2026-09-09
---

# Consolidate the self-improve plugin into this repository

## Context

`self-improve` — a hook-driven experiential-learning engine for Claude Code — is
developed in its own repository and consumes this one's catalog. The
consolidation decision, its rationale, and its rejected alternatives are
recorded in
[Self-improve consolidation](../architecture/self-improve-consolidation.md);
this plan executes it and does not restate it.

The merge source is `plume-works/agent-self-improvement` at `e94031a`: roughly
3.5k lines of standard-library-only Python under `plugin/selfimprove/`, a
shell-plus-Python dispatcher, seven hook events, four skills, a reviewer prompt
and schema, 7.6k lines of tests, and 8.4k lines of documentation.

## Approach

The plugin tree moves to `.agents/plugins/self-improve/` and is published from
the Claude marketplace only. Its Python is aligned to this repository's
interpreter floor while its standard-library-only runtime rule is preserved
intact — the two are independent, and only the second is load-bearing.

Installation comes first: the catalog publishes one plugin today, and until a
second one installs, nothing else in this plan can be verified. Documentation
conversion comes last, when the code it describes is in place.

The rejected alternative was to align the interpreter floor by keeping the
plugin's own `pyproject.toml` and test suite fully separate, as
`py_packages/validate_agent_files/` does. That isolation exists because the
validator is released independently; `self-improve` is not, so a second Python
project would add packaging surface for no reciprocal guarantee.

## Implementation Steps

### Task 1: Publish a second plugin from the Claude marketplace

**Files:** Modify: `.claude-plugin/marketplace.json`,
`.devcontainer/scripts/reinstall-agentdev-claude.sh`

- [x] Add a `self-improve` entry to `.claude-plugin/marketplace.json` pointing
  at `./.agents/plugins/self-improve`, leaving
  `.agents/plugins/marketplace.json` untouched.
  - **Evidence:** commit `a229d43`; `jq -er '.plugins[].name'` on the Claude
    manifest yields `agentdev` and `self-improve`, on the Codex manifest
    `agentdev` alone.
- [x] Replace the single `jq -er '.plugins[0].name'` read in
  `reinstall-agentdev-claude.sh` with an iteration over `.plugins[]`, so every
  published plugin is uninstalled across the `user`, `project`, and `local`
  scopes and reinstalled at the requested scope.
  - **Evidence:** commit `a229d43`; driven against a stub `claude` on `PATH`,
    the script issued six uninstalls — `agentdev` and `self-improve` across
    `user`, `project`, and `local` — then one `marketplace add` and one install
    per plugin at the requested scope. `shellcheck` clean.
- [x] Record in `reinstall-agentdev-codex.sh` why its `.plugins[0]` read stays:
  the Codex manifest publishes one plugin by design, and a comment is cheaper
  than speculative generality that no caller exercises.
  - **Evidence:** commit `a229d43`; the three-line comment sits above the
    `.plugins[0].name` read at `reinstall-agentdev-codex.sh:26`. `shellcheck`
    clean.

### Task 2: Move the plugin tree

**Files:** Create: `.agents/plugins/self-improve/**`

- [x] Copy `plugin/` from the merge source to `.agents/plugins/self-improve/`,
  preserving `selfimprove/`, `scripts/`, `hooks/`, `reviewer/`, `skills/`, and
  `.claude-plugin/plugin.json`.
  - **Evidence:** commit `a079323`; copied from the source's tracked files at
    `e94031a`, so no build residue crossed. Every copied file is byte-identical
    to its source under `cmp`, the layout diff is empty, and `scripts/si` keeps
    its executable bit.
- [x] Move the source's `tests/` to `.agents/plugins/self-improve/tests/`,
  matching the convention `.agents/plugins/agentdev/tests/` sets.
  - **Evidence:** commit `a079323`; `unit/`, `integration/`, `smoke/`, and
    `fixtures/` land under the plugin's own `tests/`. 75 files copied against 75
    tracked in the source's `plugin` and `tests` trees.
- [x] Merge the runtime-state entries from the source's `.gitignore` into the
  root `.gitignore`: `.self-improvement/`, `candidates/`, `proposals/`,
  `authorizations/`, `backups/`, `archive/`, `locks/`, `*.sqlite*`, and
  `/test-runs/`, which is where live runs land.
  - **Evidence:** commit `a079323`; each entry confirmed present by exact-match
    grep. `git ls-files | git check-ignore --stdin` reports no tracked file
    shadowed by the added patterns.

### Task 3: Guard the live tests at collection

**Files:** Create: `.agents/plugins/self-improve/tests/conftest.py` (modify the
moved file); Modify: `pyproject.toml`

- [x] Add a `pytest_collection_modifyitems` hook that skips items marked `smoke`
  or `pty` unless an opt-in environment variable is set, attaching a reason to
  each skip. Leave `harness` unguarded — it is the model-free self-check that
  runs in the ordinary suite.
  - **Evidence:** commit `c4bdc2e`; the hook in
    `.agents/plugins/self-improve/tests/conftest.py` skips on `smoke` or `pty`
    unless `SELF_IMPROVE_RUN_LIVE` is set, naming every matching marker in the
    reason. It reads `iter_markers`, not `keywords`, which also carries path
    components and would have caught every test under `tests/smoke/` whatever
    its markers. With the variable set, `--collect-only -m "smoke or pty"`
    collects all 13 live tests, so the guard skips rather than deselects.
    `make test-harness` runs its 10 tests unguarded and passes.
- [x] Add the plugin's `tests` directory to `testpaths` in the root
  `pyproject.toml`, and carry over the `smoke`, `interactive`, `pty`, `harness`,
  and `auto_memory` marker declarations.
  - **Evidence:** commit `c4bdc2e`; `.agents/plugins/self-improve/tests` joins
    `testpaths`, and all five markers are declared, their descriptions restated
    against the new opt-in variable rather than the source's `make` targets. The
    suite collects 566 tests from the new path.
- [x] Prove the guard holds for the three bypasses a marker filter does not
  cover: selecting a live test by path, by `-m`, and by node id.
  - **Evidence:** commit `c4bdc2e`; each selection skipped rather than ran, and
    reported its reason under `-rs`. By path, `tests/smoke/test_smoke.py` — 10
    skipped. By marker, `-m smoke` — 10 skipped; `-m pty` — 3 skipped. By node
    id, `test_wake_pty.py::test_the_async_wake_arrives_at_an_idle_session` — 1
    skipped, reason `live test marked smoke, pty spends model usage`.

### Task 4: Align the interpreter floor

**Files:** Modify: `.agents/plugins/self-improve/scripts/si`,
`.agents/plugins/self-improve/tests/unit/test_no_runtime_deps.py`; Delete: the
merge source's `pyproject.toml`, `.ruff.toml`, `uv.lock`

- [x] Raise the dispatcher's `min_check` from `(3, 9)` to `(3, 12)`, keeping the
  interpreter probe loop. Hooks inherit the user's shell environment, where
  `python3` may resolve to an interpreter older than the runtime needs; the
  probe is what finds a usable one.
  - **Evidence:** commit `ffe833d`; the probe loop stays, with `python3.11`,
    `python3.10`, and `python3.9` dropped from the candidate list — below the
    new floor they could only ever fail `min_check`. `self_test`'s own floor
    moved with it, since it guards the path that bypasses the shim.
    `scripts/si self-test` reports `ok (python 3.12.3)`; `shellcheck` clean.
- [x] Delete `POST_39_STDLIB` and both `skipif sys.version_info < (3, 10)`
  guards from `test_no_runtime_deps.py`, so the standard-library-only assertions
  run unconditionally.
  - **Evidence:** commit `ffe833d`; the set, both `skipif` guards, and the
    `test_runtime_avoids_post_39_stdlib` test they guarded are gone — the floor
    is 3.12, so no standard-library module is out of reach. The remaining AST
    assertion runs unconditionally over all 22 runtime modules and passes. The
    walk now excludes `tests/`, which the move brought under the plugin root and
    which imports pytest by design.
- [x] Drop the source's `pyproject.toml`, its `[tool.ruff]` block with the
  `UP006`/`UP007`/`UP035` ignores, and its `.ruff.toml`; the root `.ruff.toml`
  governs the whole tree, so the plugin needs no ruff config of its own.
  - **Evidence:** commit `ffe833d`; none of the three crossed in the first place
    — Task 2 copied only `plugin/` and `tests/` — and none exists under
    `.agents/plugins/self-improve/`. The root config governs: `ruff check` and
    `ruff format --check` pass over all 63 files of the tree. A `# noqa: UP036`
    left over from the source's ignore list went with them, the root config
    selecting no `UP` rules.
- [x] Decide the fate of `test_project_declares_no_runtime_dependencies`, which
  asserts the literal string `dependencies = []` in `pyproject.toml`. The root
  file has a populated dev group, so the assertion cannot hold in its current
  form, and the AST walk beside it already enforces the real property. Either
  restate it against the plugin or remove it; record which and why.
  - **Evidence:** commit `ffe833d`; **removed**. The assertion was a proxy for
    the real rule, and the plugin it now guards declares no `pyproject.toml` of
    its own to restate it against — the plugin ships as a directory in the
    catalog, not as a Python distribution. Restating it against the root file
    would assert something false: the root legitimately declares a dev group.
    The property that matters is enforced directly by the AST walk beside it,
    which reads every runtime import rather than trusting a manifest to describe
    them.

### Task 5: Bring the Makefile

**Files:** Create: `Makefile`

- [x] Copy the source Makefile to the repository root with every explanatory
  comment intact, and the `smoke`, `smoke-auto`, `wake`, `wake-memory`,
  `wake-repeat`, and `test-harness` targets, the help text, the `SMOKE_MODEL` /
  `SMOKE_EFFORT` / `SMOKE_AUTO_MEMORY` dials, `TEST_RUN_LABEL`, and
  `unexport VIRTUAL_ENV` unchanged.
  - **Evidence:** commit `4e3b16a`; all six targets resolve under `make -n`, the
    three dials and both exports carry over verbatim, and every explanatory
    comment is preserved.
- [x] Set the live targets' opt-in environment variable from Task 3, and drop
  `-m "not smoke and not pty"` from `test`, which the collection hook now covers
  at every entry point.
  - **Evidence:** commit `4e3b16a`; `make -n` shows `SELF_IMPROVE_RUN_LIVE=1` on
    each of `smoke`, `smoke-auto`, `wake`, `wake-memory`, and `wake-repeat`, and
    on neither `test` nor `test-harness`. `make test` is a bare `pytest -q` and
    runs 825 passed, 14 skipped, spending no model usage.
- [x] Remove the `lint` and `fmt` targets, reduce `check` to `test validate`,
  and drop their help lines. Formatting is pre-commit's, per
  [Let pre-commit own formatting](20260831-pre-commit-owns-formatting.md);
  `ruff` stays in the dev group because the pre-commit hook needs it.
  - **Evidence:** commit `4e3b16a`; `make -n lint` and `make -n fmt` both fail
    with no such target, `check` is `test validate`, and the help text points at
    `pre-commit run --all-files` instead.
- [x] Retarget `validate` at `.agents/plugins/self-improve`, keeping its second
  invocation, which now validates a two-plugin marketplace.
  - **Evidence:** commit `4e3b16a`; `make validate` passes both — the plugin
    manifest at `.agents/plugins/self-improve/.claude-plugin/plugin.json` and
    the marketplace manifest now publishing two plugins.
- [x] Scope `clean` to the plugin subtree rather than the repository root, and
  fix `clean-claude`'s module path, which assumes a top-level `tests` package
  and would now collide with the agentdev suite.
  - **Evidence:** commit `4e3b16a`; `clean` removes only caches under
    `.agents/plugins/self-improve` plus `test-runs/`, leaving the other suites'
    caches alone. `clean-claude` runs `python -m tests.smoke.workspaces` from
    the plugin directory, where `tests` is its own package — from the repository
    root the name does not resolve at all. `make clean-claude` reports
    `removed 0 test-run project directories`.
- [x] Replace the missing-`uv` hint with this repository's escalation ladder
  (`AGENTS.md` Best Practice 3) instead of a `brew install` suggestion.
  - **Evidence:** commit `4e3b16a`; the no-`uv` branch names the ladder —
    devcontainer via `/agentdev:microvm-sandbox` with a Docker daemon, a
    Codespace via `/agentdev:remote-codespace-session` without one — and no
    longer suggests `brew install`.

### Task 6: Land the research material

**Files:** Create: `docs/research/**`

- [x] Move the source's `docs/case-study/` and `docs/hypothetical-extensions/`
  under `docs/research/` as a plain folder. It analyses other projects' learning
  systems and asserts nothing about this one, so it is not graph material.
  - **Evidence:** commit `5a48d8c`; all 33 tracked files copied. It stays out of
    the graph — the iwe library path is `docs/knowledge`, and
    `iwe schema validate` passes without claiming any of it. Seven links that
    pointed at the source's `docs/specs/` now resolve to the graph documents
    that replaced it; a link check over the tree reports none broken.

### Task 7: Extract the implemented specification into the graph

**Files:** Create: `docs/knowledge/data/plans/20260909-self-improve-mvp.md`,
`docs/knowledge/data/spec/self-improve-learning-loop.md`,
`docs/knowledge/data/architecture/self-improve-runtime.md`; Modify:
`docs/knowledge/data/plans.md`, `docs/knowledge/data/spec.md`,
`docs/knowledge/data/architecture.md`

- [x] File the MVP as a plan at `stage: done`, absorbing the pty wake harness
  specification, whose acceptance criterion 6.1 is **outstanding**: nine of ten
  runs reached the assertion, and five of twenty checks skipped for want of a
  staged candidate. Per
  [Evidence and outstanding work](../concept/evidence-and-outstanding-work.md),
  that belongs under its own heading and never beside the evidence.
  - **Evidence:** commit `5a48d8c`; `data/plans/20260909-self-improve-mvp` is
    filed `stage: done` with `completed: 2026-08-02` and listed under `## Done`.
    Criterion 6.1 sits under its own `## Outstanding work` heading, naming what
    closing it costs, with no ticked task's evidence line claiming it.
- [x] Write the durable behavior into `data/spec/`: hook design, the
  meaningful-event gate, reviewer isolation and output, routing and the path
  allowlist, the mutation protocol, state and privacy, and failure behavior.
  - **Evidence:** commit `5a48d8c`; `data/spec/self-improve-learning-loop`
    carries all nine areas as Requirement/Scenario pairs and is linked from
    `data/spec.md`. Transcription only — no requirement added, modified, or
    removed against the behavior as it arrived.
- [x] Write the runtime decisions and their rejected alternatives into
  `data/architecture/`, including the standard-library-only rule and the
  state-root resolution order.
  - **Evidence:** commit `5a48d8c`; `data/architecture/self-improve-runtime`
    records the stdlib-only rule against the `security-guidance` alternative,
    the state-root order and why the override precedes `CLAUDE_PLUGIN_DATA`, the
    single dispatcher, isolation by tool removal rather than an allowlist, the
    effort variable over the `--effort` flag, and why the wake needs a pty.

### Task 8: File the unimplemented proposals and the measured defects

**Files:** Create: `docs/knowledge/data/someday/*.md`,
`docs/knowledge/data/bugs/*.md`; Modify: `docs/knowledge/data/someday.md`,
`docs/knowledge/data/bugs.md`

- [x] File Codex integration, plugin execution tracing, and the Hermes-derived
  prompt stack under `data/someday/`, each keeping the analysis that makes it
  decidable later.
  - **Evidence:** commit `5a48d8c`; three documents linked from
    `data/someday.md`. Codex keeps the six named parity gaps and the every-layer
    dependency inventory; tracing keeps the shape-without-content design, the
    keyed-digest rule, the slice order, and why T4 onward stays behind a named
    hypothesis; the prompt stack keeps the adopt/adapt/refuse map and the recall
    thresholds acceptance would need.
- [x] File the reviewer decline asymmetry as a bug with its root cause openly
  unresolved: the reviewer declined seven times on the negative control against
  once on the wake check, on an identically scripted exchange; offline replay
  does not reproduce it; two hypotheses are eliminated.
  - **Evidence:** commit `5a48d8c`;
    `data/bugs/self-improve-reviewer-decline-asymmetry` carries the
    twenty-review table, the 3-in-101 replay result against 5-in-20 live, both
    eliminated hypotheses, the three that remain, and the three ways of closing
    it. Its `## Root cause` states plainly that no mechanism is identified.
- [x] File the `improve` skill's unstageable routing option as a bug. Its
  routing step 3 offers to add or patch a linked reference, and
  `candidate_paths` resolves only `CLAUDE.md`, `rules/<name>.md`, and
  `skills/<name>/SKILL.md`, so such a target is rejected as `bad_kind`.
  - **Evidence:** commit `5a48d8c`;
    `data/bugs/self-improve-unstageable-routing-option` records it against the
    code as it stands — `SKILL.md:60` offers the option, `allowlist.py:47`
    resolves three kinds, and `allowlist.py:76` raises `bad_kind` for everything
    else.

### Task 9: Merge the operating rules

**Files:** Modify:
`docs/knowledge/data/concept/evidence-and-outstanding-work.md`, `AGENTS.md`

- [x] Fold the source's evidence rule into the existing concept document as one
  idea rather than two: this repository's rule governs documents that conflate
  tenses, and the source's governs a session claiming what it did not watch
  happen — a specification whose checks have never passed is implemented but
  unverified.
  - **Evidence:** commit `798f944`; folded into
    `data/concept/evidence-and-outstanding-work` under the existing heading, as
    one idea — the closing paragraph names both sides as the same failure to
    distinguish being told something from being asked for something. No second
    heading and no second document; the `description` was widened to match.
- [x] Decide whether "new findings get their own specification" and "do not
  build instrumentation for a question nobody has framed" belong in `AGENTS.md`
  or in the plugin's own instructions, and place them once.
  - **Evidence:** commit `798f944`; both placed in `AGENTS.md`, under
    `## Project memory`. Neither is specific to the plugin: they govern how any
    finding in this workspace is recorded and when instrumentation may be built,
    and `AGENTS.md` is the file every agent loads. The routing half — which
    directory a finding lands in — was already covered by the implement skill
    and is not restated. The two documents Task 8 filed satisfy both rules.

### Task 10: Retire the merged repository's own scaffolding

**Files:** Delete: the merge source's duplicated configuration; Modify:
`uv.lock`

- [x] Drop the source's `.editorconfig`, `.hadolint.yaml`, `.markdownlint.yml`,
  `.prettierrc.yml`, `.shellcheckrc`, and `zizmor.yaml`; this repository's
  copies govern, and each source copy must be confirmed equivalent before it is
  dropped.
  - **Evidence:** commit `4fdfcd2`; all six confirmed byte-identical to this
    repository's copies under `diff` before being dropped, so nothing was lost.
    None was ever copied — Task 2 took only `plugin/` and `tests/`.
- [x] Reconcile the two `LICENSE` files, which differ, rather than deleting
  either unread.
  - **Evidence:** commit `4fdfcd2`; both read and diffed. They are the same MIT
    text differing in one line — `plume-works` against `Anton Matosov`. The
    repository `LICENSE` governs the whole checkout and stays as it is; the
    plugin keeps its own authorship in
    `.agents/plugins/self-improve/.claude-plugin/plugin.json`, which still
    declares `Anton Matosov` and `MIT`. Both facts survive and the terms are
    identical either way, so no root change was needed.
- [x] Drop the source's `.claude/settings.json`, which declares this repository
  as a remote marketplace — the relationship this merge inverts.
  - **Evidence:** commit `4fdfcd2`; read before dropping. It registered
    `plume-works/agent-devcontainer` as a github marketplace and enabled
    `agentdev@agent-devcontainer` — a consumer's configuration, meaningless now
    the catalog is this checkout. Never copied, and absent from the tree.
- [x] Decide whether the source's offline CI job needs an equivalent here, or
  whether the existing workflows already cover the new suite, and record which.
  - **Evidence:** commit `4fdfcd2`; **an equivalent was needed**. The existing
    workflows name each suite by path, so the moved tests ran in none of them —
    `validate-agent-files.yml` listed `py_packages` and the agentdev tests, and
    `ci.yml` the same two. The new suite joins both, beside the agentdev one.
    The source's job itself is not reproduced: it pinned `UV_PYTHON: '3.9'` to
    test the old interpreter floor, which Task 4 removed. The exact `ci.yml`
    invocation was run locally — 803 passed, 14 skipped, no live test collected.
- [x] Regenerate `uv.lock` through `.devcontainer/scripts/uv-sync.sh`.
  - **Evidence:** commit `4fdfcd2`; the script ran and resolved 60 packages with
    no change to `uv.lock`, the plugin adding no dependency — which is the
    standard-library-only rule holding. `uv lock --check` confirms the lockfile
    is consistent with `pyproject.toml`.

## Spec changes

This plan moves a working plugin between repositories and converts its
documentation; it changes no behavior of the code being moved.

Task 7 creates `data/spec/self-improve-learning-loop`, but as a *transcription*
of behavior that already shipped in the merge source, not as a change to it. The
requirements it will carry — hook design, the meaningful-event gate, reviewer
isolation and output, routing and the path allowlist, the mutation protocol,
state and privacy, and failure behavior — describe the plugin exactly as it
arrives. No requirement is added, modified, or removed by this plan.

The two defects filed in Task 8 are recorded, not fixed; the behavior they
describe is the behavior that ships.

## Verification

- `uv run pytest .agents/plugins/self-improve/tests` passes, and the run
  collects no live test.
- The live guard holds under each bypass a marker filter misses:
  `uv run pytest <path to a smoke test>`, `uv run pytest -m smoke`, and a
  node-id selection all skip rather than execute, each naming its reason.
- `uv run pytest` at the repository root passes across all four suites and
  spends no model usage.
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  exits 0 with the two-plugin Claude marketplace.
- `.devcontainer/scripts/reinstall-agentdev-claude.sh` installs both plugins;
  `claude plugin list` shows `agentdev` and `self-improve`, and a second run is
  idempotent.
- `claude plugin marketplace list` shows no stale entry after the reinstall.
- `.devcontainer/scripts/reinstall-agentdev-codex.sh` still installs `agentdev`
  alone and reports nothing about `self-improve`.
- `make test` and `make validate` pass; `make help` describes only targets that
  exist.
- `pre-commit run --all-files` passes.
- `iwe normalize` and `iwe schema validate` both exit 0.
- The plugin is published but not enabled: a session that has not opted in
  registers none of its hooks.

## Verification results

Run on 2026-09-09 at `ba78df0`. Every check passed except the last, which does
not hold as written.

- `uv run pytest .agents/plugins/self-improve/tests` — 574 passed, 14 skipped,
  no live test collected.
- The three bypasses all skip: by path, 10 skipped; `-m smoke`, 10 skipped;
  `-m pty`, 3 skipped; by node id, 1 skipped. Each names its reason.
- `uv run pytest` at the root — 825 passed, 14 skipped across all four suites,
  no model usage.
- `uv run validate_agent_files --recommend . --require-marketplace claude codex`
  — exit 0, 54/54 skills valid, both plugins seen.
- `reinstall-agentdev-claude.sh` installs both; `claude plugin list` shows
  `agentdev` and `self-improve`. A second run uninstalls both and reinstalls
  both.
- `claude plugin marketplace list` shows one `agent-devcontainer` entry, no
  stale name.
- `reinstall-agentdev-codex.sh` installs `agentdev` alone and mentions
  `self-improve` zero times.
- `make test` — 825 passed, 14 skipped. `make validate` passes both manifests.
  Every target `make help` names resolves.
- `pre-commit run --all-files` — every hook passed.
- `iwe normalize` and `iwe schema validate` both exit 0, with no broken links.

**The published-but-not-enabled check does not hold as stated.**
`claude plugin install` writes `enabledPlugins` for whatever it installs, so
after the reinstall script runs, a session in this checkout *does* register the
plugin's hooks. That enablement lives in the gitignored
`.claude/settings.local.json` — local working state, not a published default.
Nothing the repository ships enables it: the tracked `.claude/settings.json`
names it nowhere, and the Ansible role still stages `agentdev` alone, its
`selectattr` matching exactly one entry. The distinction is recorded in
[Self-improve consolidation](../architecture/self-improve-consolidation.md).

## Out of scope

- **Enabling the plugin.** It is published from the marketplace and nothing
  more. Staging it into `agent-desktop`, installing it at user scope, or
  enabling it by default is a separate decision with its own evidence bar.
- **Ansible staging changes.** The role selects its plugin by name and asserts
  exactly one match, so a second entry is invisible to it — which is what
  publishing-without-enabling requires.
- **Fixing either defect filed in Task 8.**
- **Codex support for `self-improve`**, which is unimplemented upstream and
  filed under `data/someday/` by Task 8.
- **Any behavioral change to the plugin**, including the reviewer prompt.

## Key references

Verified anchor points (line numbers as of 2026-09-09):

- `.devcontainer/scripts/reinstall-agentdev-claude.sh:27` — `plugin_name` read,
  the single-plugin assumption Task 1 removes
- `.devcontainer/scripts/reinstall-agentdev-codex.sh:26` — the same read, which
  stays
- `ansible/roles/agentic_tools/tasks/stage_catalog.yml:22` — `selectattr` name
  filter; selects rather than indexes, so a second plugin is invisible
- `ansible/roles/agentic_tools/tasks/stage_catalog.yml:31` — the assertion that
  exactly one entry matches that name
- `ansible/roles/agentic_tools/defaults/main.yml:41` —
  `agentic_tools_plugin_name`, the selector that filter uses
- `py_packages/validate_agent_files/validate_agent_files/paths.py:54` —
  `find_plugin_roots`, which already enumerates every published plugin
- `py_packages/validate_agent_files/validate_agent_files/validators/marketplace.py:73`
  — `_validate_ecosystem`, which validates each entry and skips an ecosystem a
  plugin does not ship for
- `.github/workflows/validate-agent-files.yml:85` — the CI invocation whose
  `--require-marketplace claude codex` the asymmetric manifests must satisfy
- `pyproject.toml:29` — `testpaths`, which Task 3 extends
