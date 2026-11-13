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

### Requirement: Runtime code imports the standard library only

Every Python module the plugin ships outside `tests/` SHALL import only the
standard library and the plugin's own modules, so it imports with nothing but a
system `python3`, offline. A unit test SHALL walk every runtime module's syntax
tree and fail on any other import. Tests and development tooling are not bound
by the rule.

#### Scenario: A runtime module gains a third-party import

- **WHEN** a module under `selfimprove/` or `agent-code/` imports `yaml`
- **THEN** `tests/unit/test_no_runtime_deps.py` fails

### Requirement: One dispatcher runs every hook and command

`agent-code/si <subcommand>` SHALL be the plugin's only executable, invoked by
every hook and skill. It SHALL run `si.py` with the first interpreter of
`python3.14`, `python3.13`, `python3.12`, `/usr/bin/python3`, `python3`, and
`python` that is at least Python 3.12, and SHALL exit 0 doing nothing when none
is. When `SELF_IMPROVE_DISABLE` is `1`, every subcommand SHALL exit 0 doing
nothing. A capture subcommand that raises SHALL record a redacted error class
and exit 0.

#### Scenario: The plugin is disabled

- **WHEN** `SELF_IMPROVE_DISABLE=1` is set and any hook fires
- **THEN** `si` exits 0 without recording or reviewing anything

### Requirement: The state root resolves override first

Runtime state SHALL live under `SELF_IMPROVE_STATE_DIR` when set, otherwise
under `CLAUDE_PLUGIN_DATA` when set, otherwise under `self-improvement/` in the
Claude configuration directory (`CLAUDE_CONFIG_DIR`, default `~/.claude`).

#### Scenario: Both variables are set in a hook

- **WHEN** a hook runs with `SELF_IMPROVE_STATE_DIR` set and Claude Code has set
  `CLAUDE_PLUGIN_DATA`
- **THEN** state is written under `SELF_IMPROVE_STATE_DIR`

### Requirement: Capture is bounded, redacted, and fails open

The plugin SHALL record only bounded event metadata, and every capture path
SHALL fail open: a capture that errors, times out, or finds no usable input
SHALL leave the completed task undisturbed rather than surfacing an error.

`UserPromptSubmit` SHALL record session and prompt identifiers and detect
correction and retention markers, placing the prompt in an ephemeral turn file
only when a review signal requires it. `PostToolUseFailure` SHALL record tool
category, normalized operation signature, error class, and turn identifier —
nothing that Requirement: Durable state is private and carries no raw content
forbids. `PostToolUse` SHALL pair a successful operation with a prior compatible
failure to produce a `failed_then_succeeded` signal deterministically.

#### Scenario: A capture hook fails

- **WHEN** any capture or gating step raises, times out, or receives unparseable
  input
- **THEN** the hook exits successfully, the completed task is preserved, and
  only a redacted error class is recorded

### Requirement: The Stop hook orchestrates without delaying the response

The `Stop` hook SHALL be configured with `asyncRewake` and SHALL return
immediately, so the primary response is never delayed by review. It SHALL skip
when `stop_hook_active` is true, while relevant background work or session
wakeups remain active, and for reviewer-originated or plugin-generated sessions.
It SHALL run the deterministic gate, invoke the reviewer only when the gate
passes, and use the `asyncRewake` signal only for a valid candidate.

#### Scenario: The session is reviewer-originated

- **WHEN** `SELF_IMPROVE_REVIEWER` is set in the session's environment
- **THEN** reflection is suppressed, preventing recursion

### Requirement: A deterministic gate decides whether to spend a review

Model review SHALL be requested only when at least one supported signal exists:
explicit retention, explicit correction, a verified workaround, repeated
friction, a confirmed technique, a reusable completion, or manual force via
`/self-improve:improve`. A signal SHALL be permission to reflect, not proof that
a lesson exists.

Explicit retention SHALL be recognized by the adverb in any instruction rather
than by a fixed list of verbs, so that a bare standing directive qualifies with
or without a stated reason. The same words describing the world rather than
instructing SHALL NOT be a signal.

The gate SHALL enforce at most one reviewer invocation per completed user turn,
at most one candidate per review, cooldown and daily invocation limits, proposal
fingerprint deduplication, and recursion guards.

#### Scenario: A bare standing directive arrives

- **WHEN** the user writes an instruction opening with a standing adverb, such
  as "always use `make test` here", carrying no rationale
- **THEN** the gate treats it as explicit retention and permits review

#### Scenario: The same words describe rather than instruct

- **WHEN** the user writes "the build always fails on CI"
- **THEN** the gate reads no signal and spends no review

#### Scenario: A directive follows unrelated inferred work

- **WHEN** the cooldown is armed by an automatically inferred signal and the
  user then states an explicit correction or retention request
- **THEN** the cooldown does not suppress it, because it will not be repeated

#### Scenario: The daily limit is reached

- **WHEN** the daily invocation ceiling is exhausted
- **THEN** every automatic signal is suppressed, including explicit ones, while
  manual force still passes

### Requirement: The reviewer is isolated and cannot mutate anything

The reviewer SHALL run as a separate Claude call with fresh context, a
reviewer-only system prompt, plugin hooks disabled, and no tools at all. Its
entire evidence bundle SHALL arrive on standard input, gathered
deterministically by the orchestrator, so it needs no filesystem access. It
SHALL use the user's configured authentication and introduce no separate
credential.

The reviewer SHALL receive only bounded current-turn event records, the current
prompt where a detected correction requires it, the final assistant message, a
redacted failure-to-success summary, candidate owner summaries and paths, and
the fingerprints needed for deduplication — never unrelated transcripts,
credentials, environment dumps, or unrestricted filesystem access.

The reviewer SHALL run the `claude` binary, or `SELF_IMPROVE_REVIEWER_CMD` when
set, with the model `SELF_IMPROVE_REVIEW_MODEL` (default `sonnet`) and a timeout
of `SELF_IMPROVE_REVIEW_TIMEOUT` seconds (default 120). Its effort SHALL be
passed as `CLAUDE_CODE_EFFORT_LEVEL` in its environment, set from
`SELF_IMPROVE_REVIEW_EFFORT` (default `medium`), never as an `--effort` flag; an
empty setting SHALL remove any inherited effort level. Its environment SHALL set
`SELF_IMPROVE_REVIEWER=1` and SHALL drop `SELF_IMPROVE_STATE_DIR` and
`CLAUDE_PLUGIN_DATA`.

#### Scenario: The reviewer is invoked

- **WHEN** the gate passes and review begins
- **THEN** the reviewer runs with no tools, hooks disabled, and a single turn,
  and cannot read, write, or execute anything

### Requirement: Reviewer output is strict, and a decline names its category

The reviewer SHALL return structured data carrying its decision, signal type,
evidence summary, lesson, applicability, counterexample, destination scope and
kind, owner query, and confidence. Malformed output, low confidence, unsupported
destinations, and policy violations SHALL become a discard. The reviewer SHALL
NOT emit final file bytes.

A discard MAY name a category from a fixed set, and that category SHALL be
journaled as the review's outcome; an absent or unrecognized value SHALL be
dropped with the discard standing rather than escalated to a schema failure.

Every review ending without a candidate SHALL record its outcome — a decline
with its category, a transport or schema failure with its error class, or a
suppressed duplicate with its fingerprint status — because all three otherwise
leave identical durable state.

Brevity SHALL NOT be grounds for discard: a stated directive is explicit
evidence even when the user supplies no rationale, and the reviewer SHALL
propose the behavior stated rather than invent a justification for it.

#### Scenario: A discard carries an unrecognized category

- **WHEN** the reviewer returns a discard whose category is absent or outside
  the fixed set
- **THEN** the value is dropped and the discard stands

### Requirement: Routing prefers an existing owner over a new artifact

After a valid reviewer result, the flow SHALL search loaded and existing
instructions, rules, and skills, preferring in order: patch the loaded owner,
patch an existing class-level umbrella, add or patch a linked reference owned by
an umbrella, then propose a new skill only when no suitable owner exists.

A proposal SHALL patch one explicitly selected artifact or create one skill. It
SHALL NOT perform broad configuration cleanup, delete artifacts, modify
Claude-managed auto-memory, rewrite hooks or settings, or consolidate files.

#### Scenario: A suitable owner already exists

- **WHEN** the lesson belongs to an artifact already loaded or present
- **THEN** the proposal patches it rather than creating a new skill

### Requirement: The mutator enforces a normative path allowlist

A proposal SHALL target only `~/.claude/CLAUDE.md`, `~/.claude/rules/*.md`,
`~/.claude/skills/<name>/SKILL.md`, `./CLAUDE.md`, `./.claude/CLAUDE.md`,
`./.claude/rules/*.md`, or `./.claude/skills/<name>/SKILL.md`. The list SHALL be
enforced by the mutator, never by the reviewer or any model-authored
instruction. Everything else SHALL be rejected, including `settings.json`, hook
configuration, Claude-managed auto-memory, and arbitrary source files.

Paths SHALL be resolved to their real location before the check, with
containment and shape both decided on the resolved path. A symlink for the
target itself SHALL be refused, as SHALL any symlinked component between an
allowed root and the target; components above the root SHALL NOT be checked,
because symlinked prefixes are ordinary and rejecting them would refuse most
scratch directories while protecting nothing.

`AGENTS.md` SHALL be excluded even where a repository keeps its instructions
there, because Claude Code does not load it directly; such a lesson routes to
the importing `CLAUDE.md` or to a rule.

#### Scenario: The target is a symlink

- **WHEN** a proposal's target, or a path component between it and its allowed
  root, is a symlink
- **THEN** the mutation is refused before any I/O

### Requirement: Mutation is authorized by the user against exact bytes

A candidate SHALL be inert until the user enters an explicit command carrying
its identity and displayed hash prefix. Authorization SHALL be a one-time record
derived from that literal user prompt, accepted only from a
`UserPromptExpansion` event whose `expansion_type` is `slash_command` and whose
`command_source` is the plugin. The `UserPromptExpansion` hook SHALL register a
wildcard matcher and select the command inside the script, so a namespaced
command name it did not anticipate is still seen. Invocation by Claude through
the `Skill` tool, a model-generated tool call, or approval of a summary SHALL
NOT authorize mutation.

`apply` SHALL consume a matching unexpired authorization, validate the proposal
ID and content hash against the displayed prefix, resolve and check the target,
require the target's current hash to match the proposal preimage, create a
mode-preserving fsynced backup, atomically install exactly the approved bytes,
re-read and verify the installed hash, append a redacted mutation record, and
invalidate the proposal and token.

On any pre-install failure the target SHALL remain unchanged. On an interrupted
or ambiguous installation, the next command SHALL reconcile observed hashes
before allowing another mutation. `rollback` SHALL perform the same checks in
reverse and SHALL NOT overwrite a target that changed independently.

#### Scenario: The target changed since the proposal was staged

- **WHEN** the target's current hash does not match the proposal preimage
- **THEN** application is refused and regeneration is required

### Requirement: Durable state is private and carries no raw content

Runtime state SHALL be private to the user, with directories created mode `0700`
and files mode `0600`, separated into ephemeral per-turn input deleted after
review or expiry, staged immutable proposals, one-time authorization records,
verified mutation backups, and redacted diagnostics and fingerprints.

Durable state SHALL NOT contain raw prompts or assistant responses, transcript
bodies, credentials, tokens, cookies, environment values, raw tool output, full
shell commands with arguments, or unrelated project file content. The plugin
SHALL NOT edit or parse Claude-managed auto-memory internals.

#### Scenario: A review completes

- **WHEN** the reviewer returns and the turn's ephemeral data is no longer
  needed
- **THEN** that data is deleted, and what persists holds no raw transcript,
  prompt, credential, or tool-output body

### Requirement: Every failure mode stays silent and preserves the task

Reviewer timeout, authentication failure, or malformed output SHALL stay silent
and record only a redacted error class. Reviewer *unavailability* SHALL be
recorded as a class naming a provider failure — rate limit, overload, usage
limit, unreachable model, or other API error — distinctly from a review that ran
and proposed nothing, since the class is all a later investigation has.

When no session is available as review completes, the candidate SHALL be
retained for explicit retrieval at the next session start, with no mutation. A
user rejection SHALL invalidate the candidate and retain only its fingerprint
and reason category. A backup or verification failure SHALL NOT claim success.

#### Scenario: No session is available to wake

- **WHEN** review completes with no session to receive the wake
- **THEN** the candidate is retained and reported at the next session start

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

### Requirement: Live tests are opt-in at collection

The plugin's `tests/conftest.py` SHALL skip, at collection, every test marked
`smoke` or `pty` unless `SELF_IMPROVE_RUN_LIVE` is set to a value other than
empty, `0`, `false`, `no`, or `off`, and each skip SHALL name the variable. The
harness self-check against a fake terminal SHALL run in the ordinary suite.

#### Scenario: A live test is named by path

- **WHEN** `pytest` is given the path of a `smoke` test and
  `SELF_IMPROVE_RUN_LIVE` is unset or `0`
- **THEN** the test is skipped and spends no model usage

### Requirement: The root Makefile runs the plugin's checks

The repository-root `Makefile` SHALL provide the live-session targets `smoke`,
`smoke-auto`, `wake`, `wake-memory`, and `wake-repeat`, each setting
`SELF_IMPROVE_RUN_LIVE`; `test-harness`, which runs the `harness` marker without
it; `validate`, which runs `claude plugin validate` on the plugin and on the
repository root, skipping when no `claude` CLI is on `PATH`; and `check`, which
runs `test` and `validate`. It SHALL have no formatting or linting target; those
belong to the pre-commit hooks.

#### Scenario: A developer runs the default checks

- **WHEN** a developer runs `make check`
- **THEN** the test suite and manifest validation run
- **AND** no live test spends model usage

#### Scenario: wake-repeat meets a failure

- **WHEN** one of `wake-repeat`'s ten consecutive live runs fails
- **THEN** the target stops at that run and exits nonzero

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
