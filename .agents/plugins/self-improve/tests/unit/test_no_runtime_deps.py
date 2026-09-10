"""
Enforce the runtime dependency rule of spec section 4.1.

Plugin runtime code must import successfully with nothing but a system
``python3``, offline. This test is what keeps that true as the plugin grows: an
accidental ``import yaml`` fails here rather than in a user's hook, where it
would surface as a silently skipped capture.

The rule constrains imports, not the interpreter version: the runtime targets
this repository's floor, so no standard-library module is out of reach.
"""

import ast
import os
import sys

import pytest

from tests.conftest import PLUGIN_ROOT

# Directories under the plugin root that ship no runtime code. `tests` is the
# suite itself, which imports pytest and is never loaded by a hook.
NON_RUNTIME_DIRS = {'__pycache__', 'tests', '.tmp', 'test-runs'}


def runtime_modules():
    for dirpath, dirnames, filenames in os.walk(PLUGIN_ROOT):
        dirnames[:] = [d for d in dirnames if d not in NON_RUNTIME_DIRS]
        for name in filenames:
            if name.endswith('.py'):
                yield os.path.join(dirpath, name)


def imported_roots(path):
    with open(path, encoding='utf-8') as handle:
        tree = ast.parse(handle.read(), filename=path)
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split('.')[0])
        # node.level > 0 is a relative import, which stays inside this package.
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            roots.add(node.module.split('.')[0])
    return roots


@pytest.mark.parametrize(
    'path', sorted(runtime_modules()), ids=lambda p: os.path.relpath(p, PLUGIN_ROOT)
)
def test_runtime_imports_stdlib_only(path):
    local_packages = {'selfimprove'}
    allowed = set(sys.stdlib_module_names) | local_packages
    offenders = sorted(root for root in imported_roots(path) if root not in allowed)
    assert not offenders, (
        '%s imports non-stdlib module(s) %s; plugin runtime code must load with a '
        'bare system python3' % (os.path.relpath(path, PLUGIN_ROOT), offenders)
    )
