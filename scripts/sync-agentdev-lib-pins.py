#!/usr/bin/env python3
"""
Write the agentdev-lib version into the pin of each plugin under .agents/plugins/.

Run from the repository root. Prints one line for each pin it rewrites, and exits 1 when it
rewrote any, as a formatter hook does.
"""

from __future__ import annotations

from pathlib import Path
import re
import sys
import tomllib

PACKAGE = Path('py_packages/agentdev_lib/pyproject.toml')
PLUGINS = Path('.agents/plugins')
PIN = re.compile(r'(["\']agentdev-lib==)([^"\']+)(["\'])')


def main() -> int:
    """Rewrite each stale pin and return 1 when any changed."""
    version = tomllib.loads(PACKAGE.read_text(encoding='utf-8'))['project']['version']
    changed = 0
    for pyproject in sorted(PLUGINS.glob('*/pyproject.toml')):
        text = pyproject.read_text(encoding='utf-8')
        for match in PIN.finditer(text):
            if match.group(2) != version:
                print(f'{pyproject}: agentdev-lib=={match.group(2)} -> =={version}')
                changed += 1
        pinned = PIN.sub(lambda match: f'{match.group(1)}{version}{match.group(3)}', text)
        if pinned != text:
            pyproject.write_text(pinned, encoding='utf-8')
    return 1 if changed else 0


if __name__ == '__main__':
    sys.exit(main())
