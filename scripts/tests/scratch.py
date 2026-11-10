"""Where tests put scratch files: real /tmp, never the checkout (AGENTS.md, temporary files)."""

import os
from pathlib import Path

# The root-test launcher sets its own root, so files it leaves never block a later run.
TMP_ROOT = Path(os.environ.get('AGENTDEV_TEST_TMP_ROOT', '/tmp/agentdev-tests'))
