---
type: adr
stage: accepted
description: Self-improve takes the authorization of the user only from the `UserPromptExpansion` hook, which has a wildcard matcher.
---

# Only a command that the user types authorizes a self-improve change

A `self-improve` proposal changes no file until the user types a command that
names it. The `UserPromptExpansion` hook sees each command that the user types,
before Claude gets its prompt. This event does not occur when Claude starts the
same skill through the `Skill` tool, so this hook is the only source of
authorization.

## Considered Options

- A `PreToolUse` hook. Rejected: it does not see a command that the user types
  directly.
- A matcher that names the commands. Rejected: Claude Code does not make sure
  that the `command_name` of a plugin skill has the namespaced form. A matcher
  that does not match removes the authorization of the user and shows no error.

## Consequences

- `.agents/plugins/self-improve/selfimprove/authz.py` creates authorization
  records only from this event, and it accepts the bare and the namespaced
  command names.
