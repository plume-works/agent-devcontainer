---
type: bug
description: validate_agent_files' --recommend, --no-warnings, and --errors-only flags have no effect on any run — the warning/recommendation path is entirely disconnected from the validation engine.
sources:
- resource: docs/agents/specs/validator-warning-visibility/ (folded and removed)
- resource: py_packages/validate_agent_files/
stage: done
severity: medium
---

# Bug: Validator warning visibility

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
   (`py_packages/validate_agent_files/validate_agent_files/validators/skill.py::SkillFrontmatterValidator.validate`,
   the vague-description check) and `SkillStructureValidator.validate`
   (`py_packages/validate_agent_files/validate_agent_files/validators/skill.py::SkillStructureValidator.validate`,
   the section-content check). Neither class is imported anywhere in the package
   outside its own module — the engine never reaches them. The tests that cover
   them construct the validators directly, masking the gap. This is the
   load-bearing break: not a flag that fails to disable output, but a feature
   that produces none.
2. **`--no-warnings` writes an attribute nothing reads.**
   `py_packages/validate_agent_files/validate_agent_files/cli.py::parse_arguments`
   declares the flag as `action='store_false', dest='warnings', default=True`,
   so argparse sets `args.warnings`.
   `py_packages/validate_agent_files/validate_agent_files/main.py::main` reads
   `getattr(parsed_args, 'no_warnings', False)` — an attribute the parser never
   creates. The `getattr` default silently swallows the mismatch, so the branch
   is permanently `False`. `--recommend`
   (`py_packages/validate_agent_files/validate_agent_files/main.py::main`) and
   `--errors-only`
   (`py_packages/validate_agent_files/validate_agent_files/main.py::main`) are
   both read correctly and do reach `show_warnings`; the CLI-to-engine plumbing
   is intact for those two, and still changes nothing downstream per (1) and
   (3).
3. **`CrossReferenceValidator` stores `show_warnings` and never reads it.**
   `py_packages/validate_agent_files/validate_agent_files/core.py::ValidationEngine.validate`
   passes `show_warnings` into `CrossReferenceValidator`, which assigns
   `self.show_warnings` at
   `py_packages/validate_agent_files/validate_agent_files/validators/cross_reference.py::CrossReferenceValidator.__init__`
   and never consults it again — the only path by which `show_warnings`
   currently leaves the engine, terminating in a dead field.

The two orphaned validators were never wired in. `SkillFrontmatterValidator` and
`SkillStructureValidator` entered in the initial extraction commit (`c1dce21`)
and no commit since references them outside their own module and
`tests/test_skill_validation.py`. No engine call site was ever removed, so there
is no prior decision to reverse: this is a first wiring, not a restoration.

## Fix

Fixed by [Connect validator
warnings](../plans/20260907-connect-validator-warnings.md).
`SkillFrontmatterValidator` and `SkillStructureValidator` are constructed in
`ValidationEngine.validate` and receive `show_warnings`; `main.py` reads the
real argparse destinations; `--no-warnings` is removed in favour of
`--errors-only`; and `CrossReferenceValidator` no longer accepts the field it
never read. The engine exposes only the validators' warning-level issues, so
their stricter error checks do not expand the default validation contract.

## Key references

Under `py_packages/validate_agent_files/validate_agent_files/`:

- `py_packages/validate_agent_files/validate_agent_files/core.py::ValidationEngine.validate`
  — `ValidationEngine.validate` runs `SkillFrontmatterValidator` and
  `SkillStructureValidator` when `show_warnings` is set, keeping only their
  warning-level issues
- `py_packages/validate_agent_files/validate_agent_files/main.py::main` —
  `show_warnings` derived from `--recommend` and `--errors-only`
- `py_packages/validate_agent_files/validate_agent_files/cli.py::parse_arguments`
  — `--recommend`, with `--errors-only`
- `py_packages/validate_agent_files/validate_agent_files/validators/skill.py::SkillFrontmatterValidator.validate`
  — the vague-description warning; the section-content warning is
- `py_packages/validate_agent_files/validate_agent_files/validators/cross_reference.py::CrossReferenceValidator.__init__`
  — `CrossReferenceValidator.__init__`, which no longer takes `show_warnings`
