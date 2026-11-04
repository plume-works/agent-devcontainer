# Cloud environment with agentdev

The repository is checked out on the session host, outside its devcontainer.
`.claude/startup.sh` has already brought the devcontainer up. The host has none
of the project toolchain; the devcontainer has all of it. Follow the
`/agentdev:devcontainer-sandbox` skill to run tools there.

## Commit and push only through the devcontainer

The git hooks run `pre-commit`, which exists only in the devcontainer. On the
host, `git commit` and `git push` fail with `No module named pre_commit`.

- ALWAYS run `git commit` and `git push` inside the devcontainer:

  ```bash
  devcontainer exec --workspace-folder <repo-root> bash -lc 'cd <repo-root> && git commit ...'
  ```

  The checkout is mounted at the same path in the container, so `<repo-root>`
  and worktrees under it resolve there too.

- NEVER pass `--no-verify` or otherwise skip the hooks to commit or push from
  the host.
- The devcontainer carries the host's git identity, and `gh` and `git push`
  authenticate through the session's agent proxy. When either fails there,
  report it; do not fall back to the host.

## GitHub access

The session's proxy refuses GitHub GraphQL, which `gh pr` and `gh issue`
subcommands use. Call REST routes with `gh api` instead, for example
`gh api repos/<owner>/<repo>/pulls/<n>` in place of `gh pr view <n>`.
`gh auth status` reports the token as invalid for the same reason; REST calls
with it work.
