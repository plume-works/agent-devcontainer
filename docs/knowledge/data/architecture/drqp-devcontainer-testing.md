---
type: architecture
description: Apply the sibling-devcontainer workflow to Dr.QP's ROS environment, colcon build and tests, generated Python requirements, and volume-backed logs.
generated:
  by: opencode/openai-gpt-6.1-sol
  at: 2026-10-18T19:34:45Z
sources:
- resource: https://github.com/Dr-QP/Dr.QP/blob/main/AGENTS.md
- resource: https://github.com/Dr-QP/Dr.QP/blob/main/.devcontainer/devcontainer.json
- resource: https://github.com/Dr-QP/Dr.QP/blob/main/scripts/ros-dep.sh
- resource: https://github.com/Dr-QP/Dr.QP/blob/main/docker/ros/deploy/install-overlay-python-requirements.py
---

# Dr.QP devcontainer testing

Apply [Testing sibling workspaces in
devcontainers](sibling-devcontainer-testing.md) for startup, workspace
targeting, registry diagnostics, and completion handling. Run the commands below
with the shell tool's working directory set to the Dr.QP checkout root. Read its
current `AGENTS.md` before choosing the test scope.

## Workspace and runtime environment

``` bash
workspace="$PWD"
bunx @devcontainers/cli up --workspace-folder "$workspace"
```

Dr.QP configures `/opt/ros/overlay_ws` as its container workspace. A host
checkout such as `/workspaces/Dr.QP` identifies the source tree for
`--workspace-folder`; ROS commands execute in the container workspace. Build,
install, and log directories are backed by named volumes, so inspect or copy
their contents from the container.

Always pass ROS commands through `scripts/with-ros-env.sh`. During iteration,
build with `--packages-up-to <package>` and test with
`--packages-select <package>`. A full build and test run requires an explicit
user request.

## Full workspace build and tests

``` bash
bunx @devcontainers/cli exec --workspace-folder "$workspace" \
  scripts/with-ros-env.sh python3 -m colcon build --symlink-install
bunx @devcontainers/cli exec --workspace-folder "$workspace" \
  env DRQP_TEST_MODE=slow scripts/with-ros-env.sh python3 -m colcon test \
  --return-code-on-test-failure --mixin coverage-pytest
bunx @devcontainers/cli exec --workspace-folder "$workspace" \
  scripts/with-ros-env.sh python3 -m colcon test-result
```

`DRQP_TEST_MODE=slow` enables the complete Gazebo launch suite. Keep
`--symlink-install` for Python coverage and hot reload, and
`--mixin coverage-pytest` for Python coverage collection. Inspect coverage
output independently of passing tests; a no-data warning means coverage is
incomplete.

## Post-build Python runtime requirements

The development virtual environment and ROS system interpreter have separate
dependencies. After building a fresh environment, `scripts/ros-dep.sh` installs
generated Python runtime requirements as well as unresolved rosdeps. If a built
package cannot import a declared Python runtime dependency and only the
generated requirements phase is needed, invoke its helper directly:

``` bash
bunx @devcontainers/cli exec --workspace-folder "$workspace" \
  scripts/with-ros-env.sh python3 \
  docker/ros/deploy/install-overlay-python-requirements.py build install
```

Run this phase when the dependency failure calls for it, not before every test.
After resolving the failure, rerun failed packages with the same test mode and
coverage settings:

``` bash
bunx @devcontainers/cli exec --workspace-folder "$workspace" \
  env DRQP_TEST_MODE=slow scripts/with-ros-env.sh python3 -m colcon test \
  --packages-select-test-failures --return-code-on-test-failure \
  --mixin coverage-pytest
bunx @devcontainers/cli exec --workspace-folder "$workspace" \
  scripts/with-ros-env.sh python3 -m colcon test-result
```

## Logs and reports

Inspect package test output in `log/latest_test/<package>/stdout_stderr.log` or
`streams.log` and build output in `log/latest_build/`. These paths are inside
`/opt/ros/overlay_ws`. For detailed test failures, run
`colcon test-result --all --verbose` through the same ROS wrapper.

Set `container_id` to the successful `up` result's `containerId`, then copy
volume-backed logs into the host checkout:

``` bash
mkdir -p .tmp/colcon-logs
docker cp "${container_id}:/opt/ros/overlay_ws/log/." .tmp/colcon-logs/
```

When stopping the environment with Compose, include both
`.devcontainer/docker-compose.yml` and `devcontainer-compose-pins.yml`, matching
the target's configuration and Compose project identity.
