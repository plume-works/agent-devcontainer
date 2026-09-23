---
type: codebase
description: Installs the apt development toolchain and a list of pinned, checksum-verified single-binary tools (zizmor, the iwe trio, codebase-memory-mcp, bun).
source: ansible/roles/dev_tools
source_digest: sha256:994e42ee873dfde6efc08f364731f9a9daf7e256c0ab3d1b2214f520c96b77d9
verified:
  by: claude-code/opus-5
  at: 2026-09-23T00:00:00Z
stale_after: 2026-12-22
generated:
  by: claude-code/opus-5
  at: 2026-09-23T00:00:00Z
sources:
- id: code
  resource: ansible/roles/dev_tools
---

# dev_tools role

The general toolchain role: build tooling, git from the git-core PPA,
`pre-commit`, `shellcheck`, `jq`, `ffmpeg`, `btop`, `tmux`, and the pinned
release binaries every other part of the workspace assumes are on `PATH`.

## Public surface

- `dev_tools_apt_pins` —
  `ansible/roles/dev_tools/vars/apt_pins_<suite>_<arch>.yml`; the apt package
  set with its pinned versions
- `dev_tools_pinned_tools` — `ansible/roles/dev_tools/defaults/main.yml:14`;
  each entry names a version, a download URL prefix, an asset prefix, an
  optional `binaries` list, and a per-architecture `target` + `checksum`
- Installed binaries under `/usr/local/bin`: `zizmor`, `iwe`, `iwes`, `iwec`,
  `codebase-memory-mcp`, `bun`

## How it works

`tasks/main.yml` loads the pin file for the running release and architecture,
adds the PPA, installs the apt list as `name=version` specs, then loops
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
  `git-lfs` from the git-core PPA this role adds; both are recorded in
  `ROLE_REPOS` in `scripts/apt-pins-refresh.py`.
- The `iwe` version here must match `IWE_VERSION` in
  `.github/workflows/validate-knowledge-base.yml:18`, which installs the same
  release on the runner.
- `bun` takes the amd64 `-baseline` asset, which runs without AVX2. The plain
  `x64` build is faster but faults on a host that lacks it, and the image
  targets unknown hardware.
- These pins carry a checksum, so Renovate cannot move them: it would advance
  the version and leave the hash behind. They stay hand-maintained, unlike the
  version-only pins in the other roles' `defaults/`.
- `codebase-memory-mcp` uses the `-portable` (static) Linux build; the plain
  build links a newer glibc than some target bases carry. Its agent-config
  wiring is deferred to container create for the same volume-shadowing reason
  the catalog install is.

## Key references

Verified anchor points (line numbers as of 2026-09-22):

- `ansible/roles/dev_tools/tasks/main.yml:3-5` — the pin file include
- `ansible/roles/dev_tools/tasks/main.yml:17-22` — the pinned apt install
- `ansible/roles/dev_tools/tasks/main.yml:24` — the pinned-tools loop
- `ansible/roles/dev_tools/tasks/install_pinned_tool.yml:14-24` — the archive
  layout facts
- `ansible/roles/dev_tools/tasks/install_pinned_tool.yml:31` — download with
  checksum
- `ansible/roles/dev_tools/tasks/install_pinned_tool.yml:40` — extract to a
  tempdir
- `ansible/roles/dev_tools/tasks/install_pinned_tool.yml:46` — copy named
  binaries only
- `ansible/roles/dev_tools/defaults/main.yml:14-84` — the pin table
