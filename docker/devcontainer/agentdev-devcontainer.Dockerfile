# Tag-only by design, like agentdev-deploy: CI always supplies the exact agentdev-base
# digest built in the same run (see .github/workflows/ci.yml).
ARG FROM_IMAGE=ghcr.io/plume-works/agentdev-base:edge

FROM $FROM_IMAGE

ARG FROM_IMAGE

# The devcontainer CLI's UID update re-owns the account's home and fails when it is missing,
# so the home exists and stays empty; see ADR-0075.
RUN userdel --remove ubuntu \
    && groupadd --gid 1000 agent \
    && useradd --no-create-home --uid 1000 --gid 1000 --home-dir /home/agent \
      --shell /bin/bash agent \
    && install -d -m 0755 -o agent -g agent /home/agent

RUN install -d -m 0755 /etc/agentdev/hooks/created.d /etc/agentdev/hooks/started.d \
      /etc/agentdev/hooks/attached.d

# The runtime CLI is a uv tool on the system interpreter, like validate_agent_files; the
# bind mount is writable because setuptools writes its egg-info beside the source.
RUN --mount=type=bind,source=py_packages/agentdev_runtime,target=/tmp/agentdev-runtime,rw \
    UV_TOOL_DIR=/opt/uv-tools UV_TOOL_BIN_DIR=/usr/local/bin UV_NO_CACHE=1 \
    UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy \
    uv tool install --reinstall --python /usr/bin/python3 /tmp/agentdev-runtime

# The runtime root is image-owned; derived images extend it only through the hook
# directories and documented environment. See ADR-0032.
COPY --chmod=0644 docker/devcontainer/supervisord.conf /etc/agentdev/supervisord.conf
COPY --chmod=0644 .devcontainer/firewall-allowlist.txt /etc/agentdev/firewall-allowlist.txt

# Defaults a consumer's descriptor or derived image may override.
# Do not set UV_CACHE_DIR, UV_PYTHON_INSTALL_DIR, or PRE_COMMIT_HOME: their defaults are on the home volume.
ENV AGENTDEV_RUNTIME_MODE=devcontainer \
    AGENTDEV_USER=agent \
    AGENTDEV_HOME=/home/agent \
    AGENTDEV_AGENTS_AUTH_DIR=/var/lib/agentdev/auth \
    CLAUDE_SECURESTORAGE_CONFIG_DIR=/var/lib/agentdev/auth/claude \
    AGENTDEV_VENV_ROOT=/home/agent/.local/share/uv/venvs \
    XDG_RUNTIME_DIR=/run/agentdev/xdg \
    DBUS_SESSION_BUS_ADDRESS=unix:path=/run/agentdev/xdg/bus \
    DISPLAY=:100 \
    DOCKER_HOST=unix:///var/run/docker.sock \
    AGENTDEV_STOP_TIMEOUT=30 \
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/agent/.local/bin

# Inherited by every descriptor that selects this image: the stable lifecycle commands,
# the entrypoint kept in place, the nested engine's non-overlay storage, and the runtime
# account remapped to the host user with its home on one per-instance volume.
LABEL devcontainer.metadata='[{ \
  "privileged": true, \
  "overrideCommand": false, \
  "remoteUser": "agent", \
  "updateRemoteUserUID": true, \
  "mounts": [ \
    {"source": "dind-var-lib-docker-${devcontainerId}", "target": "/var/lib/docker", "type": "volume"}, \
    {"source": "agentdev-home-${devcontainerId}", "target": "/home/agent", "type": "volume"} \
  ], \
  "containerEnv": {"DEV_WORKSPACE_FOLDER": "${containerWorkspaceFolder}"}, \
  "postCreateCommand": "agentdev-runtime lifecycle created --wait", \
  "postStartCommand": "agentdev-runtime lifecycle ready", \
  "postAttachCommand": "agentdev-runtime lifecycle attached", \
  "waitFor": "postStartCommand" \
}]'
LABEL org.opencontainers.image.title="agentdev-devcontainer"
LABEL org.opencontainers.image.description="Dev Container runtime with supervised Docker, D-Bus, keyring, and Xpra, and stable lifecycle commands."
LABEL org.opencontainers.image.base.name="$FROM_IMAGE"

EXPOSE 14500

HEALTHCHECK --interval=15s --timeout=10s --start-period=5m --retries=3 \
  CMD ["/usr/local/bin/agentdev-runtime", "health", "ready"]

ENTRYPOINT ["/usr/local/bin/agentdev-runtime", "supervisor", "run"]
CMD []
