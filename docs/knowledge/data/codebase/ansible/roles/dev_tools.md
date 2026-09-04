---
type: codebase
description: Installs the apt development toolchain and a list of pinned, checksum-verified single-binary tools (zizmor, the iwe trio, codebase-memory-mcp).
source: ansible/roles/dev_tools
source_digest: sha256:bf4d9add86cc2b21f54fd9407025cc7ecf450abff863a4cee1cb0453e312221a
verified:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
stale_after: 2026-12-03
generated:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
sources:
- id: code
  resource: ansible/roles/dev_tools
---

# dev_tools role

The general toolchain role: build tooling, git from the git-core PPA,
`pre-commit`, `shellcheck`, `jq`, `ffmpeg`, `btop`, and the pinned release
binaries every other part of the workspace assumes are on `PATH`.

## Public surface

- `dev_tools_pinned_tools` — `ansible/roles/dev_tools/defaults/main.yml:14`;
  each entry names a version, a download URL prefix, an asset prefix, an
  optional `binaries` list, and a per-architecture `target` + `checksum`
- Installed binaries under `/usr/local/bin`: `zizmor`, `iwe`, `iwes`, `iwec`,
  `codebase-memory-mcp`

## How it works

`tasks/main.yml` adds the PPA, installs the apt list, then loops
`install_pinned_tool.yml` over `dev_tools_pinned_tools`: check the architecture
is listed, download the archive with its checksum, extract into a temporary
directory, copy only the named binaries to `/usr/local/bin` as `root:root`, and
clean up. The archive is never unpacked into `/usr/local/bin` itself.

## Depends on

`extra_facts` for `system_arch`. Nothing else in the play.

## Invariants & gotchas

- Extract-then-copy is the whole defense against a release archive whose `./`
  entry carries its build runner's uid: unpacking directly would re-own
  `/usr/local/bin`, which [perm_probe](perm_probe.md) then catches.
- The `iwe` version here must match `IWE_VERSION` in
  `.github/workflows/validate-knowledge-base.yml:18`, which installs the same
  release on the runner.
- `codebase-memory-mcp` uses the `-portable` (static) Linux build; the plain
  build links a newer glibc than some target bases carry. Its agent-config
  wiring is deferred to container create for the same volume-shadowing reason
  the catalog install is.

## Key references

Verified anchor points (line numbers as of 2026-09-04):

- `ansible/roles/dev_tools/tasks/main.yml:34` — the pinned-tools loop
- `ansible/roles/dev_tools/tasks/install_pinned_tool.yml:16` — download with
  checksum
- `ansible/roles/dev_tools/tasks/install_pinned_tool.yml:25` — extract to a
  tempdir
- `ansible/roles/dev_tools/tasks/install_pinned_tool.yml:31` — copy named
  binaries only
- `ansible/roles/dev_tools/defaults/main.yml:14-64` — the pin table
