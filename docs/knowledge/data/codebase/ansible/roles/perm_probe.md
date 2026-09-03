---
type: codebase
description: Stats the shared /usr/local paths and fails the play when any is owned by a non-root account; run first and last in the playbook as a build guard.
source: ansible/roles/perm_probe
commit: eb60f60450c6009b076bc51993b49a924653eaa4
verified:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:04:51Z
stale_after: 2026-12-02
generated:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:04:51Z
sources:
- id: code
  resource: ansible/roles/perm_probe
  title: the code this map describes, read at commit eb60f60
---

# perm_probe role

A guard, not a provisioner. It emits one greppable `PERM_PROBE` line per probed
path and, with `perm_probe_fail_on_drift`, aborts the play at the first path
whose owner is not `uid=0 gid=0`.

## Public surface

- `perm_probe_label`, `perm_probe_paths`, `perm_probe_expected_uid`,
  `perm_probe_expected_gid`, `perm_probe_fail_on_drift` —
  `ansible/roles/perm_probe/defaults/main.yml`
- Log lines `PERM_PROBE [<label>] ...` and `PERM_PROBE DRIFT [<label>] ...`

## How it works

`stat -c` over `/usr/local/bin`, `/usr/local`, `/usr/local/lib`, and
`/usr/local/share` collects numeric uid/gid, resolved names, and mode; a drift
list is built from the expected owner; a labeled report is printed; and the play
fails on a non-empty list when asked to.

## Depends on

Nothing. It is deliberately dependency-free so it can run before every other
role.

## Invariants & gotchas

- The `final` probe must fail the build rather than warn: a bad owner in a
  published layer reproduces in every warm rebuild even after the offending role
  is fixed.
- The label is what attributes a drift to a role; two probes bracket the
  suspect.

## Key references

Verified anchor points (line numbers as of 2026-09-03):

- `ansible/roles/perm_probe/tasks/main.yml:8` — the stat loop
- `ansible/roles/perm_probe/tasks/main.yml:33` — drift detection
- `ansible/roles/perm_probe/tasks/main.yml:53` — fail on drift
- `ansible/playbooks/setup-dev.yml:18,40` — the two guard invocations
