#!/usr/bin/env bash
set -euo pipefail

# Stands in for a publish step: its only effect is a marker beside the clone.
date -u +%FT%TZ >"$(git rev-parse --show-toplevel)/../published.marker"
echo "published"
