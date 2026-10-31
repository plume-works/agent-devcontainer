---
type: bug
description: Under pytest-xdist, the CBM tests fail with ETXTBSY because every worker's fixture copies the pinned codebase-memory-mcp binary over one shared /tmp path while another worker is executing it.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T05:09:57Z
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

Not fixed. Options include staging only when the staged binary is absent or
reports a different version, or copying to a unique temporary name and renaming
it into place atomically. Either keeps a running binary's inode untouched.

## Key references

Verified anchor points (line numbers as of 2026-10-31):

- `scripts/tests/cbm_pin.py:29` — `stage_pinned_cbm`
- `scripts/tests/cbm_pin.py:36-37` — the shared staging path
- `scripts/tests/cbm_pin.py:39-41` — the unconditional `shutil.copy2` over it
- `scripts/tests/scratch.py:5` — `TMP_ROOT`, shared by every worker
- `scripts/tests/test_agent_runtime_cbm.py:29` — fixture calling it
- `scripts/tests/test_repair_codex_cbm_hooks_block.py:256` — fixture calling it
