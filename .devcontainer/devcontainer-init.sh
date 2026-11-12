#!/usr/bin/env bash
set -euo pipefail

script_dir=$(dirname "${BASH_SOURCE[0]}")

if [[ -f "$script_dir/local.env" ]]; then
    cp -f "$script_dir/local.env" "$script_dir/.env"
else
    rm -f "$script_dir/.env"
    touch "$script_dir/.env"
fi

# Claude's credentials outlive every Compose project and are shared only by containers
# remapped to the same host UID and GID; docker-compose.yml declares the volume external.
auth_volume="agentdev-agents-auth-$(id -u)-$(id -g)"
docker volume create "$auth_volume" >/dev/null
echo "AGENTDEV_AUTH_VOLUME=$auth_volume" >> "$script_dir/.env"

gitdir=$(realpath "$(git rev-parse --git-common-dir)")
echo "GIT_REPO=$gitdir" >> "$script_dir/.env"

LOCAL_WORKSPACE_FOLDER=$(realpath "$script_dir/..")
# Remote Control names its environment after this hostname; spec: claude-remote-control.
# Inline because a migrated consumer keeps no .devcontainer/scripts/.
host="${HOSTNAME:-$(hostname)}"
host="${host%%.*}"
stem="$(basename "$LOCAL_WORKSPACE_FOLDER")"
if [[ -n "${CODER_WORKSPACE_NAME:-}" ]]; then
    container_hostname="coder-$CODER_WORKSPACE_NAME"
elif [[ -n "${VSCODE_PID:-}" || -n "${VSCODE_IPC_HOOK:-}" ]]; then
    container_hostname="vscode-$host-$stem"
else
    container_hostname="cli-$host-$stem"
fi
container_hostname="$(printf '%s' "$container_hostname" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-')"
container_hostname="${container_hostname#-}"
container_hostname="${container_hostname:0:63}"
container_hostname="${container_hostname%-}"
{
    echo "LOCAL_WORKSPACE_FOLDER=$LOCAL_WORKSPACE_FOLDER"
    # Compose has no equivalent of devcontainer.json's ${localWorkspaceFolderBasename},
    # so export it here. It must stay in sync with `workspaceFolder` in
    # devcontainer.json, which is /workspaces/${localWorkspaceFolderBasename}.
    echo "WORKSPACE_BASENAME=$(basename "$LOCAL_WORKSPACE_FOLDER")"
    echo "CONTAINER_HOSTNAME=$container_hostname"
} >> "$script_dir/.env"

# A TLS-intercepting proxy's CA, for the runtime to trust; design: spec/agentdev-runtime-images.
# Always written, empty when the host names none, so Compose bind-mounts a file.
extra_ca="$script_dir/.extra-ca.crt"
: > "$extra_ca"
if [[ -n "${AGENTDEV_EXTRA_CA_CERTS:-}" ]]; then
    if [[ ! -r "$AGENTDEV_EXTRA_CA_CERTS" ]]; then
        echo "devcontainer-init: AGENTDEV_EXTRA_CA_CERTS=$AGENTDEV_EXTRA_CA_CERTS is not readable" >&2
        exit 1
    fi
    cat "$AGENTDEV_EXTRA_CA_CERTS" > "$extra_ca"
elif [[ -n "${NODE_EXTRA_CA_CERTS:-}" && -r "$NODE_EXTRA_CA_CERTS" ]]; then
    cat "$NODE_EXTRA_CA_CERTS" > "$extra_ca"
fi
