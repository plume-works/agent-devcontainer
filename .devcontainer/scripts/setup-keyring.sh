#!/usr/bin/env bash
# Bring up a GNOME Keyring Secret Service (org.freedesktop.secrets) inside the
# container. Safe to run standalone to enable the keyring; used to store
# `gh auth login` tokens.
#
# Idempotent: a live session is reused, a saved session is restored, otherwise
# a fresh dbus + gnome-keyring session is started. The resulting D-Bus session
# environment is persisted to .tmp/keyring-session.env so other processes can
# source it and reach the keyring.
#
# IMPORTANT: login.keyring is the actual secret store. Overwriting it destroys
# every secret already saved in it (e.g. `gh auth login` tokens), so we must
# NEVER clobber an existing keyring.
#
# AT-REST STORAGE TRADEOFF: the login keyring is created with an EMPTY password
# (see ensure_login_keyring), so GNOME Keyring stores its secrets UNENCRYPTED on
# disk. This is deliberate: it lets the daemon start headless without an
# interactive unlock prompt. It is acceptable for a single-user devcontainer
# whose disk is already protected by host-level encryption (FileVault / the
# Docker Desktop VM). docker/mcp secrets bypass this keyring entirely: the
# devcontainer and the mcp-gateway sidecar both mount the host's
# docker-secrets-engine socket directly (see .devcontainer/devcontainer-init.sh),
# so those secrets never persist inside the container.
#
# If the threat model changes and at-rest encryption is required for the gh
# token keyring, switch to `gnome-keyring-daemon --login` (reads a password on
# stdin) with a STABLE unlock password pulled from the host keychain /
# 1Password at init time.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
env_file="${AGENTDEV_KEYRING_ENV_FILE:-$script_dir/../../.tmp/keyring-session.env}"
# shellcheck source=runtime-keyring.sh
source "$script_dir/runtime-keyring.sh"

# A fixed address from containerEnv reaches every process in the container; without one,
# D-Bus clients such as gh autolaunch a bus per call that never exits.
fixed_socket=""
if [[ ${DBUS_SESSION_BUS_ADDRESS:-} =~ ^unix:path=([^,\;]+)$ ]]; then
    fixed_socket="${BASH_REMATCH[1]}"
fi

bus_alive() {
    gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus \
        --method org.freedesktop.DBus.GetId >/dev/null 2>&1
}

load_saved_session() {
    [[ -z "$fixed_socket" ]] || return 1
    [[ -f "$env_file" ]] || return 1
    # shellcheck disable=SC1090
    source "$env_file"
    keyring_session_ready
}

write_env_file() {
    mkdir -p "$(dirname "$env_file")"
    cat >"$env_file" <<EOF
export DBUS_SESSION_BUS_ADDRESS='${DBUS_SESSION_BUS_ADDRESS}'
export DBUS_SESSION_BUS_PID='${DBUS_SESSION_BUS_PID:-}'
export GNOME_KEYRING_CONTROL='${GNOME_KEYRING_CONTROL:-}'
EOF
    chmod 600 "$env_file"
}

# Reuse a live Secret Service session, or restore a previously-saved one.
if keyring_session_ready; then
    # A fixed bus is reused as is; rewriting would drop the PID recorded at its start.
    if [[ -z "$fixed_socket" ]] || ! grep -qF "'$DBUS_SESSION_BUS_ADDRESS'" "$env_file" 2>/dev/null; then
        write_env_file
    fi
    exit 0
fi

if load_saved_session; then
    write_env_file
    exit 0
fi

rm -f "$env_file"
if [[ -z "$fixed_socket" ]]; then
    unset DBUS_SESSION_BUS_ADDRESS
fi
unset DBUS_SESSION_BUS_PID GNOME_KEYRING_CONTROL

# Skip gracefully when the GNOME keyring stack is unavailable. This script runs
# unconditionally from the post-start hook, so a hard failure here would break
# every container image that does not ship the keyring stack.
for cmd in dbus-daemon gnome-keyring-daemon gdbus; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "$cmd is not installed; skipping keyring setup." >&2
        exit 0
    fi
done

keyring_ensure_login_keyring

if [[ -n "$fixed_socket" ]]; then
    if ! bus_alive; then
        mkdir -p "$(dirname "$fixed_socket")"
        chmod 700 "$(dirname "$fixed_socket")"
        # A socket left by a killed daemon would make the bind fail.
        rm -f "$fixed_socket"
        DBUS_SESSION_BUS_PID="$(dbus-daemon --session --fork --print-pid=1 \
            --address="$DBUS_SESSION_BUS_ADDRESS")"
    fi
else
    dbus_output="$(dbus-daemon --session --fork --print-address=1 --print-pid=1)"
    DBUS_SESSION_BUS_ADDRESS="$(printf '%s\n' "$dbus_output" | sed -n '1p')"
    DBUS_SESSION_BUS_PID="$(printf '%s\n' "$dbus_output" | sed -n '2p')"
fi
export DBUS_SESSION_BUS_ADDRESS DBUS_SESSION_BUS_PID

keyring_output="$(gnome-keyring-daemon --start --components=secrets)"
GNOME_KEYRING_CONTROL="$(printf '%s\n' "$keyring_output" | sed -n 's/^GNOME_KEYRING_CONTROL=//p')"
if [[ -n "$GNOME_KEYRING_CONTROL" ]]; then
    export GNOME_KEYRING_CONTROL
fi

keyring_wait_ready 5

write_env_file
