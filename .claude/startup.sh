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
readonly PIN_DIR="${REPO_ROOT}/.tmp/comp-pin"

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
    dockerd >"${DOCKERD_LOG}" 2>&1 &

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

bring_devcontainer_up() {
    log "Bringing up devcontainer"
    bun install @devcontainers/cli@0.80.2 --global
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
