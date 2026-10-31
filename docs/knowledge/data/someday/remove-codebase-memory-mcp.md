---
type: someday
description: Agents never chose the codebase-memory-mcp graph tools on their own and gained no accuracy when told to use them, so removal is the leaning, pending a test on a much larger codebase.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T22:00:00Z
sources:
- resource: AGENTS-codebase-memory-mcp.md
- resource: .devcontainer/scripts/runtime-supervisor.py
- resource: docs/knowledge/data/architecture/cbm-daemon-lifecycle.md
- resource: https://github.com/plume-works/Dr.QP
---

# Remove codebase-memory-mcp

The devcontainer runs codebase-memory-mcp (CBM): a daemon that indexes the
checkout into a code graph, an MCP server exposing graph queries
(`search_graph`, `trace_path`, `get_code_snippet`, `query_graph`), and hooks
that inject graph context at session start and before every Bash call. The
measurements below show agents getting no benefit from it on the codebases
tested. The leaning is to remove it; the open question is whether a much larger
codebase changes the result.

## Measurements

**Transcripts.** Across 386 Claude Code sessions (357 on four Coder workspaces
running this repository, 29 on a workspace running the Dr.QP ROS repository,
late September to October 2026), agents made no CBM tool call. The tools were
loadable in most sessions but are deferred behind `ToolSearch`, and no session
loaded them. The hooks injected graph context into 334 of the 357 sessions, and
many of those injections reported that no indexed project matched the working
directory.

**Controlled comparisons.** Headless agents answered code questions and made
refactors in fresh, indexed clones of this repository and of Dr.QP (about 25k
lines of Python plus about 6k of C++). Each task ran with CBM blocked, with CBM
available and unmentioned, and with the prompt telling the agent to use it.

| Round                   | Tasks                                                                                                                 | Runs |
| ----------------------- | --------------------------------------------------------------------------------------------------------------------- | ---- |
| Sonnet 5.5              | callers, call-path trace, rename impact, method rename                                                                | 72   |
| Opus 5.5, medium effort | C++ virtual-call trace, C++ signature impact, module extraction, ROS topic wiring, 61-site field addition, two traces | 48   |

- **No unprompted use.** With CBM available and unmentioned, 0 of 40 runs called
  it.
- **No accuracy gain.** Scored against ground truth from the code, every setup
  found the same lines and every refactor passed its tests. That included the
  traps: a module function sharing its name with a method, `monkeypatch` string
  targets, a call site in another package, implicit `std::vector` to `std::span`
  conversion, and publishers that must not be listed as subscribers.
- **Higher cost when used.** Told to use CBM, agents spent 24–56% more with
  Sonnet and 29–36% more with Opus, took longer, and in every run verified the
  graph's answer with grep before using it.

## Hypotheses eliminated

- **Agents don't know about CBM.** The MCP server instructions advertise it in
  every session and the hooks inject graph context into most of them, yet no
  session loaded it.
- **A stronger model would use it.** Opus at medium effort behaved the same as
  Sonnet.
- **It pays off on real code rather than on this repository's shell and YAML.**
  Dr.QP's Python and C++ showed the same result.
- **Static types are where the graph wins.** In Dr.QP's C++, `trace_path`
  outbound from `a1_16_hardware_interface::write` listed thirteen callees but
  not the virtual `servo->sendJogCommand` call that carries the command. In
  Python it missed cross-package calls on untyped receivers (`leg.solve_ik`),
  and qualified-name lookups returned "function not found".

## Operating cost

Observed with CBM 0.12.1:

- Every client on an account shares one cache directory; see [CBM daemon
  lifecycle](../architecture/cbm-daemon-lifecycle.md).
- A session in a git worktree queries the index of the main checkout, not its
  own tree.
- An index is keyed to the checkout path, so moving the checkout leaves an index
  for a path that no longer exists.

Bugs already filed against it include
[cbm-cache-under-foreign-owned-checkout](../bugs/cbm-cache-under-foreign-owned-checkout.md),
[cbm-start-failure-latches-degraded](../bugs/cbm-start-failure-latches-degraded.md),
and
[cbm-codex-hooks-block-foreign-tables](../bugs/cbm-codex-hooks-block-foreign-tables.md).

## Related measurement: the codebase map

The same transcripts showed no agent reading `data/codebase/` for orientation.
Told to start from the map, agents spent more and repeated map claims they did
not check, one of which was wrong while the digest check reported the map fresh.
In five of nine rename refactors of this repository, agents also edited a map
document the prompt never mentioned. [Remove the codebase
map](../plans/20261031-remove-codebase-map.md) acts on that.

## Promotion criteria

A test on a much larger codebase settles it: one where a grep for a common
symbol returns more matches than an agent can read (hundreds of thousands of
lines, ideally in a statically typed language), using the same three setups and
graded against ground truth.

- **Remove** — promote to a plan that deletes the daemon, the MCP server, the
  hooks, the image install, the supervisor's `cbm` and `index` services,
  `AGENTS-codebase-memory-mcp.md`, and the CBM agents and skill, if CBM again
  adds no accuracy or saves no cost.
- **Keep it opt-in** — promote to a plan that removes the hooks and automatic
  indexing but keeps the MCP server for explicit use, if CBM wins on that
  codebase.

Closing this without the larger test is also a valid outcome: removal on the
present evidence, recorded as a decision.
