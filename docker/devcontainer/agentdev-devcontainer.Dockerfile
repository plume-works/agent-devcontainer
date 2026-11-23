# The base supplies systemd as PID 1, the Docker engine under systemd, the `dev` account, and
# the shared toolchain and agent CLIs; see ADR-0107. Renovate moves the digest through a pull
# request that builds and tests this image.
FROM ghcr.io/plume-works/devcontainer-base:edge@sha256:283df43f0be62d88ea4995a828b3842b7c89b80c8927a08f3c20a5be4e9fe93e

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]

# From the base image's dated Ubuntu archive snapshot. python3-yaml serves the pinned-tool
# fetcher below; iptables and ipset the egress firewall; fuse-overlayfs the nested engine.
RUN apt-get update --error-on=any \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      bash-completion build-essential dirmngr ffmpeg fuse-overlayfs ipset iptables locales \
      lsb-release openssh-client pkg-config pre-commit python3-argcomplete python3-pip \
      python3-setuptools python3-venv python3-yaml tzdata unzip wget xz-utils \
 && locale-gen en_US.UTF-8 \
 && update-locale LANG=en_US.UTF-8 LC_ALL=en_US.UTF-8 \
 && ln -sf /usr/share/zoneinfo/Etc/UTC /etc/localtime \
 && echo Etc/UTC > /etc/timezone \
 && rm -rf /var/lib/apt/lists/*
ENV LANG=en_US.UTF-8 LANGUAGE=en_US:en LC_ALL=en_US.UTF-8

# Xpra and its HTML5 client from xpra.org, whose repository the archive snapshot does not cover.
RUN a=$(dpkg --print-architecture) && . /etc/os-release \
 && curl -fsSL https://xpra.org/xpra.asc -o /usr/share/keyrings/xpra.asc \
 && echo "deb [arch=$a signed-by=/usr/share/keyrings/xpra.asc] https://xpra.org $VERSION_CODENAME main" \
      > /etc/apt/sources.list.d/xpra.list \
 && apt-get update --error-on=any \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y xpra xpra-html5 \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      libgl1 libgl1-mesa-dri libglvnd0 mesa-utils python3-opengl python3-pyinotify python3-xdg xvfb \
 && dpkg --compare-versions "$(dpkg-query -W -f='${Version}' xpra)" ge 6 \
 && rm -rf /var/lib/apt/lists/*

# Checksum-pinned release binaries and VirtualGL: see docker/devcontainer/pinned-tools.yml.
RUN --mount=type=bind,source=scripts/fetch-pinned-tool.py,target=/tmp/fetch-pinned-tool.py \
    --mount=type=bind,source=docker/devcontainer/pinned-tools.yml,target=/tmp/pinned-tools.yml \
    d=$(mktemp -d) \
 && python3 -I /tmp/fetch-pinned-tool.py "$d" --all --pins /tmp/pinned-tools.yml \
 && apt-get update --error-on=any \
 && DEBIAN_FRONTEND=noninteractive apt-get install -y "$d/virtualgl.deb" \
 && rm "$d/virtualgl.deb" \
 && install -m 0755 -o root -g root "$d"/* /usr/local/bin/ \
 && rm -rf "$d" /var/lib/apt/lists/*

# Bun runs these npm packages' Node scripts, so their commands work without Node.js.
# renovate: datasource=npm depName=playwright
ARG PLAYWRIGHT_VERSION=1.65.1
# renovate: datasource=npm depName=@modelcontextprotocol/inspector
ARG MCP_INSPECTOR_VERSION=2.16.0
ENV PLAYWRIGHT_BROWSERS_PATH=/opt/playwright
RUN BUN_INSTALL=/usr/local bun add --global --exact \
      "playwright@${PLAYWRIGHT_VERSION}" "@modelcontextprotocol/inspector@${MCP_INSPECTOR_VERSION}" \
 && for bin in playwright mcp-inspector; do \
      target=$(readlink -f "/usr/local/bin/$bin"); rm "/usr/local/bin/$bin"; \
      printf '#!/bin/sh\nexec /usr/local/bin/bun --bun %s "$@"\n' "$target" > "/usr/local/bin/$bin"; \
      chmod 0755 "/usr/local/bin/$bin"; \
    done \
 && install -d -o root -g root -m 0755 /opt/playwright \
 && apt-get update --error-on=any \
 && playwright install --with-deps chromium \
 && chmod -R a+rwX /opt/playwright \
 && [ "$(playwright --version)" = "Version ${PLAYWRIGHT_VERSION}" ] \
 && rm -rf /var/lib/apt/lists/*

# uv tools on the system interpreter, outside every home; the bind mounts are writable because
# setuptools writes its egg-info beside the source.
# A pin the build verifies: bump it with py_packages/validate_agent_files/pyproject.toml.
ARG VALIDATE_AGENT_FILES_VERSION=1.0.1
RUN --mount=type=bind,source=py_packages/validate_agent_files,target=/tmp/validate-agent-files,rw \
    --mount=type=bind,source=py_packages/agentdev_runtime,target=/tmp/agentdev-runtime,rw \
    export UV_TOOL_DIR=/opt/uv-tools UV_TOOL_BIN_DIR=/usr/local/bin UV_NO_CACHE=1 \
      UV_PYTHON_DOWNLOADS=never UV_LINK_MODE=copy \
 && uv tool install --reinstall --python /usr/bin/python3 /tmp/validate-agent-files \
 && uv tool install --reinstall --python /usr/bin/python3 /tmp/agentdev-runtime \
 && [ "$(/opt/uv-tools/validate-agent-files/bin/python -c \
      'import importlib.metadata as m; print(m.version("validate_agent_files"))')" \
      = "$VALIDATE_AGENT_FILES_VERSION" ] \
 && chmod -R u=rwX,go=rX /opt/uv-tools

# The agentdev catalog, staged outside every home: the create phase installs it into each
# agent's user scope. A pin the build verifies: bump it with .claude-plugin/marketplace.json.
ARG AGENTDEV_PLUGIN_VERSION=5.0.0
ENV AGENTDEV_CATALOG_DIR=/opt/agentdev
RUN --mount=type=bind,source=.claude-plugin,target=/tmp/catalog/.claude-plugin \
    --mount=type=bind,source=.agents/plugins,target=/tmp/catalog/.agents/plugins \
    m=/tmp/catalog/.claude-plugin/marketplace.json \
 && [ "$(jq '[.plugins[] | select(.name == "agentdev")] | length' "$m")" = 1 ] \
 && [ "$(jq -r '.plugins[] | select(.name == "agentdev").version' "$m")" = "$AGENTDEV_PLUGIN_VERSION" ] \
 && install -d -m 0755 "$AGENTDEV_CATALOG_DIR" \
 && cp -a /tmp/catalog/. "$AGENTDEV_CATALOG_DIR/" \
 && find "$AGENTDEV_CATALOG_DIR" -depth -type d \( -name __pycache__ -o -name .pytest_cache \
      -o -name .ruff_cache -o -name .tmp -o -name tests \) -exec rm -rf {} + \
 && chown -R root:root "$AGENTDEV_CATALOG_DIR" \
 && chmod -R u=rwX,go=rX "$AGENTDEV_CATALOG_DIR"

# The gh wrapper takes the base image's gh path, so every caller, git's credential helper
# included, goes through it; see ADR-0074.
RUN mv /usr/local/bin/gh /usr/bin/gh
COPY --chmod=0755 docker/devcontainer/gh /usr/local/bin/gh

# COPY --chmod gives the parent directories it creates the file's mode, which no account
# but root could then traverse, so every target directory exists first.
RUN install -d -m 0755 /etc/docker /etc/fish/conf.d /etc/agentdev/hooks/created.d \
      /etc/agentdev/hooks/started.d /etc/agentdev/hooks/attached.d \
      /etc/systemd/system/docker.service.d /etc/systemd/user
COPY --chmod=0644 docker/devcontainer/daemon.json /etc/docker/daemon.json
COPY --chmod=0644 docker/devcontainer/agentdev.fish /etc/fish/conf.d/agentdev.fish
COPY --chmod=0644 docker/devcontainer/xdg-runtime.sh /etc/profile.d/agentdev-xdg-runtime.sh
COPY --chmod=0644 .devcontainer/firewall-allowlist.txt /etc/agentdev/firewall-allowlist.txt
# Ubuntu's skeleton .bashrc would shorten the system-wide history settings again.
RUN --mount=type=bind,source=docker/devcontainer/shell.bashrc,target=/tmp/shell.bashrc \
    cat /tmp/shell.bashrc >> /etc/bash.bashrc \
 && sed -i '/^HISTSIZE=/d; /^HISTFILESIZE=/d; /^HISTCONTROL=/d' /etc/skel/.bashrc /home/dev/.bashrc

COPY --chmod=0644 docker/devcontainer/systemd/agentdev-bootstrap.service \
     docker/devcontainer/systemd/agentdev-created.service /etc/systemd/system/
COPY --chmod=0644 docker/devcontainer/systemd/docker.service.d/agentdev.conf \
     /etc/systemd/system/docker.service.d/agentdev.conf
COPY --chmod=0644 docker/devcontainer/systemd/agentdev-xpra.service /etc/systemd/user/
# The xpra package's system proxy socket would hold the port the desktop's own server binds.
RUN systemctl enable agentdev-bootstrap.service agentdev-created.service \
 && systemctl --global enable agentdev-xpra.service \
 && systemctl disable xpra.socket && systemctl mask xpra.socket xpra.service

# Tools with their own root store read the system one, so an added CA reaches them all.
# See ADR-0024. A consumer descriptor or a derived image can change the other defaults.
# Do not set UV_CACHE_DIR, UV_PYTHON_INSTALL_DIR, or PRE_COMMIT_HOME: their defaults are on the home volume.
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt \
    NODE_EXTRA_CA_CERTS=/etc/ssl/certs/ca-certificates.crt \
    AGENTDEV_USER=dev \
    AGENTDEV_HOME=/home/dev \
    AGENTDEV_AGENTS_AUTH_DIR=/var/lib/agentdev/auth \
    CLAUDE_SECURESTORAGE_CONFIG_DIR=/var/lib/agentdev/auth/claude \
    AGENTDEV_VENV_ROOT=/home/dev/.local/share/uv/venvs \
    DISPLAY=:100 \
    DOCKER_HOST=unix:///var/run/docker.sock \
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/dev/.local/bin

WORKDIR /workspaces/project

# Inherited by every descriptor that selects this image: the lifecycle commands, systemd kept
# as PID 1, the nested engine's storage, and one per-instance home volume. See ADR-0031.
LABEL devcontainer.metadata='[{ \
  "privileged": true, \
  "overrideCommand": false, \
  "remoteUser": "dev", \
  "updateRemoteUserUID": true, \
  "mounts": [ \
    {"source": "dind-var-lib-docker-${devcontainerId}", "target": "/var/lib/docker", "type": "volume"}, \
    {"source": "dind-var-lib-containerd-${devcontainerId}", "target": "/var/lib/containerd", "type": "volume"}, \
    {"source": "agentdev-home-${devcontainerId}", "target": "/home/dev", "type": "volume"} \
  ], \
  "containerEnv": {"DEV_WORKSPACE_FOLDER": "${containerWorkspaceFolder}"}, \
  "postCreateCommand": "agentdev-runtime lifecycle created --wait", \
  "postStartCommand": "agentdev-runtime lifecycle ready", \
  "postAttachCommand": "agentdev-runtime lifecycle attached", \
  "waitFor": "postStartCommand" \
}]'
LABEL org.opencontainers.image.title="agentdev-devcontainer"
LABEL org.opencontainers.image.description="Dev Container for agent-driven development on plume-works/devcontainer-base: Xpra, the agentdev catalog, an opt-in egress firewall, and stable lifecycle commands."
LABEL org.opencontainers.image.version.agentdev="$AGENTDEV_PLUGIN_VERSION"
LABEL org.opencontainers.image.version.playwright="$PLAYWRIGHT_VERSION"
LABEL org.opencontainers.image.version.validate-agent-files="$VALIDATE_AGENT_FILES_VERSION"

EXPOSE 14500

HEALTHCHECK --interval=15s --timeout=10s --start-period=5m --retries=3 \
  CMD ["/usr/local/bin/agentdev-runtime", "health", "ready"]
