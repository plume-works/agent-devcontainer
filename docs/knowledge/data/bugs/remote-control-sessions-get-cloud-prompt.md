---
type: bug
stage: pending
severity: medium
description: Sessions spawned by `claude remote-control` on an agentdev container receive Claude Code's cloud-session instructions, which wrongly state that the session runs in Anthropic's cloud without `gh`, and those instructions override this repository's own workflow.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/remote_control.py
- resource: .claude/startup.py
- resource: openspec/specs/claude-remote-control/spec.md
- resource: https://code.claude.com/docs/en/remote-control
- resource: https://code.claude.com/docs/en/claude-code-on-the-web
---

# Bug: Remote Control sessions on a workspace receive cloud-session instructions

## Symptom

A session spawned by `claude remote-control` on a Coder workspace is told it
runs in a managed cloud environment. The instructions state that `gh` is
unavailable and may be used only for search, and that every other GitHub
operation goes through `mcp__github__` tools. None of that holds on the
workspace: `gh` is installed and authenticated, the session has no
`mcp__github__` tools, and the checkout is not ephemeral.

The session then refuses or delays work the user asked for. `/agentdev:pr-open`
names `gh` as its primary client, and the injected rule forbids it, so a pull
request is not opened until the user overrides the rule. The same text also adds
its own commit, push, attribution, and pull-request rules on top of `AGENTS.md`.

## Reproduction

1. Run with `AGENTDEV_CLAUDE_RC_MODE=server`, so the `claude-remote` tmux
   session runs `claude remote-control --spawn worktree`.
2. Start a session from claude.ai or the Claude app.
3. On the workspace, read
   `~/.claude/bridge-spawn/<session>/append-system-prompt.txt`.

The file opens with `# Your current remote execution environment` and contains
`Use gh only for search`. Its SHA-256 equals the session's
`CLAUDE_CODE_BRIDGE_PROMPT_SHA256`, and the session process receives it through
`--append-system-prompt-file`. `gh pr create` works from the same session.

Measured on Claude Code 2.1.316.

## Root cause

Server mode spawns each session as
`claude --print --sdk-url https://api.anthropic.com/v1/code/sessions/<id>`. The
server stages that session's `append-system-prompt` launch argument into the
file above. The text is written for Anthropic-hosted sessions and is not
adjusted for `CLAUDE_CODE_ENVIRONMENT_KIND=bridge`, although the Remote Control
documentation says the session keeps the local environment, tools, and project
configuration.

Nothing in this repository writes the text. Its origin outside the workspace is
inferred: the launch argument reaches the local server from the session's work
item, and sessions here have carried two different versions of the file.

Eliminated:

- **The repository.** No file under version control contains the text.
- **A client switch.** `claude remote-control --help` and the Remote Control
  documentation offer no flag, setting, or variable for spawned sessions'
  prompts, and the server refuses `--settings` ([Claude Remote Control server
  mode](../../../../openspec/specs/claude-remote-control/spec.md#rationale)).

## Potential solution

The text cannot be removed from this side, so the workspace has to state the
facts that correct it, and the defect should be reported to Anthropic.

- **Correct it at session start.** Have the repository's `SessionStart` hook,
  `.claude/startup.py`, detect `CLAUDE_CODE_ENVIRONMENT_KIND=bridge` together
  with `AGENTDEV_RUNTIME_MODE`, and add context saying this is the user's own
  workspace, that `gh` is the GitHub client, and that `AGENTS.md` governs. It
  applies only where the text is wrong, and needs no change to the session's
  launch.
- **State the precedence in `AGENTS.md`.** One rule, for any harness instruction
  that describes the environment, covers text the hook cannot anticipate.
- **Use pinned-pane mode.** `AGENTDEV_CLAUDE_RC_MODE=session` runs an
  interactive `claude` instead of spawning through the server, so it may not
  receive the text. It gives up concurrent sessions, and whether it avoids the
  text is unconfirmed.

Rewriting `append-system-prompt.txt` or wrapping the spawned binary is rejected.
The server writes the file immediately before spawning an absolute path, and the
recorded hash ties the file to that session, so either would be a race against
Claude Code's internals that breaks without notice.
