---
type: someday
description: Bringing the learning loop to Codex, with the six documented parity gaps that make it a redesign rather than a second manifest.
generated:
  by: claude-code/opus-5
  at: 2026-09-09T00:00:00Z
sources:
- resource: https://github.com/plume-works/agent-self-improvement
  title: agent-self-improvement at e94031a, spec 0003
---

# Codex integration for self-improve

Bring the [learning loop](../spec/self-improve-learning-loop.md) to the Codex
CLI without pretending that similarly named platform features have identical
semantics. Analysed, never implemented: no Codex package, hook adapter, reviewer
invocation, authorization flow, mutation, or smoke check exists.

This is why `self-improve` ships no Codex manifest, and why the two marketplaces
publish different plugin sets — recorded in
[Self-improve consolidation](../architecture/self-improve-consolidation.md).

## Why it is not just a second manifest

The Claude dependency is at every layer, not only in packaging: manifest and
marketplace schema, hook event names and `asyncRewake`, the `CLAUDE_PLUGIN_DATA`
state root, `prompt_id` turn identity, the `UserPromptExpansion` authorization
seam, `PostToolUseFailure`, `Stop`'s `last_assistant_message` and background
registries, `claude -p` with its tool- and hook-disabling flags, the
`destination_kind` names, the `~/.claude` allowlist layout, slash-command syntax
in the skills, and `claude plugin validate` in the build. Every one needs a
Codex adapter or an explicit finding that the behavior is already portable.

The shape that survives is one host-neutral learning engine with explicit
packaging, hook, reviewer, routing, and presentation adapters per host.

## The six parity gaps

- **GAP-1: no asynchronous idle-session wake.** Codex documents that
  asynchronous command hooks are unsupported. The Codex path must run a bounded
  *synchronous* review in `Stop` and return a continuation, which delays a
  signal-bearing turn by the reviewer timeout and must not be described as a
  wake. Emulating one with a detached process, by editing session files, or via
  an unrelated app-server instance is excluded. The gap closes only when an
  official same-session asynchronous callback is documented and observed.
- **GAP-2: no command-expansion provenance event.** With no
  `UserPromptExpansion`, an authorization may be minted only when the complete
  trimmed prompt matches one canonical grammar — no prefix, suffix, quote, code
  fence, prose, or embedded example — bound to session, turn, operation, object
  id, and hash prefix. That proves a host-supplied user prompt, not a keystroke,
  and the product must describe the boundary accurately.
- **GAP-3: no distinct tool-failure event.** Codex folds non-zero Bash
  completion into `PostToolUse` with no generic `error` field. The adapter needs
  fixture-backed classifiers, ignoring unknown response shapes rather than
  guessing; MCP errors, `apply_patch` failures, and hosted tools stay
  uncertified until their payloads are captured.
- **GAP-4: no documented "no tools at all" switch for `codex exec`.** Claude's
  reviewer removes every tool; Codex offers no equivalent flag. The replacement
  is a restrictive permission profile — no filesystem reads beyond minimal
  runtime paths, no writes, no network, no forwarded environment, no web search,
  MCP, plugins, skills, hooks, subagents, or memories, run from a private empty
  directory. The property to prove is stronger than a prompt saying not to use
  tools: attempts to read the project, home, plugin state, or environment and
  attempts to write must *fail* in acceptance tests. If the installed Codex
  cannot enforce that, the local-auth reviewer path is blocked, and the only
  acceptable fallback is a separately specified API reviewer with its own
  credential contract.
- **GAP-5: no behavioral equivalent of `.claude/rules/*.md`.** Codex `.rules`
  are command policy and must never receive model-authored prose, and its
  `AGENTS.md` chain is built once per run with no lazy path-glob rules. The
  router uses the active chain for short standing behavior and a skill for a
  procedure, never creates `AGENTS.override.md` automatically — it replaces
  rather than augments — and discards a candidate whose correctness depends on
  glob activation Codex cannot represent.
- **GAP-6: surface coverage.** Codex CLI only. Plugins are documented as
  unavailable in the IDE extension, so that is outside the plugin surface rather
  than merely untested; desktop, cloud, and ChatGPT Work share no assumed
  filesystem, plugin cache, hook process, or authentication state.

## What would have to be true first

Platform documentation is a design input, not acceptance evidence. Any
implementation must re-check these contracts against the tested Codex version
and record it, and the first packaged test must observe the exact prompt
delivered when a user invokes a namespaced plugin skill — until then GAP-2's
authorization is designed but unverified.
