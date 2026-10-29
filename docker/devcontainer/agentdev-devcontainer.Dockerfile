# Tag-only by design, like agentdev-deploy: CI always supplies the exact agentdev-base
# digest built in the same run (see .github/workflows/ci.yml).
ARG FROM_IMAGE=ghcr.io/plume-works/agentdev-base:edge

FROM $FROM_IMAGE

ARG FROM_IMAGE

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends supervisor \
    && rm -f /etc/supervisor/conf.d/* \
    && install -d -m 0755 /etc/agentdev/hooks/created.d /etc/agentdev/hooks/started.d \
      /etc/agentdev/hooks/attached.d

# The runtime root is image-owned; derived images extend it only through the hook
# directories and documented environment. Spec: agentdev-runtime-images.
COPY --chmod=0755 .devcontainer/scripts/ /opt/agentdev-runtime/
COPY --chmod=0644 docker/devcontainer/supervisord.conf /etc/agentdev/supervisord.conf
COPY --chmod=0644 .devcontainer/firewall-allowlist.txt /etc/agentdev/firewall-allowlist.txt
SHELL ["/bin/bash", "-o", "pipefail", "-c"]
# hadolint ignore=DL3003
RUN cd /opt/agentdev-runtime && find . -type f -not -path '*/__pycache__/*' -print0 | LC_ALL=C sort -z \
    | xargs -0 sha256sum > /etc/agentdev/runtime.sha256

# Defaults a consumer's descriptor or derived image may override; see
# architecture/devcontainer-runtime.
ENV AGENTDEV_RUNTIME_MODE=devcontainer \
    AGENTDEV_USER=root \
    AGENTDEV_HOME=/root \
    XDG_RUNTIME_DIR=/run/agentdev/xdg \
    DBUS_SESSION_BUS_ADDRESS=unix:path=/run/agentdev/xdg/bus \
    DISPLAY=:100 \
    DOCKER_HOST=unix:///var/run/docker.sock \
    CBM_CACHE_DIR=/root/.cache/codebase-memory-mcp \
    AGENTDEV_STOP_TIMEOUT=30

# Inherited by every descriptor that selects this image: the stable lifecycle commands,
# the entrypoint kept in place, and the nested engine's non-overlay storage.
LABEL devcontainer.metadata='[{ \
  "privileged": true, \
  "overrideCommand": false, \
  "mounts": [{"source": "dind-var-lib-docker-${devcontainerId}", "target": "/var/lib/docker", "type": "volume"}], \
  "remoteEnv": {"DEV_WORKSPACE_FOLDER": "${containerWorkspaceFolder}"}, \
  "postCreateCommand": "/opt/agentdev-runtime/devcontainer-created.sh", \
  "postStartCommand": "/opt/agentdev-runtime/devcontainer-ready.sh", \
  "postAttachCommand": "/opt/agentdev-runtime/devcontainer-attached.sh", \
  "waitFor": "postStartCommand" \
}]'
LABEL org.opencontainers.image.title="agentdev-devcontainer"
LABEL org.opencontainers.image.description="Dev Container runtime with supervised Docker, D-Bus, keyring, CBM, and Xpra, and stable lifecycle commands."
LABEL org.opencontainers.image.base.name="$FROM_IMAGE"

EXPOSE 14500

HEALTHCHECK --interval=15s --timeout=10s --start-period=5m --retries=3 \
  CMD ["/opt/agentdev-runtime/runtime-health.sh", "ready"]

ENTRYPOINT ["/opt/agentdev-runtime/runtime-supervisor.py", "run"]
CMD []
