"""The Codex harness counts a shipper's publish run only when it executes the script."""

import importlib.util
import json
from pathlib import Path
import sys

import pytest

COMPACT = (',', ':')

REPO_ROOT = Path(__file__).parents[2]
SUITE = REPO_ROOT / 'scripts/e2e/iwe-workflows'
sys.path.insert(0, str(SUITE))
_spec = importlib.util.spec_from_file_location(
    'e2e_iwe_workflows_harness_codex', SUITE / 'harness_codex.py'
)
harness = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(harness)
sys.path.remove(str(SUITE))

CHAINED = (
    "printf '%s\\n' '--- CHECK 1 ---'; grep -qx hello e2e/hello.txt; "
    'printf \'grep_exit=%s\\n\' "$?"; bin/publish-e2e.sh; printf \'publish_exit=%s\\n\' "$?"'
)


def rollout_line(cmd: str) -> str:
    """Encode ``cmd`` the way a Codex rollout records an exec call: compact JSON in JSON."""
    arguments = json.dumps({'cmd': cmd, 'workdir': '/w/clone'}, separators=COMPACT)
    return json.dumps(
        {'payload': {'type': 'function_call', 'name': 'exec_command', 'arguments': arguments}}
    )


@pytest.mark.parametrize(
    'cmd',
    [
        'bin/publish-e2e.sh',
        './bin/publish-e2e.sh',
        'bash bin/publish-e2e.sh',
        '/w/clone/bin/publish-e2e.sh',
        'git status && bin/publish-e2e.sh',
        CHAINED,
    ],
)
def test_executing_the_script_counts(cmd):
    """The script run alone, by path, through a shell, or after a quoted chain counts."""
    assert harness.PUBLISH_COMMAND.search(rollout_line(cmd))
    assert harness.PUBLISH_COMMAND.search(json.dumps({'cmd': cmd}, separators=COMPACT))


@pytest.mark.parametrize(
    'cmd',
    [
        'nl -ba bin/publish-e2e.sh',
        'cat bin/publish-e2e.sh',
        "sed -n '1,5p' bin/publish-e2e.sh",
        'printf "%s" "x"; grep -n publish bin/publish-e2e.sh',
    ],
)
def test_reading_the_script_does_not_count(cmd):
    """Reading the script, even after a quoted chain, is not a publish."""
    assert not harness.PUBLISH_COMMAND.search(rollout_line(cmd))
    assert not harness.PUBLISH_COMMAND.search(json.dumps({'cmd': cmd}, separators=COMPACT))
