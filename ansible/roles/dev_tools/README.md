# Development Tools Role

This Ansible role installs a general set of development tools: build tooling
(build-essential, CMake, Ninja, pkg-config), version control (git, git-lfs),
Python packaging basics, `pre-commit`, `shellcheck`, `jq`, `ffmpeg`, `btop`,
and a list of pinned single-archive tools (currently the `zizmor` GitHub
Actions auditor, `iwe`, and the `codebase-memory-mcp` binary).

## Pinned single-archive tools

Each entry in `dev_tools_pinned_tools` (`defaults/main.yml`) describes a tool
released as a per-architecture `tar.gz`: a name, a version, a download URL
built from `url_prefix`/`asset_prefix`/the per-arch `target`, and a SHA-256
checksum per architecture. `tasks/install_pinned_tool.yml` is included once
per entry via `loop` and, for each one: verifies `system_arch` is covered,
downloads and checksum-verifies the archive, extracts it to a scratch
tempdir, and copies out the files named in `binaries` (defaulting to a
single-element list containing `name`) to `/usr/local/bin/<binary>` as
`root:root` (mode `0755`). Set `binaries` explicitly when a tarball ships more
than one binary to install, as `iwe` does for `iwe`, `iwes`, and `iwec`.

Archives are extracted to a tempdir, then selected binaries are copied into
`/usr/local/bin` with explicit `owner`/`group`. Archive metadata must never
change ownership of a shared system directory.

Add a new tool by adding an entry to `dev_tools_pinned_tools`; no task
changes are needed unless the tarball ships binaries under names that differ
from what `binaries` (or the default of `name`) can express.

### codebase-memory-mcp

For `codebase-memory-mcp`, this role downloads the pinned portable archive
directly and installs the binary from that archive. Linux always uses the
`-portable` (statically linked) archive variant for compatibility with older
glibc bases.

This role installs only the binary. Agent config wiring runs from
`postCreateCommand` after volumes mount, alongside
`reinstall-agentdev-claude.sh` and `reinstall-agentdev-codex.sh`.

## Example Usage

```yaml
- name: Install development tools
  hosts: all
  become: true
  roles:
    - { role: dev_tools, tags: ['dev_tools'] }
```
