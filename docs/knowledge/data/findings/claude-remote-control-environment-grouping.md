---
type: finding
description: The Claude app groups Remote Control sessions by the git repository of the server's folder, so servers in different Coder workspaces that clone one repository share one sidebar group; no CLI flag or folder name changes this.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/remote_control.py
---

# Claude Remote Control environment grouping

Finding measured on Claude Code 2.1.325, with Remote Control servers in two
Coder workspaces that clone `plume-works/agent-devcontainer`.

## Measurement

- **The server registers four values.** `claude remote-control` sends
  `machine_name` (the hostname), `directory` (the folder it starts in),
  `branch`, and `git_repo_url` (the URL of the git remote).
- **The repository sets the group.** The Claude app shows one sidebar group with
  the name of the repository, `agent-devcontainer`. The sessions of the two
  workspaces are in this one group.
- **The hostname is secondary text only.** The environment picker shows
  `machine_name` below the group name. It does not make a different group.
- **The folder name does not set the group.** A server that starts in
  `/workspaces/<workspace name>` shows `Connected · agent-devcontainer` in its
  status line, and its sessions go into the same sidebar group.
- **The name flags change only session titles.** `--name` and
  `--remote-control-session-name-prefix` set the titles of the pre-created
  session and the spawned sessions. They do not change the group.

## Closing

Open until Claude Code adds a display name for a Remote Control environment, or
lets the app group sessions by machine. The maintainer sent this request to
Anthropic. No change in this repository or in the Coder template can close it.
