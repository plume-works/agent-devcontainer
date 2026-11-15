---
type: guide
description: How to supply the Git identity a Coder workspace's Dev Container uses.
---

# Supply the Git identity on Coder

Create or update the four Git identity secrets in the Coder account, named
`GIT_AUTHOR_NAME`, `GIT_AUTHOR_EMAIL`, `GIT_COMMITTER_NAME`, and
`GIT_COMMITTER_EMAIL`. Identity values are configuration, not credentials. But
supply them through Coder. Do not put them in the image.
