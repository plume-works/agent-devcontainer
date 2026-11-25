# agentdev-lib

Code shared by the scripts of the agentdev plugins, published so that a script
in one installed plugin can use it without reaching into another plugin's files.

- `agentdev_lib.result_codes` — the exit-code table and the `RESULT=<NAME>` line.
- `agentdev_lib.skill_common` — `Stop`, `print_error`, git and tool runners.
- `agentdev_lib.git_default_branch` — recognize a repository's default branch.

Each plugin pins the exact version. A checkout of
[agent-devcontainer](https://github.com/plume-works/agent-devcontainer) runs
this source directly.
