---
type: someday
description: A VS Code Dev Containers window forwards the Mac's SSH and GPG agent sockets into the container, so any container process can sign and authenticate with the user's keys; research whether this can be narrowed without breaking the workflows that rely on it.
generated:
  by: claude-code/opus-4.8
  at: 2026-10-21T00:00:00Z
sources:
- resource: docs/knowledge/data/plans/20261015-vscode-expo-bridge.md
---

# Narrow the devcontainer's forwarded agent exposure

A spike for the [VS Code Expo bridge](../plans/20261015-vscode-expo-bridge.md)
found, while establishing that the bridge adds no reach a devcontainer window
does not already grant, that VS Code's Dev Containers forwards the Mac's SSH
agent (`SSH_AUTH_SOCK`) and GPG agent into the container. From a container
shell, `ssh-add -l` listed the user's private keys. Any process in the container
— not only an extension, and not the bridge — can therefore sign and
authenticate as the user for as long as the window is open.

This is a devcontainer-wide exposure, independent of the Expo bridge: nothing in
this repository's `.devcontainer/` opts into it, and nothing the bridge installs
changes it. It is recorded here rather than as a bug because the root cause and
any fix are not yet established — the forwarding is VS Code's own default
behavior, and narrowing it has to be weighed against the git and signing
workflows that depend on it.

What research would settle:

- Whether the forwarding can be turned off or scoped per workspace without a
  change VS Code does not support, and what breaks when it is (git over SSH,
  commit signing, `gh` auth).
- Whether a narrower agent — one that prompts on the Mac per signature, or
  exposes only a named key — is reachable from the Dev Containers configuration.
- What the exposure is worth addressing against: the window already grants the
  container a local terminal on the Mac, so a fix here narrows one reach among
  several rather than closing the boundary.

Closing this idea could mean a bug with a verified root cause and fix, a
documented decision that the exposure is accepted for the workflows it enables,
or a `.devcontainer/` change — the research decides which.
