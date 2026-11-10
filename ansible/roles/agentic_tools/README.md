# Agentic Tools Role

Installs the agentic CLI tooling used in the workspace and the security layer
that guards it:

- **Bun-managed globals**: `@modelcontextprotocol/inspector`,
  `@anthropic-ai/claude-code`, `@opencode/cli` (OpenCode v2, trusted so its postinstall fetches the platform binary), and `@fission-ai/openspec`.
- **OpenSpec delivery**: sets the user's global OpenSpec config to `delivery: skills`,
  so `openspec init` and `openspec update` generate workflow skills and no slash commands.
- **[cc-filter](https://github.com/wissem/cc-filter)**: a hard security layer in
  front of Claude Code hooks. It blocks sensitive file access, blocks risky
  shell/search commands, and redacts secrets. The role downloads the
  architecture-appropriate release binary and wires it into the user's Claude
  Code hooks (`~/.claude/settings.json`).

Gated by `install_agentic_tools` in the playbook. The agent catalog is staged and
installed by the [`agent_catalog`](../agent_catalog/README.md) role.

## Example Usage

```yaml
- name: Install agentic tools
  hosts: all
  become: true
  roles:
    - {
        role: agentic_tools,
        tags: ['agentic_tools'],
        when: install_agentic_tools | default(false) | bool,
      }
```

## Variables

### Agent CLIs

| Variable                            | Default             | Description                                                                                     |
| ----------------------------------- | ------------------- | ----------------------------------------------------------------------------------------------- |
| `agentic_tools_claude_code_version` | pinned              | `@anthropic-ai/claude-code` version.                                                            |
| `agentic_tools_opencode_version`    | pinned              | `@opencode/cli` version; the OpenCode CLI.                                                      |
| `agentic_tools_inspector_version`   | pinned              | `@modelcontextprotocol/inspector` version.                                                      |
| `agentic_tools_openspec_version`    | pinned              | `@fission-ai/openspec` version.                                                                 |
| `agentic_tools_bun_packages`        | the four CLIs above | Packages installed as Bun globals, each at its pin; `trust: true` runs a package's postinstall. |

### cc-filter

| Variable                                  | Default                    | Description                                        |
| ----------------------------------------- | -------------------------- | -------------------------------------------------- |
| `agentic_tools_cc_filter_install`         | `true`                     | Install the cc-filter binary.                      |
| `agentic_tools_cc_filter_version`         | `v0.0.6`                   | cc-filter release tag to download.                 |
| `agentic_tools_cc_filter_install_path`    | `/usr/local/bin/cc-filter` | Destination for the cc-filter binary.              |
| `agentic_tools_cc_filter_binary_mode`     | `"0755"`                   | File mode for the installed binary.                |
| `agentic_tools_cc_filter_checksums`       | per-arch sha256 map        | Expected binary checksums; bump with the version.  |
| `agentic_tools_cc_filter_configure_hooks` | `true`                     | Merge cc-filter hooks into Claude `settings.json`. |
| `agentic_tools_cc_filter_download_url`    | derived from version/arch  | Override to pin a custom binary URL.               |

## Required External Variables

These variables are not defined by this role and must be supplied by the
playbook or inventory (the `extra_facts` role provides them in this
repository):

| Variable      | Description                                                            |
| ------------- | ---------------------------------------------------------------------- |
| `system_arch` | Target CPU architecture (`amd64` or `arm64`) for the binary URL.       |
| `user_home`   | Home directory of the target user (locates `~/.claude/settings.json`). |
| `dev_user`    | User whose global OpenSpec config is set to deliver skills only.       |
