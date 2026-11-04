# Cloud environment with agentdev

The repository is checked out on the session host, outside its devcontainer.
`.claude/startup.py` has already brought the devcontainer up. The host has none
of the project toolchain; the devcontainer has all of it. Follow the
`/agentdev:devcontainer-sandbox` skill to run tools there.

## Commit and push only through the devcontainer

The git hooks run `pre-commit`, which exists only in the devcontainer. On the
host, `git commit` and `git push` fail with `No module named pre_commit`.

- ALWAYS run `git commit` and `git push` inside the devcontainer. The checkout,
  and every worktree under it, is mounted at the same path there:

  ```bash
  devcontainer exec --workspace-folder <repo-root> bash -lc 'cd <repo-root> && git commit -F .tmp/commit-msg.txt'
  ```

- Write the commit message to a file under `./.tmp` and pass it with `-F`. A
  message given inline breaks the quoting of `bash -lc '...'` as soon as it
  holds an apostrophe.
- NEVER pass `--no-verify` or otherwise skip the hooks to commit or push from
  the host.
- The devcontainer carries the host's git identity, and `gh` and `git push`
  authenticate through the session's agent proxy. When either fails there,
  report it; do not fall back to the host.

## Worker restarts

The session's worker restarts often, sometimes in the middle of a turn. A
restart reboots the session host: the disk survives — the checkout, `./.tmp`,
Docker images, and the stopped devcontainer — and every process stops, including
the host `dockerd`, the agent proxy relay, the devcontainer, and any background
command you started.

- **Recognize it.** `Cannot connect to the Docker daemon` on the host, a failing
  `devcontainer exec`, or `git` and `gh` in the container failing with
  `Failed to connect to host.docker.internal`. A short `uptime` confirms it.
- **Restore it.** Run `.claude/startup.py resume` from the repository root. The
  `SessionStart` hook runs it when a session starts; after a restart inside a
  turn, run it yourself. It keeps whatever still runs, restarts the rest, and is
  safe to run again.
- **Pick up the interrupted work.** Restart any background command that died,
  and check `git status` and whether the last commit reached the remote before
  continuing.
- **Keep a restart cheap.** Commit and push at checkpoints, keep scratch in
  `./.tmp`, and prefer commands that can simply be run again.
- While diagnosing, never print `GH_TOKEN` or `.devcontainer/cloud-session.env`,
  which holds it.

## GitHub access

The session's proxy refuses GitHub GraphQL, which `gh pr` and `gh issue`
subcommands use. Call REST routes with `gh api` instead, for example
`gh api repos/<owner>/<repo>/pulls/<n>` in place of `gh pr view <n>`.

- A skill script that calls GraphQL fails with `GH_UNAVAILABLE`. Do its step
  through REST where the skill allows a fallback; otherwise report the blocker
  and say what the user can do by hand.
- `gh auth status` reports the token as invalid for the same reason; REST calls
  with it work.
- `agentdev-runtime doctor` fails its `gh auth`, `git credential helper` and
  `github.com` checks here although auth works; see
  `docs/knowledge/data/bugs/doctor-fails-healthy-claude-cloud-devcontainer.md`.
