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
