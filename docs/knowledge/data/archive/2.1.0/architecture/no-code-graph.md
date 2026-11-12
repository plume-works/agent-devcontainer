---
type: architecture
description: The runtime ships no code-graph index; codebase-memory-mcp was removed because agents never chose it and gained no accuracy when told to use it, and the create phase clears what it left in persisted configuration.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/cbm_purge.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/agent_state.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/docker.py
---

# No code-graph index

## Decision

The maintainer removed codebase-memory-mcp (CBM) on the evidence below, without
the test on a much larger codebase that was once the condition for removal. The
images, the runtime, and the catalog ship no code-graph daemon, MCP server,
hook, or index. Agents orient with `grep` over the code plus the `spec/` and
`architecture/` documents.

## Evidence

Across 386 Claude Code sessions on this repository and Dr.QP, agents made no CBM
tool call, although the MCP server instructions advertised it in every session
and hooks injected graph context into most of them.

In 120 controlled runs in fresh, indexed clones of both repositories (about 25k
lines of Python and 6k of C++), each task ran with CBM blocked, available and
unmentioned, and named in the prompt:

- With CBM available and unmentioned, no run called it.
- Every setup found the same lines and every refactor passed its tests.
- Told to use CBM, agents spent 24–56% more with Sonnet 5.5 and 29–36% more with
  Opus 5.5, took longer, and verified the graph's answers with `grep` anyway.

The graph also missed calls that matter: virtual C++ dispatch, and cross-package
Python calls on untyped receivers.

## What a removal leaves behind

`codebase-memory-mcp install` wrote into user configuration, which outlives the
image in the `~/.claude` and home volumes. A hook that names a missing binary
fails on every tool call, and the tool's own `uninstall` is gone with the
binary. The create phase therefore runs
[`cbm_purge`](../../../../../../py_packages/agentdev_runtime/agentdev_runtime/cbm_purge.py),
which removes those entries by exact name and leaves everything else in the
user's files alone. The behavior is specified in [Catalog
lifecycle](../../../spec/catalog-lifecycle.md).

`cbm_purge` can be deleted once no supported instance can still hold a CBM
install. The `agentdev-cbm` volume is disposable, so the `docker-gc` service
reclaims it.

## Rejected alternatives

**Keep the MCP server opt-in.** Removes the hooks and automatic indexing but
keeps a pinned binary and its upgrades for a tool no run chose unprompted.

**Require a manual `uninstall` before upgrading.** Leaves the repository free of
CBM-named code, but anyone who misses the step gets a failing hook on every tool
call.
