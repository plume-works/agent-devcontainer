# Development Tools Role

This Ansible role installs a general set of development tools: build tooling
(build-essential, CMake, Ninja, pkg-config), version control (git, git-lfs),
Python packaging basics, `pre-commit`, `shellcheck`, `jq`, `ffmpeg`, `btop`,
and a list of pinned single-binary tools (currently the `zizmor` GitHub
Actions auditor and the `codebase-memory-mcp` binary).

## Pinned single-binary tools

Each entry in `dev_tools_pinned_tools` (`defaults/main.yml`) describes a tool
released as a per-architecture `tar.gz`: a name, a version, a download URL
built from `url_prefix`/`asset_prefix`/the per-arch `target`, and a SHA-256
checksum per architecture. `tasks/install_pinned_tool.yml` is included once
per entry via `loop` and, for each one: verifies `system_arch` is covered,
downloads and checksum-verifies the archive, extracts it to a scratch
tempdir, and copies out only the file named after the tool to
`/usr/local/bin/<name>` as `root:root` (mode `0755`).

Extracting to a tempdir first — rather than unpacking the archive directly
into `/usr/local/bin` — is deliberate: some release tarballs embed a `./`
directory entry owned by the account that built the release (for example, a
GitHub Actions hosted runner's `1001:1001`), and Ansible's `unarchive` module
applies that embedded ownership to the destination directory itself when
present. Unpacking into an isolated tempdir and then copying out just the
named binary with an explicit `owner`/`group` means a tool's release process
can never corrupt the ownership of a shared system directory.

Add a new tool by adding an entry to `dev_tools_pinned_tools`; no task
changes are needed.

### codebase-memory-mcp

The upstream `install.sh` bundled in each release archive re-downloads from
GitHub's "latest" alias even when run locally, which defeats pinning — so
this role downloads the versioned archive directly instead of running that
installer. Linux always uses the `-portable` (statically linked) archive
variant for compatibility with older glibc bases.

This role deliberately does **not** run `codebase-memory-mcp install`, which
wires MCP entries into per-agent config such as `~/.claude.json` and
`~/.codex`. Those paths are commonly volume-mounted, so a build-time config
write would be silently shadowed on any container whose volume already
exists — the same reason `agentic_tools` only stages its catalog at build
time (see that role's README). Run `codebase-memory-mcp install -y --force`
as the target user from a container-create lifecycle script (alongside
`reinstall-agentdev-claude.sh`/`reinstall-agentdev-codex.sh`) to wire up agent
config once the real per-user volumes are mounted.

## Example Usage

```yaml
- name: Install development tools
  hosts: all
  become: true
  roles:
    - { role: dev_tools, tags: ['dev_tools'] }
```
