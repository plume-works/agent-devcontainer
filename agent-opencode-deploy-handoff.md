# agent-opencode: deploy and acceptance handoff

Deploy the candidate image, then run the acceptance checks for Tasks 16 and 37.
Never record a password, token, or login code in any evidence.

## The two pins

| Pin         | Image                                                                                                             | Built from                   | Native acceptance             |
| ----------- | ----------------------------------------------------------------------------------------------------------------- | ---------------------------- | ----------------------------- |
| **test**    | `ghcr.io/plume-works/agent-opencode:edge@sha256:da176dc457527d44f5d47e219a2556d1f0f9c98098c6145cc7eae6c91416817b` | `71da0d8`, the merge of #440 | 21 passed, 1 skipped per arch |
| **upgrade** | `ghcr.io/plume-works/agent-opencode:edge@sha256:d9be64188c55676ea4b3e8c821cdc42a0af903f9044b81a273c9b138d213e1f6` | `c4bfd68`, the merge of #441 | 22 passed, 1 skipped per arch |

Both were accepted on amd64 and arm64 and promoted to `edge` by main's CI/CD
(runs 40054975946 and 40064273950). Each is built on the `agent-desktop` image
promoted in the same run. Deploy and test on the **test** pin, and use the
**upgrade** pin only for the upgrade check in Task 16. The `edge` tag has moved
since, so the digest is what selects each image.

The full reference is `docker/opencode/README.md` (deployment guide) and the
README's `### Startup and failures` and `### Operating it`.

## 0. Prerequisites

- A Linux host, amd64 or arm64, with Docker Engine and the Compose plugin, that
  allows privileged containers.
- Two DNS names for the host: one for OpenCode, one for the Xpra desktop.
- A TLS reverse proxy that can join a Docker network. The guide uses Caddy.
- A GitHub token that can read the repository, if it is private.

## 1. Host setup

```bash
docker network inspect agentdev-proxy >/dev/null 2>&1 || docker network create agentdev-proxy
mkdir -p ~/agent-opencode && cd ~/agent-opencode
base=https://raw.githubusercontent.com/plume-works/agent-devcontainer/c4bfd6859b1ab8041f8924ef48de83c1166cc6a6
for f in compose.opencode.yml compose.opencode.bind.yml docker/opencode/runtime.env.example; do
  curl -fsSLO "$base/$f"
done
pin() { printf 'services:\n  opencode:\n    image: ghcr.io/plume-works/agent-opencode:edge@sha256:%s\n' "$1"; }
pin da176dc457527d44f5d47e219a2556d1f0f9c98098c6145cc7eae6c91416817b >pins-test.yml
pin d9be64188c55676ea4b3e8c821cdc42a0af903f9044b81a273c9b138d213e1f6 >pins-upgrade.yml
for f in pins-test.yml pins-upgrade.yml; do
  docker buildx imagetools inspect "$(awk '/image:/ {print $2}' "$f")" >/dev/null && echo "$f OK"
done
```

**Pass:** it prints `pins-test.yml OK` and `pins-upgrade.yml OK`. The compose
files come from `c4bfd68`, so both pins run against the same deployment files.

## 2. Settings

```bash
mkdir -p -m 700 ~/secrets
install -m 600 ~/agent-opencode/runtime.env.example ~/secrets/<project>.env
```

Fill in `OPENCODE_SERVER_PASSWORD` and `XPRA_PASSWORD` (two different random
secrets), `AGENTDEV_PROXY_NETWORK=agentdev-proxy`, and either
`AGENTDEV_REPOSITORY_URL` (clone mode) or `AGENTDEV_CHECKOUT` with
`AGENTDEV_UID`/`AGENTDEV_GID` (bind mode). Add `GH_TOKEN` if the repository is
private. Keep `ENABLE_FIREWALL=false` for these checks. Booleans accept `1`,
`true`, `yes`, `on`, `0`, `false`, `no`, `off`, or empty; anything else latches
the runtime with a configuration failure naming the variable.

## 3. Start and route

```bash
cd ~/agent-opencode
P=<project>; ENV=~/secrets/$P.env; PINS=pins-test.yml
up() { docker compose -p "$P" --env-file "$ENV" -f compose.opencode.yml \
  -f "$PINS" "$@"; }   # add -f compose.opencode.bind.yml for bind mode
up up -d
until s=$(docker inspect --format '{{.State.Health.Status}}' "$P-opencode-1"); \
  [ "$s" = healthy ] || [ "$s" = unhealthy ]; do sleep 10; done; echo "$s"
docker exec "$P-opencode-1" /opt/agentdev-runtime/runtime-health.sh status
```

**Pass:** `healthy`, and `status` reports `ready`. `degraded` means OpenCode
serves while optional work (Xpra, nested Docker, CBM, uv sync, pre-commit,
indexing) failed; `status` names it and its retry command. `failed` means the
runtime latched: PID 1 stays up, OpenCode is stopped, and nothing reruns. Record
the `status` output, then run the retry it names:

```bash
docker exec "$P-opencode-1" /opt/agentdev-runtime/runtime-supervisor.py retry [component]
```

Then add the two site blocks from the guide's section 5,
`<opencode-host> → $P-opencode-1:4096` and `<desktop-host> → $P-opencode-1:14500`,
and reloads the proxy.

## 4. Logins

- OpenCode at `https://<opencode-host>`: basic-auth user `opencode`, then
  connect a model provider in OpenCode's settings.
- Desktop at `https://<desktop-host>`: the Xpra password.
- Claude Code and Codex, from a shell in the container:

  ```bash
  docker exec -u agent -it <project>-opencode-1 bash
  claude        # log in, then exit
  codex login   # or the device-code flow from `codex login --help`
  ```

## 5. Task 16: logins and sessions behind the proxy

1. Create an OpenCode session with a recognizable title, and
   change one OpenCode user setting.
2. **Replace:** run `up up -d --force-recreate`, wait for `healthy`, and confirm in
   the browser that the provider login, the session, the setting, and the Claude
   Code and Codex logins all survived.
3. **Upgrade:** run `PINS=pins-upgrade.yml; up up -d`. The same state survives,
   and `docker inspect --format '{{.Config.Image}}' $P-opencode-1` names the
   upgrade digest, `sha256:d9be6418…`. Run the remaining steps on the upgraded
   container.
4. **Second project:** copy the env file to `~/secrets/$P2.env` with the
   same `AGENTDEV_UID`, `AGENTDEV_GID`, and `AGENTDEV_AUTH_VOLUME`, and start it
   with `-p $P2`.
5. **Separate OpenCode state:** in `$P2`, Claude Code and Codex are already logged in.
   OpenCode asks for its own provider login and lists none of `$P`'s sessions.
6. **Passwords:** from a throwaway container on the proxy network, check that the
   ports refuse requests without their passwords:

   ```bash
   docker run --rm --network agentdev-proxy curlimages/curl:8.11.1 \
     -s -o /dev/null -w '%{http_code}\n' http://$P-opencode-1:4096/api/info   # expect 401
   ```

   An Xpra session without `XPRA_PASSWORD` is refused: cancel the HTML5
   client's password prompt and it does not connect.

7. **Proxy:** OpenCode and the desktop both load through the proxy over TLS.

## 6. Task 37: restart the retained first-run deployment

This deployment is the one whose first start broke. Keep its home and workspace
volumes, and keep the firewall off.

```bash
P=<retained-project>; PINS=pins-test.yml; up up -d   # same project name, same volumes
until s=$(docker inspect --format '{{.State.Health.Status}}' "$P-opencode-1"); \
  [ "$s" = healthy ] || [ "$s" = unhealthy ]; do sleep 10; done; echo "$s"
docker exec "$P-opencode-1" /opt/agentdev-runtime/runtime-health.sh status
docker exec -u agent "$P-opencode-1" bash -lc \
  'grep -c "codebase-memory-mcp SessionStart" ~/.codex/config.toml; sha256sum ~/.codex/config.toml ~/.codex/hooks.json'
docker restart "$P-opencode-1"   # the second start
# wait for healthy again, then repeat the sha256sum line
```

**Pass:**

- The first start reaches `ready`, or a named `degraded` state, without any
  restart. `docker inspect --format '{{.RestartCount}}'` stays `0`.
- `config.toml` holds no `codebase-memory-mcp SessionStart` marker: the orphaned
  block was recovered into `hooks.json`.
- Both checksums are identical before and after the second start.

## 7. What to report back

Report the following, with no secrets, tokens, session contents, or login codes:

- the host's architecture and `docker version --format '{{.Server.Version}}'`;
- the image reference from `docker inspect --format '{{.Config.Image}}'`;
- each step's pass or fail;
- `runtime-health.sh status` for any `degraded` or `failed` state, with its
  `last-failure.json` component, reason, and exit status;
- the two checksum pairs for Task 37.

The implementing session then ticks Task 16 and Task 37 in
`docs/knowledge/data/plans/20261017-standalone-opencode-container.md` and
records the results under `## Verification results`.
