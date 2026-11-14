---
type: adr
stage: accepted
description: Setup that needs Coder user secrets or the Coder agent environment runs from the agent start, never from a Dev Container lifecycle command.
---

# Setup that needs Coder user secrets runs from the agent start

Coder adds its agent after `devcontainer up`. As a result, the Dev Container
lifecycle commands do not get Coder user secrets or the agent environment
(`GITHUB_TOKEN`, `CODER_*`, `GIT_ASKPASS`). Setup that needs them runs from the
agent start. The git credential helper is one example: with no helper for
github.com, git uses `GIT_ASKPASS=/.coder-agent/coder`, which never returns, and
`git push` does not complete.

## Considered Options

- Configure the credential helper from the Remote Control start. Rejected: it
  connects git credentials to Remote Control and to its claude.ai login gate.
- A second `coder_script` in the template that runs the helper directly.
  Rejected: the agent-start logic is then in two repositories.

## Consequences

- The template runs one configurable command, `agentdev-runtime coder start`,
  that has no information about the steps of this repository
  (`py_packages/agentdev_runtime/agentdev_runtime/coder.py::STEPS`). A rename of
  the command breaks the template.
- The agent start installs the helper only when `gh` is authenticated.
- This repository does not change the Coder `GIT_ASKPASS` and configures no
  Coder external authentication for GitHub.
- The start phase keeps its own helper setup for containers with a stored `gh`
  login, by decision of the maintainer.
