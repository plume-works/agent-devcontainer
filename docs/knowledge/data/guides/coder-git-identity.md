---
type: guide
description: How to supply the Git identity a Coder workspace's Dev Container uses.
---

# Supply the Git identity on Coder

Create or update the four Git identity secrets in the Coder account, mapped to
the exact `GIT_*` names the [Devcontainer Git credentials
spec](../spec/devcontainer-git-credentials.md) lists. Identity values are
configuration, not credentials, but they should still be supplied through Coder
rather than baked into the image.
