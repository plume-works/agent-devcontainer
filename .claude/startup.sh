#!/usr/bin/env bash
# Startup script for Claude Code cloud sessions on this repository.
#
# Registers this checkout as the agent-devcontainer plugin marketplace, installs the
# agentdev plugin, starts the Docker daemon, and pre-pulls the pinned devcontainer image.
# Run from any directory; the script resolves the repository root from its own location.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
readonly REPO_ROOT
readonly DOCKERD_LOG="/var/log/dockerd.log"
readonly DOCKER_WAIT_SECONDS=30
readonly RELAY_LOG="/var/log/agent-proxy-relay.log"
# The devcontainer's nested engine claims 172.17.0.1, so the host bridge, which
# host.docker.internal resolves to, needs another subnet.
readonly DOCKER_BRIDGE_CIDR="10.213.0.1/24"
readonly PIN_DIR="${REPO_ROOT}/.tmp/comp-pin"
readonly CLOUD_ENV="${REPO_ROOT}/.devcontainer/cloud-session.env"

log() {
    printf '\n==> %s\n' "$*"
}

die() {
    printf 'startup: error: %s\n' "$*" >&2
    exit 1
}

register_plugin() {
    log "Registering agent-devcontainer marketplace and installing agentdev"
    cd "${REPO_ROOT}"
    claude plugin marketplace add ./
    claude plugin install agentdev@agent-devcontainer
}

start_docker() {
    log "Starting Docker daemon (log: ${DOCKERD_LOG})"
    dockerd --bip "${DOCKER_BRIDGE_CIDR}" >"${DOCKERD_LOG}" 2>&1 &

    for _ in $(seq 1 "${DOCKER_WAIT_SECONDS}"); do
        docker info >/dev/null 2>&1 && return 0
        sleep 1
    done
    die "Docker daemon not ready after ${DOCKER_WAIT_SECONDS}s; see ${DOCKERD_LOG}"
}

pull_pinned_images() {
    log "Pulling pinned devcontainer images"
    mkdir -p "${PIN_DIR}"
    cp "${REPO_ROOT}/devcontainer-compose-pins.yml" "${PIN_DIR}/docker-compose.yml"
    (cd "${PIN_DIR}" && docker compose pull)
}

export_git_identity() {
    local name email
    name="$(git config --get user.name || true)"
    email="$(git config --get user.email || true)"
    [[ -n "${name}" ]] && export GIT_AUTHOR_NAME="${name}" GIT_COMMITTER_NAME="${name}"
    [[ -n "${email}" ]] && export GIT_AUTHOR_EMAIL="${email}" GIT_COMMITTER_EMAIL="${email}"
    return 0
}

# gh and git authenticate only through the session's loopback agent proxy; relay it onto
# the Docker bridge for the container. See architecture/cloud-session-devcontainer.
export_proxy_access() {
    local proxy="${HTTPS_PROXY:-${https_proxy:-}}" port bridge_ip relay_proxy no_proxy_list
    rm -f "${CLOUD_ENV}"
    if [[ ! "${proxy}" =~ ^http://127\.0\.0\.1:([0-9]+)/?$ ]]; then
        printf 'startup: warning: no loopback HTTPS_PROXY; gh and git push stay unauthenticated\n' >&2
        return 0
    fi
    port="${BASH_REMATCH[1]}"
    bridge_ip="$(docker network inspect bridge -f '{{(index .IPAM.Config 0).Gateway}}')"
    log "Relaying agent proxy ${bridge_ip}:${port} -> 127.0.0.1:${port} (log: ${RELAY_LOG})"
    nohup python3 -I "${REPO_ROOT}/.claude/agent-proxy-relay.py" \
        "${bridge_ip}" "${port}" 127.0.0.1 "${port}" >"${RELAY_LOG}" 2>&1 &
    relay_proxy="http://host.docker.internal:${port}"
    no_proxy_list="${NO_PROXY:-${no_proxy:-}}"
    {
        printf 'HTTPS_PROXY=%s\nhttps_proxy=%s\n' "${relay_proxy}" "${relay_proxy}"
        printf 'NO_PROXY=%s\nno_proxy=%s\n' "${no_proxy_list}" "${no_proxy_list}"
        printf 'GH_TOKEN=%s\n' "${GH_TOKEN:-${GITHUB_TOKEN:-}}"
    } >"${CLOUD_ENV}"
}

bring_devcontainer_up() {
    log "Bringing up devcontainer"
    bun install @devcontainers/cli@0.80.2 --global
    export_git_identity
    export_proxy_access
    devcontainer up --workspace-folder "${REPO_ROOT}"
}

add_cloud_instructions() {
    mkdir -p ~/.claude
    cp -f "${REPO_ROOT}/.claude/CLAUDE.cloud.md" ~/.claude/CLAUDE.md
}

main() {
    time register_plugin
    add_cloud_instructions
    time start_docker
    time pull_pinned_images
    time bring_devcontainer_up
    log "Startup complete"
}

main "$@"
