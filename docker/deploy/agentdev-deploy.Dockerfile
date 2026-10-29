# Tag-only by design, like agentdev-base's own base: CI always supplies the exact
# agentdev-base digest built in the same run (see .github/workflows/ci.yml).
ARG FROM_IMAGE=ghcr.io/plume-works/agentdev-base:edge

FROM $FROM_IMAGE

ARG FROM_IMAGE

# gh-stack moves out of root's home so any runtime account can register it.
# Supervisor and UID rationale: see architecture/standalone-opencode-runtime.
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends supervisor \
    && rm -f /etc/supervisor/conf.d/* \
    && userdel --remove ubuntu \
    && install -D -m 0755 /root/.local/share/gh/extensions/gh-stack/gh-stack \
      /usr/local/lib/agentdev/gh-stack/gh-stack \
    && install -m 0644 /root/.local/share/gh/extensions/gh-stack/manifest.yml \
      /usr/local/lib/agentdev/gh-stack/manifest.yml

COPY --chmod=0755 .devcontainer/scripts/ /opt/agentdev-runtime/
COPY --chmod=0644 docker/deploy/supervisord.conf /etc/agentdev/supervisord.conf
COPY --chmod=0644 .devcontainer/firewall-allowlist.txt /etc/agentdev/firewall-allowlist.txt

# The runtime identity, paths, and service defaults. Every value is overridable at
# `docker run`/Compose time; see docker/deploy/runtime.env.example.
ENV AGENTDEV_RUNTIME_MODE=deploy \
    AGENTDEV_USER=agent \
    AGENTDEV_UID=1000 \
    AGENTDEV_GID=1000 \
    AGENTDEV_HOME=/home/agent \
    DEV_WORKSPACE_FOLDER=/workspaces/project \
    AGENTDEV_AGENTS_AUTH_DIR=/var/lib/agentdev/auth \
    CLAUDE_SECURESTORAGE_CONFIG_DIR=/var/lib/agentdev/auth/claude \
    AGENTDEV_CLAUDE_DIR=/home/agent/.claude \
    AGENTDEV_CLAUDE_JSON=/home/agent/.claude.json \
    CODEX_HOME=/home/agent/.codex \
    CBM_CACHE_DIR=/home/agent/.cache/codebase-memory-mcp \
    XDG_RUNTIME_DIR=/run/agentdev/xdg \
    DBUS_SESSION_BUS_ADDRESS=unix:path=/run/agentdev/xdg/bus \
    DISPLAY=:100 \
    XPRA_HOST=0.0.0.0 \
    DOCKER_HOST=unix:///var/run/docker.sock \
    UV_CACHE_DIR=/uv/cache \
    UV_PYTHON_INSTALL_DIR=/uv/python \
    UV_PROJECT_ENVIRONMENT=/uv/venvs/project \
    AGENTDEV_STOP_TIMEOUT=30 \
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/agent/.local/bin

LABEL org.opencontainers.image.title="agentdev-deploy"
LABEL org.opencontainers.image.description="Self-starting single-project OpenCode runtime with nested Docker, CBM, keyring, and Xpra."
LABEL org.opencontainers.image.base.name="$FROM_IMAGE"

WORKDIR /workspaces/project

EXPOSE 4096 14500

# Healthy only while a live controller reports ready and the core probes pass; the
# start period covers the core path alone. See runtime-health.sh.
HEALTHCHECK --interval=15s --timeout=10s --start-period=10m --retries=3 \
  CMD ["/opt/agentdev-runtime/runtime-health.sh", "ready"]

ENTRYPOINT ["/opt/agentdev-runtime/runtime-supervisor.py", "run"]
CMD []
