---
type: plan
description: Wire the two orphaned skill validators into the engine so --recommend produces recommendations, fix the flag plumbing, and remove the redundant --no-warnings flag.
created: 2026-09-07
generated:
  by: claude-code/opus-5
  at: 2026-09-08T01:12:06Z
sources:
- resource: py_packages/validate_agent_files/
stage: done
completed: 2026-09-08
---

# Connect validator warnings

## Context

[Validator warning visibility](../bugs/validator-warning-visibility.md) records
a defect with three breaks on one wire: `SkillFrontmatterValidator` and
`SkillStructureValidator` are never constructed by the engine, `--no-warnings`
writes an argparse destination nothing reads, and `CrossReferenceValidator`
stores `show_warnings` without consulting it. The net effect is that
`--recommend` produces no output of its own on any run.

This matters now because `README.md:358` and
`.github/workflows/validate-agent-files.yml:85` both instruct contributors to
run `--recommend`, so the repository advertises a skill-quality signal it does
not actually compute. The bug doc establishes the validators were never wired in
— they arrived orphaned in the initial extraction commit `c1dce21` — so this is
a first wiring with no prior decision to reverse.

## Approach

Construct both validators inside `ValidationEngine.validate`, alongside the
`UniquenessValidator` call that already has `frontmatter` and `body` in hand,
passing `self.show_warnings` through. Only their warning-level findings become
the recommendation set; their stricter error-level checks remain direct-library
behavior and do not extend the engine's validation contract.

Redesigning the recommendation set from scratch was rejected. It would only be
warranted by a reason to distrust the existing checks, and since they were never
connected, no one ever judged them insufficient.

For the flag surface, `--no-warnings` is removed rather than repaired. It and
`--errors-only` both resolve to the same `show_warnings = False` with no
distinct behavior, so keeping both would mean documenting a difference that does
not exist. `--no-warnings` is the one to drop: it is already inert, and no
executable caller in this repository passes it — the only occurrences are its
own definition, a comment, and prose in two knowledge docs.

## Implementation Steps

### Task 1: Wire the two skill validators into the engine

**Files:** Modify:
`py_packages/validate_agent_files/validate_agent_files/core.py`

Construct both validators in `ValidationEngine.validate`, after the
`UniquenessValidator` call at `core.py:116-119` where `frontmatter` and `body`
are already bound. Run them only when warnings are enabled and append only their
warning-level findings.

- [x] `SkillFrontmatterValidator().validate(frontmatter, show_warnings=True)`
  and `SkillStructureValidator().validate(body, show_warnings=True)` run when
  recommendations are enabled, with only their warning-level issues appended to
  the result
  - **Evidence:** commits `e53993a` and `53f0476`; the focused recommendation
    and direct-validator suites pass 36 tests, including the warning path and
    eight accepted-input compatibility cases

### Task 2: Cover the recommendation path with a CLI-level regression test

**Files:** Create:
`py_packages/validate_agent_files/tests/test_recommendations.py`

Assert against a fixture the test builds, never repository content. Import flag
names from the code under test per the package's `AGENTS.md`.

- [x] A skill whose description carries a vague term reports a warning under
  `--recommend` and reports nothing extra without it
  - **Evidence:** `tests/test_recommendations.py` —
    `test_recommend_flag_reports_skill_warnings` and
    `test_without_recommend_no_warnings_are_reported`; both fail against the
    pre-wiring `core.py` and pass after it
- [x] A fixture with warnings and no errors exits `0` both with and without
  `--recommend` — warnings never drive the exit code, per
  `ValidationResult.is_valid`
  - **Evidence:** `tests/test_recommendations.py` —
    `test_warnings_never_change_the_exit_code`, parametrised over both flag
    states; full isolated suite green at 158 passed

### Task 3: Remove `--no-warnings` and read real argparse destinations

**Files:** Modify:
`py_packages/validate_agent_files/validate_agent_files/cli.py`,
`py_packages/validate_agent_files/validate_agent_files/main.py`

Delete the `--no-warnings` argument at `cli.py:65-71`. In `main.py:19-24`, drop
the `no_warnings` lookup and read `parsed_args.recommend` and
`parsed_args.errors_only` as plain attributes — the parser always defines both,
so a `getattr` default would mask a destination rename instead of raising.

- [x] `--no-warnings` is gone from the parser and `--errors-only` remains the
  single suppression flag
  - **Evidence:** `tests/test_recommendations.py` —
    `test_parser_rejects_the_removed_no_warnings_flag`; the CLI exits `2` on
    `--no-warnings` rather than ignoring it
- [x] `main.py` reads `parsed_args.recommend` and `parsed_args.errors_only`
  directly, with no `getattr` default on either
  - **Evidence:** `main.py:20` — a single
    `parsed_args.recommend and not parsed_args.errors_only`; pinned by
    `test_parser_exposes_recommend_and_errors_only_destinations`, isolated suite
    green at 159 passed

### Task 4: Drop the dead `show_warnings` field from `CrossReferenceValidator`

**Files:** Modify:
`py_packages/validate_agent_files/validate_agent_files/validators/cross_reference.py`,
`py_packages/validate_agent_files/validate_agent_files/core.py`

The removed parameter was stored without being read. All skill, agent, and
prompt call sites now construct `CrossReferenceValidator` without it.

- [x] `CrossReferenceValidator.__init__` no longer accepts `show_warnings`, and
  the skill call site no longer passes it
  - **Evidence:** `show_warnings` no longer appears in `cross_reference.py`;
    isolated suite green at 159 passed

### Task 5: Reword the description that trips the new check

**Files:** Modify:
`.agents/plugins/agentdev/skills/sync-super-linter-tool-versions/SKILL.md`

Turning the frontmatter check on surfaces exactly one catalog finding: the
description's phrase `local lint tools` matches the vague term `tools`. Reword
that phrase so the catalog is clean under `--recommend`, keeping the skill's
discovery keywords intact.

- [x] The skill's description no longer trips the vague-term check, and
  `--recommend` over `.agents/` reports no warnings
  - **Evidence:** `uv run validate_agent_files --recommend .agents` reports
    41/41 valid with 0 warnings; the publisher gate
    (`--recommend . --require-marketplace claude codex`) reports 47/47 valid
    with 0 warnings

### Task 6: Update the CLI interface map document

**Files:** Modify:
`docs/knowledge/data/codebase/api-validate-agent-files-cli.md`

The invocation synopsis and flag prose both name `--no-warnings`, and the "How
it works" claim that `core.py` calls the per-file validators only becomes true
with Task 1.

- [x] The synopsis drops `--no-warnings`, the flag prose describes `--recommend`
  and `--errors-only` only, and `source_digest` plus `verified` are refreshed
  for the edited `cli.py`
  - **Evidence:** `stale-map-docs.py` reports
    `FRESH data/codebase/api-validate-agent-files-cli` after the edit, having
    reported `STALE` before it

## Spec changes

`data/spec/agent-file-discovery` is the closest existing spec and covers *which
files* are discovered, not what is reported about them; this work does not touch
discovery. No spec document currently states the validator's warning behavior.

Rather than create one for a flag surface that is already documented as an
interface, the intended behavior is recorded as a normative outcome against
[the CLI interface map](../codebase/api-validate-agent-files-cli.md):

`validate_agent_files` SHALL emit skill frontmatter and structure
recommendations as warning-level issues when `--recommend` is passed, SHALL
suppress them when `--errors-only` is passed, and SHALL NOT let warning-level
issues change the exit code, which stays driven by `ValidationResult.is_valid`.
`--no-warnings` SHALL NOT be accepted.

## Verification

From the package root, the isolated suite that proves the package carries no
dependency on this repository:

``` bash
cd py_packages/validate_agent_files && uv run --isolated --extra dev pytest
```

Then, from the repository root, against a scratch fixture under `.tmp/` — a
skill whose description carries a vague term and whose top-level section is
near-empty:

``` bash
uv run validate_agent_files .tmp/<fixture>
uv run validate_agent_files --recommend .tmp/<fixture>
uv run validate_agent_files --recommend --errors-only .tmp/<fixture>
```

The first and third must match and report no warnings; the second must report
the vague-description and short-section warnings and still exit `0`.

Confirm the removed flag is rejected rather than silently ignored:

``` bash
uv run validate_agent_files --no-warnings .tmp/<fixture>   # must exit 2
```

Finally, the publisher gate the repository depends on, which must stay green
with recommendations live:

``` bash
uv run validate_agent_files --recommend . --require-marketplace claude codex
```

## Verification results

All checks pass as of 2026-09-07, at commit `7333146`:

- Isolated package suite: 159 passed.
- The bare run and `--recommend --errors-only` produce byte-identical output
  with no warnings; `--recommend` reports both the vague-description and
  short-section warnings and still exits `0`.
- `--no-warnings` exits `2`.
- Publisher gate: 47/47 skills valid, 0 errors, 0 warnings.

The fixture must sit outside the work tree, not under `.tmp/`. Discovery skips
gitignored paths, so a `.tmp/` fixture reports
`contains no skills, agents, or prompts` and exercises nothing.

## Out of scope

- Adding new validators or new rules. This connects an existing path; it does
  not extend the rule set.
- Changing which files are discovered, or any `--mode`/`--require-marketplace`
  behavior.
- Triaging warnings in consuming repositories. Only this repository's catalog is
  in scope, and Task 5 covers its single finding.

## Key references

Verified anchor points (line numbers as of 2026-09-08):

- `py_packages/validate_agent_files/validate_agent_files/core.py:80` —
  `ValidationEngine`
- `py_packages/validate_agent_files/validate_agent_files/core.py:87` —
  `ValidationEngine.validate`, the wiring point
- `py_packages/validate_agent_files/validate_agent_files/core.py:116` —
  `UniquenessValidator` call, where `frontmatter` and `body` are bound
- `py_packages/validate_agent_files/validate_agent_files/core.py:121` —
  warning-only skill-validator gate
- `py_packages/validate_agent_files/validate_agent_files/core.py:290` —
  `ValidationEngine` construction from `CustomizationsValidationEngine`
- `py_packages/validate_agent_files/validate_agent_files/core.py:133,352,401` —
  skill, agent, and prompt `CrossReferenceValidator` sites
- `py_packages/validate_agent_files/validate_agent_files/cli.py:54` —
  `--recommend`
- `py_packages/validate_agent_files/validate_agent_files/cli.py:66` —
  `--errors-only`
- `py_packages/validate_agent_files/validate_agent_files/main.py:22` —
  `show_warnings` derivation
- `py_packages/validate_agent_files/validate_agent_files/validators/skill.py:11`
  — `SkillFrontmatterValidator`
- `py_packages/validate_agent_files/validate_agent_files/validators/skill.py:92`
  — vague-description check
- `py_packages/validate_agent_files/validate_agent_files/validators/skill.py:123`
  — `SkillStructureValidator`
- `py_packages/validate_agent_files/validate_agent_files/validators/skill.py:151`
  — short-section check
- `py_packages/validate_agent_files/validate_agent_files/validators/cross_reference.py:81`
  — the independent cross-reference warning path
- `py_packages/validate_agent_files/validate_agent_files/types.py:55` —
  `ValidationResult.is_valid`, error-only
