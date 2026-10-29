#!/usr/bin/env bash
# agentdev-base entrypoint. The base image is lifecycle-neutral — nothing to source and
# no supervisor to start — so just hand off to the requested command.
set -e

exec "$@"
