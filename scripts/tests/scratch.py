"""Where tests put scratch files: real /tmp, never the checkout (AGENTS.md, temporary files)."""

from pathlib import Path

# Set TMP_ROOT to the agentdev-tests directory under /tmp.
TMP_ROOT = Path('/tmp/agentdev-tests')
