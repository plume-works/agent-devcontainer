"""Where tests put scratch files: real /tmp, never the checkout (AGENTS.md, temporary files)."""

from pathlib import Path

TMP_ROOT = Path('/tmp/agentdev-tests')
