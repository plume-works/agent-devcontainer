---
type: codebase
description: Builds the validate_agent_files package from the provisioning sources and installs it as an isolated uv tool, verifying the installed version against a pin.
source: ansible/roles/validate_agent_files
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
  resource: ansible/roles/validate_agent_files
  title: the code this map describes, read at commit eb60f60
---

# validate_agent_files role

Puts the `validate_agent_files` CLI on `PATH` in the image so a consuming
project validates its agents and skills with no checkout of this repository and
no `uv run` prefix.

## Public surface

- `validate_agent_files_source_dir`, `validate_agent_files_version` —
  `ansible/roles/validate_agent_files/defaults/main.yml`
- The `validate_agent_files` executable installed by `uv tool install`

## How it works

Stats the package source and fails if it is missing, copies it into a temporary
build directory, prunes build scratch directories, installs it with
`uv tool install`, reads back the installed version, and fails unless it equals
the pin.

## Depends on

`uv_setup` (must run first), and the
[validator package](../../py_packages/validate_agent_files.md) sources at
`validate_agent_files_source_dir`.

## Invariants & gotchas

- The pin is verified, not fetched: `VALIDATE_AGENT_FILES_VERSION` in the
  Dockerfile and `version` in the package's `pyproject.toml` are bumped together
  or the build fails.
- The package must build with zero knowledge of this repository, since the role
  copies only `py_packages/validate_agent_files/`.

## Key references

Verified anchor points (line numbers as of 2026-09-03):

- `ansible/roles/validate_agent_files/tasks/main.yml:12` — fail when the source
  is missing
- `ansible/roles/validate_agent_files/tasks/main.yml:59` — `uv tool install`
- `ansible/roles/validate_agent_files/tasks/main.yml:81` — installed-version
  read-back
