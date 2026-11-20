---
type: adr
stage: accepted
description: 'The OpenCode bridge registers skills under their bare names and commands as agentdev:<name>, and the skill tool strips an agentdev: prefix.'
---

# Skills keep their bare names, and commands have a namespace

The OpenCode bridge registers each skill under the bare `name` of its
frontmatter, and each command as `agentdev:<name>`. The skill tool strips an
`agentdev:` prefix, because the catalog text names sibling skills as
`/agentdev:<name>`. The bridge registers its own commands because OpenCode
excludes its own skill-derived commands from autocomplete.

## Considered Options

- Register v2 skills under `agentdev:<name>` IDs. Rejected: the model would then
  fail to load a skill under its bare frontmatter name, which the catalog also
  uses.
- Bare `<name>` commands. Rejected: they would rank higher on `/pr`, but they
  would differ from the names in Claude Code and could collide with the bare
  skills of other plugins; the namespaced ranking is usable.
- Rewrite the catalog text to "the `<name>` skill". Rejected: it rewrites more
  than 100 `/agentdev:<name>` references and makes invocation in Claude Code
  less precise, for a gap that the prefix rewrite closes.

## Consequences

- The `agentdev:<name>` command of an explicit-only skill still runs, because
  the skill permission does not apply to commands.
- A skill or a command that the user defines with the same name replaces the one
  from the bridge. On v1, the bridge does not change a key that the user
  configuration already defines.
