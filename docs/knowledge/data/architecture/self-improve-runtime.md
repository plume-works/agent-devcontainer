---
type: architecture
description: The self-improve plugin's runtime decisions — standard-library-only code, one dispatcher, the state-root resolution order, reviewer isolation by tool removal, and the environment dials.
generated:
  by: claude-code/opus-5
  at: 2026-09-09T00:00:00Z
sources:
- resource: .agents/plugins/self-improve/scripts/si
- resource: .agents/plugins/self-improve/selfimprove/paths.py
- resource: .agents/plugins/self-improve/selfimprove/reviewer.py
- resource: .agents/plugins/self-improve/tests/unit/test_no_runtime_deps.py
---

# Self-improve runtime

How the [self-improve learning loop](../spec/self-improve-learning-loop.md) is
built, and why. The behavior itself is specified there; this records the
decisions that constrain any reimplementation of it.

## Runtime code imports the standard library only

Plugin runtime code must import successfully with nothing but a system
`python3`, offline. Hook scripts run inside Claude Code's environment rather
than one the plugin controls, capture hooks run on a five-second budget, and
every capture path must fail open. A third-party import there needs a bootstrap
step in precisely the code that must be most reliable.

Anthropic's `security-guidance` plugin shows the alternative's cost: a virtual
environment under `~/.claude/`, `pip` and network access, documented degraded
fallbacks for a failed install, and best-effort YAML because the plugin does not
install PyYAML for the user.

The rule splits by location, not preference. Runtime code is standard library
only; tests and development tooling are unconstrained and managed with `uv`. An
AST walk over every runtime module enforces it, failing on any non-stdlib import
— a rule checked by reading the imports rather than by trusting a manifest to
describe them.

The standard library covers hashing, JSON, unified diffs, subprocess timeouts,
advisory locking, and atomic replacement. What remains hand-written is a small
set of generic helpers — atomic write with fsync and mode preservation, a lock
context manager, a `name`/`description`-only frontmatter reader, and a flat
reviewer-output validator — beside domain logic no dependency provides.

This is independent of which interpreter version the runtime targets. In this
repository the baseline is the container's Ubuntu LTS Python, so the floor is
the repository's own `>=3.12`; only the stdlib-only rule is load-bearing. The
dispatcher still probes for a usable interpreter, because a hook inherits the
user's shell environment where `python3` is frequently a stale virtualenv.

## One dispatcher, not one executable per operation

`scripts/si <subcommand>` is the only executable. Hooks and skills both invoke
it, so there is one place that parses hook JSON from standard input and one
place that fails open. The normative separation of capture, review,
authorization, mutation, and rollback is realized as modules rather than as
separate executables — the separation is a property of the code, and duplicating
the fail-open entry logic across five scripts would put the most reliability-
critical path in five places.

## State root resolution order

Runtime state resolves as `SELF_IMPROVE_STATE_DIR`, then `CLAUDE_PLUGIN_DATA`,
then `~/.claude/self-improvement/`.

The explicit override precedes the plugin data directory because Claude Code
sets `CLAUDE_PLUGIN_DATA` in every hook environment it creates, discarding any
inherited value. An override that lost to it would have no effect on the hooks
that write state — the only place the setting matters.

## The reviewer is isolated by having no tools, not by an allowlist

The reviewer runs with `--tools "" --disallowedTools "*"`, hooks disabled, a
single turn, and its whole evidence bundle on standard input. Owner paths and
summaries are gathered deterministically by the orchestrator and inlined.

This is strictly stronger than the read-only artifact allowlist the design would
otherwise permit: an allowlist constrains what a tool may reach, while removing
the tools leaves nothing to constrain. The reviewer cannot read, write, or
execute anything, so the isolation does not depend on the allowlist being
correct.

Reviewer effort is carried by `CLAUDE_CODE_EFFORT_LEVEL` in that environment,
not by the `--effort` flag. Review failure is silent by design, so a CLI too old
to know the flag would abort every review with nothing on screen to explain it,
whereas an unrecognized environment variable is ignored and the review still
happens at the default level. Losing the saving is acceptable; losing the review
is not.

## The authorization event is chosen for what it can observe

Authorization is read from `UserPromptExpansion`, which Claude Code documents
for user-typed commands before their prompts reach Claude. This closes the
direct-command path a `PreToolUse` hook cannot observe.

The hook registers a wildcard matcher and selects the command inside the script
rather than in a matcher expression: the namespaced form reported in
`command_name` for a plugin skill is not guaranteed, and a matcher that failed
to match would silently discard the user's authorization rather than fail
loudly.

## Environment dials

| Variable                      | Purpose                                                              |
| ----------------------------- | -------------------------------------------------------------------- |
| `SELF_IMPROVE_REVIEW_MODEL`   | Reviewer model; defaults to `sonnet`                                 |
| `SELF_IMPROVE_REVIEW_EFFORT`  | Reviewer effort; defaults to `medium`. Empty accepts the CLI default |
| `SELF_IMPROVE_REVIEW_TIMEOUT` | Seconds to wait for the reviewer before giving up silently           |
| `SELF_IMPROVE_DISABLE`        | Set to `1` to disable the plugin without uninstalling it             |
| `SELF_IMPROVE_REVIEWER`       | Set in the reviewer's environment; suppresses reflection there       |
| `SELF_IMPROVE_REVIEWER_CMD`   | Overrides the reviewer binary; tests substitute a deterministic fake |
| `SELF_IMPROVE_STATE_DIR`      | Overrides the state root                                             |

## Why the wake needs a pseudo-terminal to verify

`asyncRewake` wakes an idle interactive session. A print-mode session has no
idle state to wake into: it finishes at `result`, and a probe plugin whose
`Stop` hook exited 2 after a delay produced no follow-up turn with stdin held
open. So the one behavior that distinguishes this plugin cannot be observed
through the stream-JSON interface the rest of the smoke suite uses, and its
automated check drives a real pty instead.

That harness asserts on plugin-controlled state and one plugin-controlled marker
— the candidate identifier it reads independently from disk — and on nothing the
interface renders. Screen-diffing, matching Claude's prose, and grading a
rendered proposal are all excluded: Claude Code redraws, uses an alternate
screen, and reflows on resize, and a byte comparison the headless checks already
make is stronger evidence than a model reading a terminal.
