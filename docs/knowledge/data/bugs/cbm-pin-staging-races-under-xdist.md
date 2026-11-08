---
type: bug
stage: done
severity: low
description: Under pytest-xdist, the CBM tests fail with ETXTBSY because every worker's fixture copies the pinned codebase-memory-mcp binary over one shared /tmp path while another worker is executing it.
sources:
- resource: scripts/tests/cbm_pin.py
- resource: scripts/tests/test_agent_runtime_cbm.py
- resource: scripts/tests/test_repair_codex_cbm_hooks_block.py
- resource: scripts/tests/scratch.py
---

# Bug: CBM pin staging races under pytest-xdist

## Symptom

`uv run pytest -n auto` over the CBM test files fails some tests with
`OSError: [Errno 26] Text file busy` (ETXTBSY) while staging or running the
pinned `codebase-memory-mcp` binary. The same files pass when run serially.

## Reproduction

On a host where `codebase-memory-mcp` on `PATH` reports the pinned version, run
`uv run pytest -n auto scripts/tests/test_agent_runtime_cbm.py scripts/tests/test_repair_codex_cbm_hooks_block.py`.
Some tests error with ETXTBSY. Running the same command without `-n`, all of
them pass.

## Root cause

`stage_pinned_cbm` stages to a fixed path,
`/tmp/agentdev-tests/cbm-pin-<version>/codebase-memory-mcp`, which every xdist
worker shares. When the installed binary matches the pin, it calls
`shutil.copy2` onto that path unconditionally, even when the staged copy is
already current. Linux refuses to open an executing file for writing, so a
worker that re-stages while another worker's test runs the binary hits ETXTBSY.

## Fix

`stage_pinned_cbm` returns the staged binary untouched when it already reports
the pinned version. Otherwise it stages the binary in a private temporary
directory beside the destination and renames it into place, which never writes
to an inode another worker is executing.

## Key references

- `scripts/tests/cbm_pin.py::stage_pinned_cbm` — `stage_pinned_cbm`
- `scripts/tests/cbm_pin.py::stage_pinned_cbm` — reuse of a current staged
  binary
- `scripts/tests/cbm_pin.py::stage_pinned_cbm` — private staging directory
- `scripts/tests/cbm_pin.py::stage_pinned_cbm` — the atomic rename into place
- `scripts/tests/scratch.py::TMP_ROOT` — `TMP_ROOT`, shared by every worker
