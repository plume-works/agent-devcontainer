---
type: task
description: Port the agent-owned Ship/Implement e2e suite from bash to pytest, with an isolated clone and OpenCode server per test so scenarios can run in parallel.
stage: done
priority: high
created: 2026-10-19
generated:
  by: claude-code/opus-5.5
  at: 2026-10-19T06:30:00Z
sources:
- resource: scripts/e2e/20261007-agent-owned-ship-implement/run.sh
completed: 2026-10-19
---

# Port the agent-owned Ship/Implement e2e suite to pytest

Port the agent-owned Ship/Implement e2e suite
(`scripts/e2e/20261007-agent-owned-ship-implement/run.sh`) from bash to pytest.

## Why

The bash suite cannot run scenarios in parallel safely. Every scenario shares
one clone, one OpenCode background server on a fixed port, and one sandbox home
folder, so scenarios can affect each other, and a check like "no commit" can
pass without the agent ever touching the clone. Error handling depends on bash
errexit rules inside subshells, which can turn a failed step into a passing
check. Re-running one scenario means re-running all of them.

## Requirements

- Each test gets its own clone, created by a fixture under `./.tmp/`, so no
  scenario sees another's commits or plan changes.
- Each OpenCode test gets its own server, with its own port, home folder and
  password, stopped by the fixture even when the test fails.
- OpenCode is driven through the server's HTTP API, not the `opencode api`
  client. Every session names the clone's folder explicitly; the suite sets its
  own wait limit and pages through messages itself.
- One pytest test per scenario and harness (Claude Code, Codex, OpenCode), with
  each current check as an assertion that shows the relevant transcript excerpt
  when it fails.
- Safe to run in parallel with pytest-xdist, with the number of workers capped
  because all tests share the model provider's rate limits. A single scenario
  runs with `-k`.
- Uses the default OpenCode test models from `AGENTS.md` and runs through
  `uv run pytest`.
- Start with the OpenCode harness. Claude Code and Codex follow.
- The port keeps every existing check, compared scenario by scenario with the
  bash version, and no check gets weaker.

Not a user-visible change; release impact is internal.
