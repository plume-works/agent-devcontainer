---
type: task
stage: done
priority: medium
created: 2026-11-02
completed: 2026-11-03
description: Delete the tests that check file contents or another tool's work instead of running behaviour, as the AGENTS.md Tests rule requires.
sources:
- resource: AGENTS.md
- resource: scripts/tests/test_agent_runtime_ci.py
- resource: scripts/tests/test_macos_bootstrap_pins.py
- resource: scripts/tests/test_claude_remote_control_start.py
- resource: https://github.com/plume-works/agent-devcontainer/pull/629
---

# Remove tests that check file contents instead of running behaviour

`AGENTS.md` `### Tests` says a test runs the behaviour it covers, and never
reads a repository file to check its text, keys, steps, or versions, checks that
two files agree, or checks that another tool did its job. These tests do exactly
that and are deleted with no replacement:

- `scripts/tests/test_agent_runtime_ci.py` —
  `test_renovate_tracks_the_pin_and_lets_its_tasks_edit_it`,
  `test_renovate_moves_every_dev_container_reference_together`, and
  `test_workflow_jobs_share_the_dev_container_pin`;
- `scripts/tests/test_macos_bootstrap_pins.py`;
- `test_compose_does_not_pass_setup_token` in
  `scripts/tests/test_claude_remote_control_start.py`.

The maintainer decided cross-file consistency tests go with no replacement: the
Renovate pin test checks only that Renovate did its job, cannot catch a new
usage written with an old pin, and when two pins diverged on `main` it failed
every pull request that merged `main` instead of preventing the divergence. This
settles the reviewer item [PR
#629](https://github.com/plume-works/agent-devcontainer/pull/629) left open.

Done when the listed tests are deleted and the remaining tests in those files
pass.
