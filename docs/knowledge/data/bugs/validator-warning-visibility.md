---
type: bug
description: validate_agent_files' --recommend, --no-warnings, and --errors-only flags have no effect on any run — the warning/recommendation path is entirely disconnected from the validation engine.
generated:
  by: claude-code/opus-5
  at: 2026-09-07T00:00:00Z
sources:
- resource: docs/agents/specs/validator-warning-visibility/ (folded and removed)
- resource: py_packages/validate_agent_files/
---

# Validator warning visibility

## Symptom

`validate_agent_files`' entire warning-and-recommendation path is inert.
`--recommend`, `--no-warnings`, and `--errors-only` change no observable output
on any run. `README.md` and `.github/workflows/validate-agent-files.yml` tell
contributors to run `--recommend`; it currently shows nothing extra, so the
repository believes it has a quality signal it does not have.

## Reproduction

A scratch skill whose description carries vague terms
`SkillFrontmatterValidator` looks for (`helpers`, `utilities`, `tools`,
`various`, `general`) and whose top-level header is followed by a near-empty
section — tripping both warning checks — produces byte-identical output under
every flag combination, each reporting `Errors: 0, Warnings: 0` and exiting 0.

``` bash
cd py_packages/validate_agent_files
uv run validate_agent_files <fixture>                              # no recommendations
uv run validate_agent_files --recommend <fixture>                  # recommendations
uv run validate_agent_files --recommend --no-warnings <fixture>    # suppressed again
uv run validate_agent_files --recommend --errors-only <fixture>    # suppressed again
```

The first, third, and fourth runs should match; the second should differ from
all of them. Today all four are identical.

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
   is permanently `False`. `--recommend` (`main.py:22`) and `--errors-only`
   (`main.py:23`) are both read correctly and do reach `show_warnings`; the
   CLI-to-engine plumbing is intact for those two, and still changes nothing
   downstream per (1) and (3).
3. **`CrossReferenceValidator` stores `show_warnings` and never reads it.**
   `core.py:98` passes `show_warnings` into `CrossReferenceValidator`, which
   assigns `self.show_warnings` at `validators/cross_reference.py:44` and never
   consults it again — the only path by which `show_warnings` currently leaves
   the engine, terminating in a dead field.

The two orphaned validators were never wired in. `SkillFrontmatterValidator` and
`SkillStructureValidator` entered in the initial extraction commit (`c1dce21`)
and no commit since references them outside their own module and
`tests/test_skill_validation.py`. No engine call site was ever removed, so there
is no prior decision to reverse: this is a first wiring, not a restoration.

## Fix

Not started. Wire `SkillFrontmatterValidator` and `SkillStructureValidator` into
`CustomizationsValidationEngine`, treating their existing checks as the intended
recommendation set — `tests/test_skill_validation.py` already describes the
behavior. Redesigning the recommendation set from scratch was considered and
rejected: it would only be warranted by a reason to distrust the existing
checks, and since they were never wired in (see Root cause), nothing was ever
rejected about them.

Fixing the `--no-warnings`/`args.no_warnings` attribute mismatch alone is not
worth shipping on its own — it would make the flag control a value that still
reaches nothing. Fix the wiring first, or fix all three together.

Acceptance criteria for the eventual fix:

1. A skill that triggers a recommendation check reports it under `--recommend`
   and does not report it without the flag. A regression test asserts both
   directions against a fixture, not against repository content.
2. `--no-warnings` suppresses warning-level issues. Suppression is upstream of
   rendering — when `show_warnings` is false the issues are never generated, so
   no formatter sees them and one test covers all three. If the design instead
   becomes generate-then-filter, `text`, `json`, and `csv` each need their own.
3. Warning-level issues never change the exit code — it stays error-driven, per
   `ValidationResult.is_valid`. A test pins this: a fixture with warnings and no
   errors exits 0 with and without `--recommend`.
4. `main.py` reads the real argparse destinations — no
   `getattr(parsed_args, ..., default)` on a flag the parser always defines;
   that pattern is what let the `--no-warnings` mismatch pass silently, and will
   hide the next rename the same way.
5. `CrossReferenceValidator` either uses `show_warnings` or stops accepting it —
   no stored, unread field survives the change.
6. The redundancy between `--no-warnings` and `--errors-only` is resolved. They
   are not merely documented alike ("Exclude warnings from validation results"
   vs. "Show only errors, exclude warnings") — both land on the same
   `show_warnings = False` at `main.py:23-24` with no distinct behavior, so
   documenting a difference would mean inventing one. Remove one, or keep it as
   an explicit alias.

Constraints for whoever picks this up: tests reference no path outside
`py_packages/validate_agent_files/` and import flag names/contract values from
the code under test rather than restating them as literals (per
`py_packages/validate_agent_files/AGENTS.md`); CLI/library tests belong in
`py_packages/validate_agent_files/tests/`, never the plugin suite; turning
recommendations on for the first time surfaces one finding in the catalog —
`sync-super-linter-tool-versions` trips the vague-term check on "tools" — so
triage it rather than weakening the check, and keep any catalog edit out of this
fix. `.github/workflows/validate-agent-files.yml` runs `--recommend` today, but
warnings cannot fail it: `ValidationResult.is_valid` is error-only. Out of
scope: adding new validators — this connects a path, it does not extend the rule
set.

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
