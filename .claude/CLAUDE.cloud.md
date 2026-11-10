# Cloud environment with agentdev

The repository is checked out on the session host, and `.claude/startup.py`
has provisioned the project toolchain there: `uv` with the project environment,
`bun`, `iwe`, and the pinned binaries the pre-commit hooks call. Run tools,
tests, `git commit`, `git push` and `gh` directly on the host. Cloud sessions
run no devcontainer.

- The git hooks run `pre-commit` from the project environment. NEVER pass
  `--no-verify` or otherwise skip them.
- `git push` and `gh` authenticate through the session's agent proxy.

## Docker

The host runs `dockerd` for short-lived containers. Docker's client config
sends every `docker run` and `docker build` through a relay to the session's
agent proxy, so containers have network access with no extra flags. A container
that makes TLS requests also needs the host's CA bundle, for example
`-v /etc/ssl/certs/ca-certificates.crt:/etc/ssl/certs/ca-certificates.crt:ro`.
Never rely on a long-running container: a worker restart stops it.

## Worker restarts

The session's worker restarts often, sometimes in the middle of a turn. A
restart reboots the session host: the disk survives — the checkout, `./.tmp`,
and the provisioned toolchain — and every process stops, including the host
`dockerd`, the agent proxy relay, every container, and any background command
you started.

- **Recognize it.** A background command that vanished, or
  `Cannot connect to the Docker daemon`; a short `uptime` confirms it.
- **Restore Docker.** Run `.claude/startup.py resume` from the repository root.
  The `SessionStart` hook runs it when a session starts; after a restart inside
  a turn, run it yourself. It is safe to run again.
- **Pick up the interrupted work.** Restart any background command that died,
  and check `git status` and whether the last commit reached the remote before
  continuing.
- **Keep a restart cheap.** Commit and push at checkpoints, keep scratch in
  `./.tmp`, and prefer commands that can simply be run again.
- While diagnosing, never print `GH_TOKEN`.

## GitHub access

The session's proxy refuses GitHub GraphQL, which `gh pr` and `gh issue`
subcommands use. Call REST routes with `gh api` instead, for example
`gh api repos/<owner>/<repo>/pulls/<n>` in place of `gh pr view <n>`.

- A skill script that calls GraphQL fails with `GH_UNAVAILABLE`. Do its step
  through REST where the skill allows a fallback; otherwise report the blocker
  and say what the user can do by hand.
- `gh auth status` reports the token as invalid for the same reason; REST calls
  with it work.
