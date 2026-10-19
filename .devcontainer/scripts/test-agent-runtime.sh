#!/usr/bin/env bash
set -euo pipefail

# Container acceptance for agent-opencode against the explicit image in
# AGENTDEV_RUNTIME_TEST_IMAGE; extra arguments go to pytest. Bounded, cleans up every
# labelled resource it made, and fails when every test was skipped.

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
image="${AGENTDEV_RUNTIME_TEST_IMAGE:?set AGENTDEV_RUNTIME_TEST_IMAGE to the image under test}"
label="agentdev.test=acceptance"
report="$repo_root/.tmp/agent-runtime-acceptance.xml"

cleanup() {
  local ids
  ids="$(docker ps -aq --filter "label=$label")"
  [[ -z $ids ]] || xargs docker rm -f <<<"$ids" >/dev/null
  ids="$(docker volume ls -q --filter "label=$label")"
  [[ -z $ids ]] || xargs docker volume rm -f <<<"$ids" >/dev/null
  ids="$(docker network ls -q --filter "label=$label")"
  [[ -z $ids ]] || xargs docker network rm <<<"$ids" >/dev/null
}
trap cleanup EXIT

docker image inspect "$image" >/dev/null 2>&1 || docker pull "$image"
mkdir -p "$(dirname "$report")"
cd "$repo_root"
status=0
timeout "${AGENTDEV_RUNTIME_TEST_TIMEOUT:-5400}" uv run pytest \
  scripts/tests/test_agent_runtime_acceptance.py --junitxml="$report" -rs "$@" || status=$?
((status == 0)) || exit "$status"

python3 - "$report" <<'EOF'
import sys
import xml.etree.ElementTree as ET

suite = ET.parse(sys.argv[1]).getroot().find('testsuite')
ran = int(suite.get('tests')) - int(suite.get('skipped'))
if ran == 0:
    sys.exit('test-agent-runtime: every acceptance test was skipped')
print(f'test-agent-runtime: {ran} acceptance tests ran')
EOF
