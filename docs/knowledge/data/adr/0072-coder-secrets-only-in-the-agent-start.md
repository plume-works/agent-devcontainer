---
type: adr
stage: accepted
---

# Setup that needs Coder user secrets runs from the Coder agent start

Coder adds its agent after `devcontainer up`. As a result, the Dev Container
lifecycle commands do not get Coder user secrets or the agent environment
(`GITHUB_TOKEN`, `CODER_*`, `GIT_ASKPASS`). Setup that needs them runs from the
agent start: `agentdev-runtime coder start`, which the Coder template runs each
time the Coder agent starts. The git credential helper is one example: with no
helper for github.com, git uses `GIT_ASKPASS=/.coder-agent/coder`, which never
returns, so `git push` hangs.

## Considered Options

- Configure the credential helper from the Remote Control start. Rejected: it
  ties git credentials to Remote Control and to its claude.ai login gate.
- A second `coder_script` in the template that runs the helper directly.
  Rejected: it splits the agent-start logic across two repositories.

## Consequences

- The template runs one configurable command, `agentdev-runtime coder start`,
  that knows nothing of the steps of this repository. A rename of the command
  breaks the template.
- This repository does not change the Coder `GIT_ASKPASS` and configures no
  Coder external authentication for GitHub.
- The start phase keeps its own helper setup for containers with a stored `gh`
  login, by decision of the maintainer.
