---
type: bug
description: validate_agent_files' --recommend, --no-warnings, and --errors-only flags have no effect on any run — the warning/recommendation path is entirely disconnected from the validation engine.
generated:
  by: claude-sonnet-5
  at: 2026-08-12T00:00:00Z
sources:
- resource: docs/agents/specs/validator-warning-visibility/ (folded and removed)
---

# Validator warning visibility

## Symptom

`validate_agent_files`' entire warning-and-recommendation path is inert.
`--recommend`, `--no-warnings`, and `--errors-only` change no observable output
on any run. `README.md` and `.github/workflows/validate-agent-files.yml` tell
contributors to run `--recommend`; it currently shows nothing extra, so the
repository believes it has a quality signal it does not have.

## Reproduction

A scratch skill carrying three of the vague description terms
`SkillFrontmatterValidator` looks for (`helpers`, `utilities`, `tools`) was
validated with and without `--recommend`. Output was byte-identical, and the
summary line read `Errors: 1, Warnings: 0` both times. The same comparison for
`--recommend` against `--recommend --no-warnings` over
`.agents/plugins/agentdev/skills` was also byte-identical.

``` bash
cd py_packages/validate_agent_files
uv run validate_agent_files <fixture>                              # no recommendations
uv run validate_agent_files --recommend <fixture>                  # recommendations, exit code unchanged
uv run validate_agent_files --recommend --no-warnings <fixture>    # suppressed again
```

The first and third runs match. The second should differ from both — today all
three are identical.

## Root cause

Three independent breaks sit on the same wire:

1. **`--recommend` cannot produce recommendations.** `show_warnings` is read in
   exactly two places: `SkillFrontmatterValidator.validate`
   (`validators/skill.py:91`, the vague-description check) and
   `SkillStructureValidator.validate` (`validators/skill.py:150`, the
   section-content check). Neither class is imported anywhere in the package
   outside its own module — the engine never reaches them. The tests that cover
   them construct the validators directly, masking the gap. This is the
   load-bearing break: not a flag that fails to disable output, but a feature
   that produces none.
2. **`--no-warnings` writes an attribute nothing reads.** `cli.py:65-71`
   declares the flag as `action='store_false', dest='warnings', default=True`,
   so argparse sets `args.warnings`. `main.py:23` reads
   `getattr(parsed_args, 'no_warnings', False)` — an attribute the parser never
   creates. The `getattr` default silently swallows the mismatch, so the branch
   is permanently `False`. (`--errors-only` on the same line is read correctly
   and is the only flag that reaches `show_warnings` at all — which, per (1) and
   (3), still changes nothing downstream.)
3. **`CrossReferenceValidator` stores `show_warnings` and never reads it.**
   `core.py:98` passes `show_warnings` into `CrossReferenceValidator`, which
   assigns `self.show_warnings` at `validators/cross_reference.py:44` and never
   consults it again — the only path by which `show_warnings` currently leaves
   the engine, terminating in a dead field.

Not investigated: whether the two orphaned validators were dropped from the
engine or never wired in. That question decides whether the fix is "restore the
call sites" or "design the recommendation set from scratch" — left open
deliberately.

## Fix

Not started. Decide first whether to **restore** (wire
`SkillFrontmatterValidator` and `SkillStructureValidator` into
`CustomizationsValidationEngine`, treating their existing checks as the intended
recommendation set — cheapest, and `tests/test_skill_validation.py` already
describes the behavior) or **redesign** (treat the two validators as abandoned
and define the recommendation set deliberately — more work, and should not
happen without a reason to distrust the existing checks). Trace the git history
of `validators/skill.py` and `core.py` first; that history is the deciding
evidence.

Fixing the `--no-warnings`/`args.no_warnings` attribute mismatch alone is not
worth shipping on its own — it would make the flag control a value that still
reaches nothing. Fix the wiring first, or fix all three together.

Acceptance criteria for the eventual fix:

1. A skill that triggers a recommendation check reports it under `--recommend`
   and does not report it without the flag. A regression test asserts both
   directions against a fixture, not against repository content.
2. `--no-warnings` suppresses warning-level issues, in each of the `text`,
   `json`, and `csv` formatters.
3. Warning-level issues never change the exit code — it stays error-driven, per
   `ValidationResult.is_valid`. A test pins this: a fixture with warnings and no
   errors exits 0 with and without `--recommend`.
4. `main.py` reads the real argparse destinations — no
   `getattr(parsed_args, ..., default)` on a flag the parser always defines;
   that pattern is what let the `--no-warnings` mismatch pass silently, and will
   hide the next rename the same way.
5. `CrossReferenceValidator` either uses `show_warnings` or stops accepting it —
   no stored, unread field survives the change.
6. The redundancy between `--no-warnings` and `--errors-only` (documented
   near-identically: "Exclude warnings from validation results" vs. "Show only
   errors, exclude warnings") is resolved — either they're documented as
   meaningfully different, or one is removed.

Constraints for whoever picks this up: tests reference no path outside
`py_packages/validate_agent_files/` and import flag names/contract values from
the code under test rather than restating them as literals (per
`py_packages/validate_agent_files/AGENTS.md`); CLI/library tests belong in
`py_packages/validate_agent_files/tests/`, never the plugin suite; turning
recommendations on for the first time will surface findings across
`.agents/plugins/agentdev/` — triage them, don't weaken the checks to keep the
tree green, and don't fold catalog edits into this fix;
`.github/workflows/validate-agent-files.yml` runs `--recommend` today, so
confirm the job still passes or split catalog cleanup into its own commit ahead
of the fix. Out of scope: adding new validators — this restores a path, it does
not extend the rule set.

## Verification

``` bash
cd py_packages/validate_agent_files && uv run --isolated --extra dev pytest
```

Then, from the repository root, against a scratch fixture under `.tmp/` — a
skill whose description carries the vague terms the frontmatter validator looks
for:

``` bash
uv run validate_agent_files .tmp/<fixture>
uv run validate_agent_files --recommend .tmp/<fixture>
uv run validate_agent_files --recommend --no-warnings .tmp/<fixture>
```

The first and third must match; the second must differ from both.

Finally, run the publisher gate the repository actually depends on:

``` bash
uv run validate_agent_files --recommend . --require-marketplace claude codex
```
