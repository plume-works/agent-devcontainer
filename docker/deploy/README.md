# Deploying agentdev-deploy

This guide takes a host from nothing to a running `agentdev-deploy` project behind
TLS, then shows how to check that logins and sessions survive replacement and
upgrade. The settings, storage, and operating reference is the
[Standalone OpenCode runtime](../../README.md#standalone-opencode-runtime) section of
the repository README.

## What you need

- A Linux host, amd64 or arm64, with Docker Engine and the Compose plugin, that allows
  privileged containers. The runtime runs its own nested Docker engine.
- Two DNS names pointing at the host, one for OpenCode and one for the Xpra desktop.
  Both services are served at the root path, so they cannot share a hostname.
- A reverse proxy that terminates TLS and forwards WebSockets. The example below uses
  Caddy; any proxy that can join a Docker network works.
- For a private repository, a GitHub token that can read it.

## 1. Create the proxy network

Each project container joins this network and publishes no host ports. Only the
proxy reaches it.

```bash
docker network create agentdev-proxy
```

Create it once per host and reuse it for every project.

## 2. Get the deployment files

The deployment is three Compose files and an env-file template. Clone the repository,
or fetch the files at the commit you want to run:

```bash
mkdir -p ~/agentdev-deploy && cd ~/agentdev-deploy
base=https://raw.githubusercontent.com/plume-works/agent-devcontainer/main
for f in compose.opencode.yml compose.opencode.bind.yml opencode-compose-pins.yml \
  docker/deploy/runtime.env.example; do
  curl -fsSLO "$base/$f"
done
```

`opencode-compose-pins.yml` names the image by tag and digest. Upgrading means taking
a newer copy of that one file.

## 3. Write the project's settings

Each project gets its own env file outside any repository, readable only by you:

```bash
mkdir -p -m 700 ~/secrets
install -m 600 runtime.env.example ~/secrets/myproject.env
```

Fill in at least:

| Setting                        | Value                                                          |
| ------------------------------ | -------------------------------------------------------------- |
| `OPENCODE_SERVER_PASSWORD`     | A long random secret, for example `openssl rand -base64 32`    |
| `XPRA_PASSWORD`                | A different random secret, or set `AGENTDEV_SKIP_XPRA=1`       |
| `AGENTDEV_PROXY_NETWORK`       | `agentdev-proxy`                                               |
| `AGENTDEV_REPOSITORY_URL`      | The HTTPS clone URL (clone mode)                               |
| `AGENTDEV_CHECKOUT`            | The host checkout's absolute path (bind mode instead)          |
| `GH_TOKEN`                     | The GitHub token, when the repository is private               |
| `AGENTDEV_UID`, `AGENTDEV_GID` | In bind mode, the IDs that own the checkout (`id -u`, `id -g`) |

Every project that should share Claude Code and Codex logins uses the same
`AGENTDEV_UID`, `AGENTDEV_GID`, and `AGENTDEV_AUTH_VOLUME`.

To reach the project from claude.ai/code or the Claude app, also set
`AGENTDEV_CLAUDE_RC_MODE` to `server` (conversations started on demand) or
`session` (one pinned conversation); `runtime.env.example` lists the spawn setting
for server mode. Left empty, Claude Remote Control stays off.

## 4. Start the project

The `-p` name scopes the project's volumes and its container name,
`<project>-opencode-1`.

```bash
cd ~/agentdev-deploy
# Clone mode: the first start clones the repository into the workspace volume.
docker compose -p myproject --env-file ~/secrets/myproject.env \
  -f compose.opencode.yml -f opencode-compose-pins.yml up -d

# Bind mode: mount the host checkout instead.
docker compose -p myproject --env-file ~/secrets/myproject.env \
  -f compose.opencode.yml -f opencode-compose-pins.yml -f compose.opencode.bind.yml up -d
```

The first start clones the workspace and starts OpenCode; the Python environment,
pre-commit hooks, and the code index follow in the background. Follow it until the
container reports `healthy`:

```bash
docker logs -f myproject-opencode-1
docker inspect --format '{{.State.Health.Status}}' myproject-opencode-1
```

If it stays unhealthy, `docker exec myproject-opencode-1
/opt/agentdev-runtime/runtime-health.sh status` names what failed and how to retry
it. The README's [operating notes](../../README.md#operating-it) list the usual
causes.

## 5. Route the proxy to it

Point each hostname at the project's container name on the proxy network. Every
project's service is called `opencode`, so with more than one project on the
network, the bare service name is ambiguous; always use `<project>-opencode-1`.

A minimal Caddy deployment, kept in its own directory:

```caddyfile
# Caddyfile
opencode.example.com {
    reverse_proxy myproject-opencode-1:4096
}

desktop.example.com {
    reverse_proxy myproject-opencode-1:14500
}
```

```yaml
# compose.yml next to the Caddyfile; pin the image by digest as with the runtime.
services:
  caddy:
    image: caddy:2
    restart: unless-stopped
    ports: ['80:80', '443:443']
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - caddy-data:/data
    networks: [proxy]
volumes:
  caddy-data:
networks:
  proxy:
    name: agentdev-proxy
    external: true
```

Caddy obtains certificates for both names and forwards WebSockets without extra
settings. Another project adds two more site blocks naming its own container.

With `ENABLE_FIREWALL=true`, set `AGENTDEV_TRUSTED_PROXY_CIDRS` to the proxy's
address on `agentdev-proxy`. Creating the network with a fixed `--subnet` and giving
the proxy a static `ipv4_address` keeps that address stable.

## 6. Log in

- **OpenCode.** Open `https://opencode.example.com`. The browser asks for basic-auth
  credentials: user `opencode`, password `OPENCODE_SERVER_PASSWORD`. Connect a model
  provider from OpenCode's settings. This login belongs to this project container
  only.
- **Desktop.** Open `https://desktop.example.com`; the Xpra HTML5 client asks for
  `XPRA_PASSWORD` when it connects.
- **Claude Code and Codex.** Log in once from a shell in the container; every project
  container in the same identity cohort then shares the login:

  ```bash
  docker exec -u agent -it myproject-opencode-1 bash
  claude        # follow its login prompt, then exit
  codex login   # `codex login --help` lists a device-code flow for remote hosts
  ```

- **Claude Remote Control.** With `AGENTDEV_CLAUDE_RC_MODE` set, Remote Control
  starts by itself, in tmux session `claude-remote`, within seconds of the
  claude.ai login above, in every running project container that shares the login
  and sets the mode; no restart is needed. Until then, `runtime-health.sh status`
  shows `remote-control: waiting for a claude.ai login`. If the session exits, the
  runtime starts it again. To look at it:

  ```bash
  docker exec -u agent -it myproject-opencode-1 tmux -L claude-remote attach -t claude-remote
  ```

## 7. Check that state survives

Run these checks after the first deployment and after any change to the deployment
files. Keep credentials and session contents out of anything you record.

1. Create an OpenCode session and change a user setting.
2. Replace the container: `docker compose ... up -d --force-recreate` with the same
   files. The OpenCode provider login, the session, the setting, and the Claude Code
   and Codex logins are all still there.
3. Upgrade: take a newer `opencode-compose-pins.yml` and run the same `up -d`. The
   same state survives, and `docker inspect` shows the new digest.
4. Start a second project with another `-p` name, the same IDs, and the same auth
   volume. It is already logged in to Claude Code and Codex, asks for its own OpenCode
   provider login, and lists none of the first project's sessions.
5. From another container on `agentdev-proxy`, port `4096` refuses requests without
   the OpenCode password and port `14500` refuses sessions without the Xpra password.

## Upgrading and removing

- **Upgrade:** replace `opencode-compose-pins.yml` with a newer copy and run the
  project's `up -d` again. The image reapplies its managed configuration and keeps
  user settings, sessions, and logins.
- **Stop:** `docker compose -p myproject ... down` keeps every volume.
- **Remove one project's state:** delete its volumes by name, for example
  `docker volume rm myproject_home myproject_uv myproject_docker myproject_workspace`.
  Never use `down -v`: it also deletes the auth volume that other projects share.
