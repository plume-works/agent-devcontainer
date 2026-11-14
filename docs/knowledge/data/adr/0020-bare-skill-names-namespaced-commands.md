---
type: adr
stage: accepted
description: 'The OpenCode bridge registers skills under their bare names and commands as agentdev:<name>, and the skill tool removes an agentdev: prefix.'
---

# Skills keep their bare names, and commands have a namespace

The OpenCode bridge registers each skill under the bare `name` of its
frontmatter, and each command as the namespaced command `agentdev:<name>`. The
catalog text names the other skills of the catalog as `/agentdev:<name>`, so the
skill tool removes an `agentdev:` prefix. The bridge registers its own commands,
because OpenCode does not show its skill-derived commands in autocomplete.

## Considered Options

- Register v2 skills under `agentdev:<name>` IDs. Rejected: the model then
  cannot load a skill under its bare name, which the catalog also uses.
- Bare `<name>` commands. Rejected: they are different from the names in Claude
  Code, and they can have the same name as a bare skill of a different plugin.
- Change the catalog text to "the `<name>` skill". Rejected: it changes more
  than 100 references, and it makes the invocation in Claude Code less accurate.

## Consequences

- The v1 `tool.execute.before` hook removes the `agentdev:` prefix from the
  `name` argument. The v2 `tool.hook("execute.before")` removes it from the `id`
  argument.
- An explicit-only skill gets `permission.skill.<name> = "deny"` on v1 and
  `autoinvoke: false` on v2. Its `agentdev:<name>` command still runs, because
  the skill permission does not apply to commands.
- A skill or a command that the user defines with the same name replaces the one
  from the bridge. On v1, the bridge does not change a key that the user
  configuration already defines.
