---
type: bug
description: scripts/run-root-tests always selects only requires_root tests, so the conftest guard that stops a run with unmarked tests never sees one and the usage error it promises never occurs.
stage: pending
severity: low
sources:
- resource: scripts/run-root-tests
- resource: scripts/tests/conftest.py
- resource: .github/workflows/ci.yml
- resource: docs/knowledge/data/findings/spec-usefulness-audit.md
- resource: docs/spec-audit/requirements.jsonl
---

# Bug: the root-test launcher guard against unmarked tests cannot fire

## Symptom

When `scripts/run-root-tests` gets a path that holds an unmarked test, it must
stop with a usage error that names that test. It does not stop. It runs the
marked tests and deselects the unmarked ones without a message.

## Reproduction

1. Run `scripts/run-root-tests scripts/tests` as a non-root account with
   passwordless `sudo`.
2. `scripts/tests` holds unmarked tests.
3. The run passes, and no usage error names an unmarked test.

## Root cause

`scripts/run-root-tests` always passes `-m requires_root`. pytest deselects the
unmarked tests before `scripts/tests/conftest.py::pytest_collection_finish`
reads `session.items`, so its list of other tests is always empty. The guard
fires only when a caller gives a second `-m`. `.github/workflows/ci.yml` runs
`scripts/run-root-tests -n 8 scripts/tests` and expects success.
