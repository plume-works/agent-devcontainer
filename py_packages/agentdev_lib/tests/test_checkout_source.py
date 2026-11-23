"""A plugin script in this checkout runs the agentdev-lib source next to it."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

CHECKOUT = Path(__file__).resolve().parents[3]
LIB_SOURCE = CHECKOUT / 'py_packages' / 'agentdev_lib' / 'agentdev_lib'
PLUGINS = CHECKOUT / '.agents' / 'plugins'


def test_plugin_script_imports_checkout_package(scratch: Path) -> None:
    """Each plugin's uv project resolves agentdev_lib to the checkout's own source files."""
    environment = {key: value for key, value in os.environ.items() if key != 'VIRTUAL_ENV'}
    resolved = {}
    for plugin in sorted(path.parent for path in PLUGINS.glob('*/pyproject.toml')):
        completed = subprocess.run(
            ['uv', 'run', '--quiet', '--project', str(plugin), 'python', '-c',
             'import agentdev_lib.result_codes as m; print(m.__file__)'],
            cwd=scratch,
            env=environment,
            capture_output=True,
            text=True,
            check=True,
        )  # fmt: skip
        resolved[plugin.name] = Path(completed.stdout.strip())

    assert resolved
    assert set(resolved.values()) == {LIB_SOURCE / 'result_codes.py'}
