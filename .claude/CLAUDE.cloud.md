# Cloud environment with agentdev

The repository is checked out on the session host, outside its devcontainer.
`.claude/startup.py` has already brought the devcontainer up. The host has none
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

## Worker restarts

The session's worker restarts often, sometimes in the middle of a turn. A
restart keeps the disk — the checkout, `./.tmp`, Docker images, and the stopped
devcontainer — and stops every process: the host `dockerd`, the agent proxy
relay, the devcontainer, and any background command or monitor you started.

- **Recognize it.** `Cannot connect to the Docker daemon` on the host, a failing
  `devcontainer exec`, or `git` and `gh` in the container failing with
  `Failed to connect to host.docker.internal` mean the worker restarted;
  `uptime` confirms it.
- **Restore it.** Run `.claude/startup.sh resume` from the repository root. The
  `SessionStart` hook runs it when a session starts; after a restart inside a
  turn, run it yourself. It keeps whatever still runs and restarts the rest, and
  is safe to run again.
- **Container from before the fixed relay port.** When `git` in the container
  still fails on a `host.docker.internal` port other than 3128, its environment
  predates the fix: remove the container with
  `docker rm -f $(docker ps -aq --filter label=devcontainer.local_folder=<repo-root>)`
  and run `resume` again. The checkout is bind-mounted, so work in it is kept.
- **Pick up the interrupted work.** Restart any background command that died,
  and check `git status` and whether the last commit reached the remote before
  continuing.
- **Keep a restart cheap.** Commit and push at checkpoints, keep scratch in
  `./.tmp`, and prefer commands that can simply be run again.
- While diagnosing, never print `GH_TOKEN`, `HTTPS_PROXY`, or
  `.devcontainer/cloud-session.env`, which holds the token.

## GitHub access

The session's proxy refuses GitHub GraphQL, which `gh pr` and `gh issue`
subcommands use. Call REST routes with `gh api` instead, for example
`gh api repos/<owner>/<repo>/pulls/<n>` in place of `gh pr view <n>`.
`gh auth status` reports the token as invalid for the same reason; REST calls
with it work.
