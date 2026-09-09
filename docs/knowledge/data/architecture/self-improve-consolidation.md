---
type: architecture
description: Why the self-improvement plugin lives in this repository as a second catalog plugin, and the constraints that placement creates.
generated:
  by: claude-code/opus-5
  at: 2026-09-09T00:00:00Z
sources:
- resource: https://github.com/plume-works/agent-self-improvement
  title: agent-self-improvement, merged at e94031a
- resource: .devcontainer/scripts/reinstall-agentdev-claude.sh
- resource: .devcontainer/scripts/reinstall-agentdev-codex.sh
- resource: ansible/roles/agentic_tools/defaults/main.yml
- resource: py_packages/validate_agent_files/validate_agent_files/core.py
---

# Self-improve consolidation

The `self-improve` plugin — a hook-driven experiential-learning engine for
Claude Code — is developed in this repository as a second plugin in the catalog,
alongside `agentdev`.

## Why one repository

The catalog is the set of behaviors agents have; the self-improvement loop is
how that set changes over time. They are one subsystem seen statically and
dynamically, which is why they share a checkout rather than a dependency edge.

The loop also needs somewhere durable to write. Its own design routes an
approved lesson to whichever artifact should own it, against a flat path
allowlist. This repository already has typed destinations and skills that route
into them, so the two designs converge on the same problem.

Rejected alternatives:

- **Two repositories, the loop consuming the catalog.** The original
  arrangement. It duplicates the lint, CI, lockfile, and Super-Linter pin
  surfaces, and the cost of keeping one such surface aligned is already high
  enough here to warrant the `sync-super-linter-tool-versions` skill.
- **Vendoring the loop as an unowned subtree.** Keeps the file layout but not
  the point: the loop is developed here, not merely carried.

## Placement is not activation

Publishing the plugin from the catalog and enabling it for consumers are
separate decisions, and only the first is made. `self-improve` registers seven
hook events, including `UserPromptSubmit`, `PostToolUse`, and a `Stop` hook with
an asynchronous rewake — a behavioral change to every session, not a packaging
change. Staging it into `agent-desktop` is a later decision that carries its own
evidence bar. A marketplace can publish a plugin that nothing enables.

## Constraints this placement creates

### The catalog is no longer single-plugin

`reinstall-agentdev-claude.sh` and `reinstall-agentdev-codex.sh` resolve the
plugin to install with `jq -er '.plugins[0].name'`, and
`agentic_tools_plugin_name` is a scalar. Marketplace *names* were deliberately
de-hardcoded so a rename needs no edit; plugin arity never was. A second entry
is otherwise installed never and uninstalled never — a silent no-op rather than
an error.

`validate_agent_files` is the exception: it already enumerates every plugin a
marketplace manifest publishes.

### The two ecosystems publish different plugin sets

`self-improve` ships no Codex manifest, and Codex integration is analysed but
unimplemented. The manifests are therefore asymmetric by design, and neither
should be made to mirror the other:

``` text
.claude-plugin/marketplace.json     -> agentdev, self-improve
.agents/plugins/marketplace.json    -> agentdev
```

### The runtime imports the standard library only

Hook scripts run inside Claude Code's environment on a five-second budget and
must fail open, so a third-party import would need a bootstrap step in precisely
the code that must be most reliable. Anthropic's `security-guidance` plugin
shows the alternative's cost: a virtual environment under `~/.claude/`, `pip`
and network access, and documented degraded fallbacks when that install fails.
An AST walk over every runtime module enforces the rule.

This is independent of which interpreter version the runtime targets. The plugin
arrived targeting Python 3.9 to survive an arbitrary developer machine — its
dispatcher probes for a usable interpreter because a shell's `python3` is
frequently a stale virtualenv. Here the baseline is the container's Ubuntu LTS
Python, so the floor is the repository's own `>=3.12` and the interpreter probe
remains. Only the stdlib-only rule is load-bearing.

### Live tests spend model usage and must be opt-in at collection

Parts of the suite drive real Claude sessions. Deselecting them by marker in
`addopts` is not sufficient protection, because the natural way to iterate on a
test — naming its path, or passing `-m` — replaces the filter and fires the
session. The guard is therefore a `pytest_collection_modifyitems` hook in the
plugin's own `tests/conftest.py` that skips the live markers unless an
environment variable opts in, so every entry point is covered and each skip
states its reason. The Makefile targets that own these runs set the variable.

The model-free harness self-check is deliberately outside the guard: it runs in
the ordinary suite.

## Where the merged material lives

| Material                              | Destination                               |
| ------------------------------------- | ----------------------------------------- |
| Plugin source, tests                  | `.agents/plugins/self-improve/`           |
| Case studies, hypothetical extensions | `docs/research/`                          |
| Implemented specs                     | plans, `data/spec/`, `data/architecture/` |
| Proposed, unimplemented specs         | `data/someday/`                           |
| Measured defects                      | `data/bugs/`                              |

Research is a plain folder, not graph material: it analyses other projects'
learning systems and asserts nothing about this one. Only implemented
specifications yield durable knowledge; the rest is recoverable from history.
