---
type: architecture
description: Run a sibling repository's build and tests in its own devcontainer through bunx, with explicit workspace targeting and isolated registry diagnostics.
generated:
  by: opencode/openai-gpt-6.1-sol
  at: 2026-10-18T19:34:45Z
sources:
- resource: .agents/plugins/agentdev/skills/microvm-sandbox/SKILL.md
- resource: AGENTS.md
- resource: https://github.com/devcontainers/cli
- resource: https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
---

# Testing sibling workspaces in devcontainers

## Execution boundary

Use the target repository's devcontainer to supply its build and test toolchain.
Run the Dev Containers CLI through `bunx @devcontainers/cli`; a global CLI
installation is unnecessary. The agent can remain in agentdev while its shell
tool targets a sibling checkout.

Read that checkout's `AGENTS.md` and devcontainer configuration first. Set the
shell tool's working directory to the target repository root for the commands
below; `--workspace-folder` identifies the same absolute checkout explicitly.
This also gives host-side lifecycle commands the target repository context.

``` bash
workspace="$PWD"
docker info
bunx @devcontainers/cli up --workspace-folder "$workspace"
bunx @devcontainers/cli exec --workspace-folder "$workspace" pwd
```

Docker must be reachable from the agent's shell; run `docker compose version` to
check Compose availability when the target configuration uses Compose. With a
remote or outer Docker daemon, bind-mount source paths must also exist on the
daemon's filesystem. Use the target's configured socket and Docker-in-Docker
arrangement; socket mounts are deployment-specific.

`up` applies the target's image pins, Compose files, features, mounts, and
lifecycle hooks. Use its returned `containerId` and `remoteWorkspaceFolder` when
inspecting processes or copying artifacts. The container workspace can differ
from the host path: use the configured container workspace for paths inside
`exec`, and the host checkout for `--workspace-folder`. Named build and log
volumes may hide artifacts from the host checkout even when source edits are
bind-mounted.

## Build and test execution

Pass the target repository's commands and environment wrappers through `exec`.
Keep test and build selectors narrow unless the user requests a full run.
Install dependencies using that repository's documented workflow; its
development virtual environment and runtime interpreter can have different
dependencies.

Use direct argument passing for a single command. Use an explicit shell when the
target's documented command needs shell syntax, such as a pipeline or
environment activation. For example, after assigning `build_command` and
`test_command` to the target's documented shell commands:

``` bash
bunx @devcontainers/cli exec --workspace-folder "$workspace" \
  bash -lc "$build_command"
bunx @devcontainers/cli exec --workspace-folder "$workspace" \
  bash -lc "$test_command"
```

Use a shell available in the target image; the example assumes Bash. Preserve
the target's environment wrappers, working directory, test mode, and coverage
flags. After correcting an environment failure, use its runner's failed-test
selector or rerun the affected scope. Report test success separately from
coverage collection: passing tests do not establish that a coverage report
contains data.

## Public GHCR pulls and credential isolation

Public GHCR images support anonymous pulls. The package REST API's
`read:packages` requirement does not establish that an anonymous image pull
needs that scope. A registry denial with the default Docker configuration can be
diagnosed against a credential-free configuration without changing the user's
login state:

``` bash
mkdir -p .tmp/docker-anonymous
DOCKER_CONFIG="$PWD/.tmp/docker-anonymous" \
  bunx @devcontainers/cli up --workspace-folder "$workspace"
```

Compare the same image and digest with both configurations. If anonymous access
succeeds and the configured access fails, investigate the configured credentials
or credential helper. Keep the isolated `DOCKER_CONFIG` on related CLI
invocations while diagnosing. Private images still require authorized registry
credentials; preserve image pins while resolving access.

## Completion and artifacts

Give long builds and integration tests sufficient execution time. If a shell
tool times out, inspect the container's process state before retrying: losing
the client connection does not prove that the container-side test stopped. Avoid
overlapping runs against shared build and test-result directories.

Collect the target runner's build logs, test reports, and coverage artifacts. If
they live in a container volume, copy them using the container ID returned by
`up`. Set `container_id` from that result and `container_artifact_dir` to the
absolute artifact directory inside the container:

``` bash
mkdir -p .tmp/test-artifacts
docker cp "${container_id}:${container_artifact_dir}/." .tmp/test-artifacts/
```

Keep artifacts under the target repository's `.tmp/`. Record the final
test-result summary and whether the container remains running. Container
shutdown follows the target's documented lifecycle. For Compose targets, include
all configured override files and the correct project identity. Persistent
volumes retain build state between executions.
