# Development Tools Role

This Ansible role installs a general set of development tools: build tooling
(build-essential, CMake, Ninja, pkg-config), version control (git, git-lfs),
Python packaging basics, `pre-commit`, `shellcheck`, `jq`, `ffmpeg`, `btop`,
and the pinned `zizmor` GitHub Actions auditor, `iwe`/`iwes`/`iwec`, and the
`codebase-memory-mcp` binary.

## codebase-memory-mcp

Installs only the pinned `codebase-memory-mcp` binary to
`/usr/local/bin/codebase-memory-mcp`. The upstream `install.sh` bundled in each
release archive re-downloads from GitHub's "latest" alias even when run
locally, which defeats pinning — so this role downloads the versioned archive
directly, verifies its checksum, and copies out just the binary (skipping the
bundled `install.sh`, `LICENSE`, and `THIRD_PARTY_NOTICES.md`). Linux always
uses the `-portable` (statically linked) archive variant for compatibility
with older glibc bases.

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
