---
type: bug
description: The self-test unwritable-state-root test asserts an OSError the kernel never raises for UID 0, so it fails wherever the suite runs as root.
generated:
  by: claude-code/opus-5
  at: 2026-09-09T00:00:00Z
sources:
- resource: .agents/plugins/self-improve/tests/integration/test_dispatcher.py
- resource: .agents/plugins/self-improve/selfimprove/commands.py
stage: done
---

# Self-test unwritable-root check assumes a non-root user

## Symptom

`test_self_test_fails_when_state_root_is_unwritable` fails in this repository's
devcontainer, which runs as root. The test expects `si self-test` to exit 1
against an unwritable state root; it exits 0 and reports `ok`.

The failure is not a defect in the behavior under test — it is the test
asserting a guarantee the operating system does not make to a privileged user.
The check it guards is still valuable for the unprivileged case it was written
for.

## Reproduction

``` console
$ uv run pytest .agents/plugins/self-improve/tests/integration/test_dispatcher.py::test_self_test_fails_when_state_root_is_unwritable
E   AssertionError: assert 0 == 1
1 failed
```

The same test fails identically in the unmerged upstream checkout at `e94031a`,
so the move into this repository did not introduce it — the suite simply had not
been run as root before.

## Root cause

The test makes its state root `mode=0o500` and expects the write to be refused.
`DIR_MODE` enforcement and the write probe both depend on the kernel rejecting
the access, and for UID 0 it does not: `CAP_DAC_OVERRIDE` bypasses the
permission bits, so `os.makedirs` under a mode-500 directory succeeds.

`self_test` therefore records no failure and exits 0. Both of its state-root
checks — the `DIR_MODE` comparison and the `atomic_write` probe — are
unreachable as failures for a privileged user, because `ensure_dir` recreates
the directory at the expected mode before either runs.

## Fix

The test is skipped when `os.getuid() == 0`, with that reason attached. The
behavior it covers is verified correct for the unprivileged user it targets: as
`nobody`, `si self-test` against a mode-500 parent exits 1 and reports
`cannot create state root ... (Permission denied)`.

Skipping states the limit honestly but leaves the root case uncovered. Driving
the refusal through something privilege does not bypass — a read-only mount, or
an unwritable path on a filesystem mounted `ro` — would restore it, and is the
better fix whenever the coverage is wanted back.

No plugin behavior changed:
[Consolidate the self-improve plugin into this repository](../plans/20260909-consolidate-self-improve-plugin.md)
moves the code and does not modify it.

## Key references

Verified anchor points (line numbers as of 2026-09-09):

- `.agents/plugins/self-improve/tests/integration/test_dispatcher.py:42-52` —
  the root skip and the `mode=0o500` directory the test relies on
- `.agents/plugins/self-improve/selfimprove/commands.py:396-414` — the state
  root checks that cannot fail for UID 0
- `.agents/plugins/self-improve/selfimprove/paths.py:13` — `DIR_MODE`, the mode
  `ensure_dir` restores before the probe runs
