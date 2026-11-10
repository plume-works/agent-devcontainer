---
type: bug
description: In the devcontainer of a Claude Code cloud session, the zizmor pre-commit hook fails with a 401 on any change to a GitHub workflow or action, because its online audits send the session's placeholder GH_TOKEN for repositories outside the session's GitHub scope.
sources:
- resource: .pre-commit-config.yaml
- resource: .claude/startup.py
- resource: docs/knowledge/data/architecture/cloud-session-host-toolchain.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/686
stage: done
severity: medium
---

# Bug: zizmor online audits fail in the cloud devcontainer

## Symptom

In the devcontainer of a Claude Code cloud session, a commit or push that
touches `.github/workflows/` or `.github/actions/` fails at the `zizmor` hook:

``` text
error in 'ref-confusion' audit
couldn't list branches for actions/github-script
HTTP status client error (401 Unauthorized) for url
(https://github.com/actions/github-script.git/git-upload-pack)
```

`zizmor --offline` on the same files passes.

## Reproduction

1. In a cloud-session devcontainer whose `GH_TOKEN` comes from
   `.devcontainer/cloud-session.env`, stage a change to any file under
   `.github/workflows/` that uses an action from outside the session's GitHub
   scope, such as `actions/github-script`.
2. Run `pre-commit run zizmor`.

## Root cause

`zizmor`'s online audits read `GH_TOKEN` and send it to GitHub for the
repositories of the actions a workflow uses. In a cloud session that token is
the placeholder the agent proxy replaces with the real credential. Through the
proxy, a `git-upload-pack` request with the token returns 200 for this
repository and 401 for `actions/github-script`, while the same request with no
token returns 200. The placeholder therefore works only for repositories in the
session's GitHub scope, and every other repository rejects it.

## Fix

`.claude/startup.py` merges `ZIZMOR_OFFLINE=true` into the `env` of the cloud
session's user-level `~/.claude/settings.json`, so the `zizmor` hook skips its
online audits in cloud sessions only. Every other host keeps them.
