---
type: spec
description: The self-improve plugin's durable behavior — its standard-library runtime and single dispatcher, hook design, the meaningful-event gate, reviewer isolation and output, routing and the path allowlist, the mutation protocol, state and privacy, failure behavior, and how it is published without being enabled.
sources:
- resource: .agents/plugins/self-improve/hooks/hooks.json
- resource: .agents/plugins/self-improve/selfimprove/gate.py
- resource: .agents/plugins/self-improve/selfimprove/reviewer.py
- resource: .agents/plugins/self-improve/selfimprove/allowlist.py
- resource: .agents/plugins/self-improve/selfimprove/mutate.py
- resource: .agents/plugins/self-improve/reviewer/prompt.md
- resource: .agents/plugins/self-improve/agent-code/si
- resource: .agents/plugins/self-improve/agent-code/si.py
- resource: .agents/plugins/self-improve/selfimprove/paths.py
- resource: .agents/plugins/self-improve/selfimprove/config.py
- resource: .agents/plugins/self-improve/tests/unit/test_no_runtime_deps.py
- resource: .agents/plugins/self-improve/tests/conftest.py
- resource: Makefile
- resource: .claude-plugin/marketplace.json
- resource: .claude/settings.json
- resource: ansible/roles/agent_catalog/tasks/stage_catalog.yml
- resource: py_packages/agentdev_runtime/agentdev_runtime/catalog.py
- resource: .agents/plugins/self-improve/skills/apply/SKILL.md
---

# Self-improve learning loop

## Purpose

The plugin recognizes a verified correction or hard-won workflow, extracts the
reusable lesson, routes it to the artifact that should own it, and makes it
available to later sessions. Reflection is automatic; durable mutation is not —
every write is authorized by the user against one exact set of bytes.

The product claim is narrow: Claude can notice a meaningful experience and
propose retaining its lesson safely. It does not claim that a retained lesson
improves future behavior.

## Requirements

### Requirement: The plugin is published but not enabled by default

The catalog's Claude marketplace manifest SHALL publish `self-improve` beside
`agentdev`, and `agentdev-runtime catalog install` SHALL install every plugin
that manifest publishes. The image build SHALL stage and install only the plugin
named by `agent_catalog_plugin_name` (`agentdev`), failing when the manifest
publishes other than exactly one plugin of that name, and the committed
`.claude/settings.json` SHALL NOT enable `self-improve`.

#### Scenario: A developer reinstalls the catalog

- **WHEN** `agentdev-runtime catalog install` runs in a checkout
- **THEN** `self-improve` is installed and enabled in that checkout's local
  scope only, and no tracked file changes

## Rationale

### The plugin lives in this repository as a second catalog plugin

The catalog is the set of behaviours agents have and the learning loop is how
that set changes, so both share one checkout rather than a dependency edge, and
the loop routes approved lessons into destinations this repository already
types. Publishing the plugin and enabling it are separate decisions, and only
publishing is made: its seven hook events, including `UserPromptSubmit`,
`PostToolUse`, and an asynchronously rewaking `Stop`, change every session, so
enabling it by default carries its own evidence bar. Enablement is judged on
what the repository carries, not on one machine's local settings.

Rejected:

- **Two repositories, the loop consuming the catalog.** It duplicates the lint,
  CI, lockfile, and tool-version surfaces, each kept aligned across both.
- **Vendoring the loop as an unowned subtree.** It keeps the file layout but not
  the point: the loop is developed here, not merely carried.

### The runtime is standard-library Python behind one dispatcher

Hook scripts run inside Claude Code's environment rather than one the plugin
controls, on a five-second capture budget, and must fail open, so a third-party
import would need a bootstrap step in precisely the code that must be most
reliable. The rule is checked by reading imports, not by trusting a manifest.
Only the stdlib-only rule is load-bearing; the interpreter floor is the
repository's own, and the dispatcher still probes for an interpreter because a
hook inherits a shell where `python3` is often a stale virtualenv. One
dispatcher keeps hook-JSON parsing and fail-open handling in one place; the
separation of capture, review, authorization, mutation, and rollback is a
property of the modules, not of separate executables.

The state override precedes `CLAUDE_PLUGIN_DATA` because Claude Code sets that
variable in every hook environment, discarding an inherited value, so an
override that lost to it would never reach the hooks that write state.

Skills invoke the dispatcher as `${CLAUDE_PLUGIN_ROOT}/agent-code/si`, not by a
skill-relative path: the executable sits at the plugin root, not in a skill, and
the plugin is published only to Claude Code, which substitutes the variable.

Rejected:

- **Third-party runtime dependencies installed on demand** (a virtual
  environment under `~/.claude/`, `pip`, network access). They need degraded
  fallbacks when the install fails, in the code path that must not fail.
- **One executable per operation.** It repeats the fail-open entry logic, the
  most reliability-critical path, in each script.
- **A `pyproject.toml` and Python project of the plugin's own**, as
  `py_packages/validate_agent_files/` has. That isolation exists because the
  validator is released independently; the plugin is not.

### The reviewer is isolated by removing its tools

The reviewer runs with every tool removed, hooks disabled, one turn, and its
whole evidence bundle on standard input. Removing the tools leaves nothing to
constrain, so isolation does not depend on an allowlist being correct. Its
effort goes in the environment because review failure is silent: a CLI too old
for an `--effort` flag would abort every review unseen, while an unknown
variable is ignored and the review still runs at the default level.

Rejected:

- **A read-only artifact allowlist for the reviewer.** It constrains what a tool
  may reach, which is weaker than holding no tool.
- **The `--effort` flag.** Losing the saving is acceptable; losing the review is
  not.

### Authorization is read from the event that sees typed commands

Authorization comes from `UserPromptExpansion`, which fires for user-typed
commands before their prompts reach Claude, closing the direct-command path a
`PreToolUse` hook cannot observe. The matcher is a wildcard because the
namespaced form of a plugin skill's `command_name` is not guaranteed, and a
matcher that failed to match would silently discard the user's authorization.

### Live tests are guarded at collection

Deselecting live markers in `addopts` is replaced by every natural way to
iterate on a test — naming its path, passing `-m`, selecting a node id — each of
which would fire a paid session, so the guard is a collection hook that covers
every entry point and states its reason.
