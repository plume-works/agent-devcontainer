---
type: codebase
description: Installs the apt development toolchain and a list of pinned, checksum-verified single-binary tools (zizmor, the iwe CLI and LSP server, codebase-memory-mcp, bun).
source: ansible/roles/dev_tools
source_digest: sha256:29c08d14077793b973936f61ca9f7ac4091ccd4c3b98b63f7e2bdb8a4e8ecab5
verified:
  by: claude-code/opus-5.5
  at: 2026-10-23T21:51:57Z
stale_after: 2027-01-21
generated:
  by: claude-code/opus-5.5
  at: 2026-10-23T21:51:57Z
sources:
- id: code
  resource: ansible/roles/dev_tools
---

# dev_tools role

The general toolchain role: build tooling, git from the git-core PPA,
`pre-commit`, `shellcheck`, `jq`, `ffmpeg`, `btop`, `tmux`, and the pinned
release binaries every other part of the workspace assumes are on `PATH`.

## Public surface

- `dev_tools_pinned_tools` — `ansible/roles/dev_tools/defaults/main.yml:18`;
  each entry names a version, a download URL prefix, an asset prefix (where
  `{version}` expands to the version and `{bare_version}` to it without a
  leading `v`), an optional `binaries` list, and a per-architecture `target` +
  `checksum`
- Installed binaries under `/usr/local/bin`: `zizmor`, `gitleaks`, `actionlint`,
  `iwe`, `iwes`, `codebase-memory-mcp`, `bun`

## How it works

`tasks/main.yml` adds the PPA, installs the apt list unpinned, then loops
`install_pinned_tool.yml` over `dev_tools_pinned_tools`: resolve the asset name
and archive layout, check the architecture is listed, download the archive with
its checksum, extract into a temporary directory, copy only the named binaries
to `/usr/local/bin` as `root:root`, and clean up. The archive is never unpacked
into `/usr/local/bin` itself. An entry's `extension` selects the archive format
when it is not `tar.gz` and `binaries_in_asset_dir` says its binaries sit under
a directory named after the asset; `bun`'s `.zip` needs both, and the `unzip` in
the apt list is what extracts it.

## Depends on

`extra_facts` for `system_arch`. Nothing else in the play.

## Invariants & gotchas

- Extract-then-copy is the whole defense against a release archive whose `./`
  entry carries its build runner's uid: unpacking directly would re-own
  `/usr/local/bin`, which [perm_probe](perm_probe.md) then catches.
- `cmake` in the apt list resolves from the Kitware repository that
  [cmake_kitware](../../ansible.md) adds before this role runs, and `git` and
  `git-lfs` from the git-core PPA this role adds.
- The `iwe` entry is also the knowledge-base CI's and Renovate post-upgrade
  task's `iwe`: both install it from this pin through
  `scripts/fetch-pinned-tool.py`.
- `bun` takes the amd64 `-baseline` asset, which runs without AVX2. The plain
  `x64` build is faster but faults on a host that lacks it, and the image
  targets unknown hardware.
- Every entry except `zizmor`, `gitleaks`, and `actionlint` carries a
  `# renovate:` comment above its `version`, so Renovate bumps it and
  `scripts/refresh-pin-checksums.py`, which registers this file in `PIN_FILES`,
  recomputes its checksums in the same commit. Those three have no comment: they
  move with the Super-Linter tool sync. `gitleaks` and `actionlint` sit at the
  `.pre-commit-config.yaml` revisions of their hooks.
- `codebase-memory-mcp` uses the `-portable` (static) Linux build; the plain
  build links a newer glibc than some target bases carry. Its agent-config
  wiring is deferred to container create for the same volume-shadowing reason
  the catalog install is.

## Key references

Verified anchor points (line numbers as of 2026-10-23):

- `ansible/roles/dev_tools/tasks/main.yml:10` — the apt install
- `ansible/roles/dev_tools/tasks/main.yml:37` — the pinned-tools loop
- `ansible/roles/dev_tools/tasks/install_pinned_tool.yml:13-26` — the archive
  layout facts, `{version}` and `{bare_version}` expanded in `asset_prefix`
- `ansible/roles/dev_tools/tasks/install_pinned_tool.yml:32` — download with
  checksum
- `ansible/roles/dev_tools/tasks/install_pinned_tool.yml:41` — extract to a
  tempdir
- `ansible/roles/dev_tools/tasks/install_pinned_tool.yml:47` — copy named
  binaries only
- `ansible/roles/dev_tools/defaults/main.yml:19-113` — the pin table
