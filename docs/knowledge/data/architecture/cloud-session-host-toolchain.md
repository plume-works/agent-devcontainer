---
type: architecture
description: A Claude Code cloud session works on the session host itself — .claude/startup.py provisions the project toolchain there with the image's own Ansible roles — and runs no Docker daemon and no devcontainer.
sources:
- resource: .claude/startup.py
- resource: .claude/CLAUDE.cloud.md
- resource: ansible/playbooks/setup-dev.yml
- resource: docker/ansible/setup-ansible.sh
- resource: .pre-commit-config.yaml
- resource: https://code.claude.com/docs/en/claude-code-on-the-web
---

# Cloud session host toolchain

## Setup

A Claude Code cloud session runs `.claude/startup.py` as its environment setup
script, once, when the session's host is built. It:

1. registers the checkout as the `agent-devcontainer` plugin marketplace and
   installs `agentdev`;
2. copies `.claude/CLAUDE.cloud.md` to `~/.claude/CLAUDE.md`, which tells the
   session that tools, commits, pushes and `gh` run on the host;
3. merges `ZIZMOR_OFFLINE=true` into the `env` of the user-level
   `~/.claude/settings.json`, so every command the session runs skips zizmor's
   online audits, which the session's placeholder `GH_TOKEN` fails ([Bug: zizmor
   online audits fail in the cloud
   devcontainer](../bugs/zizmor-online-audits-fail-in-cloud-devcontainer.md));
4. installs Ansible with `docker/ansible/setup-ansible.sh` and runs
   `ansible/playbooks/setup-dev.yml` with the `dev_tools` and `uv_setup` tags,
   which install the pinned binaries every `language: system` pre-commit hook
   calls, `bun`, `iwe`, and `uv`;
5. runs `uv sync` and installs the git hooks with
   `pre-commit install --install-hooks` for the `pre-commit`, `pre-push`,
   `pre-merge-commit` and `post-checkout` hook types.

Any failing step fails the script, and the session starts without the steps
after it.

## Decision

Cloud sessions run no Docker daemon and no devcontainer (human:author). The
session host is reclaimed after a few idle minutes and cold-boots on the next
event with a new agent proxy port ([Cloud session host
restarts](cloud-session-host-restarts.md)); a toolchain on the host's disk
survives that, while a container reached through a relay to the proxy had to be
restored before every turn. `git push` and `gh` reach GitHub through the
session's agent proxy directly, and no `SessionStart` hook runs.

## Constraints

- Host tools and the published images come from the same `dev_tools` and
  `uv_setup` roles and the same `uv.lock`, so a hook resolves the same version
  on the host as in CI's pre-commit job.
- Work that needs Docker — image builds, the image and lifecycle tests — does
  not run in a cloud session; CI runs it.
- The `link-venv` hook needs `agentdev-runtime`, which only the images ship, so
  on the host it skips and `.venv` is the project environment `uv sync` made.
- GitHub GraphQL is refused by the session's proxy policy, so `gh` commands
  built on it fail; `gh auth status` validates the token through GraphQL and
  reports it as invalid while REST calls with it succeed.
