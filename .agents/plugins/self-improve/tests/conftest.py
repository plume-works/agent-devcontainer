"""
Shared fixtures and the live-test collection guard.

Every test runs against a throwaway state root and a throwaway Claude home. No
test may read or write the developer's real ``~/.claude``.
"""

import json
import os
import subprocess
import sys

import pytest

# Resolved from this file so the suite runs from the plugin cache, where the
# repository that develops the plugin is not present.
PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SI = os.path.join(PLUGIN_ROOT, 'scripts', 'si')

sys.path.insert(0, PLUGIN_ROOT)

# Markers whose tests drive a real Claude session and spend model usage.
# `harness` is deliberately absent: it self-checks the pty harness against a
# fake terminal, costs nothing, and runs in the ordinary suite.
LIVE_MARKERS = ('smoke', 'pty')
LIVE_OPT_IN_ENV = 'SELF_IMPROVE_RUN_LIVE'


def pytest_collection_modifyitems(items):
    """
    Skip live tests unless the opt-in variable is set.

    The guard is at collection because deselecting by marker in ``addopts`` is
    bypassed by every natural way to iterate on a test — naming its path,
    passing ``-m``, or selecting a node id — each of which replaces the filter
    and fires a paid session.
    """
    if os.environ.get(LIVE_OPT_IN_ENV):
        return
    for item in items:
        # iter_markers, not keywords: keywords also carries path components, so
        # every test under tests/smoke/ would match 'smoke' whatever it is
        # marked — including the harness self-checks that drive no session.
        applied = {marker.name for marker in item.iter_markers()}
        marked = [marker for marker in LIVE_MARKERS if marker in applied]
        if marked:
            item.add_marker(
                pytest.mark.skip(
                    reason=(
                        f'live test marked {", ".join(marked)} spends model usage; '
                        f'set {LIVE_OPT_IN_ENV}=1 to run it'
                    )
                )
            )


@pytest.fixture
def claude_home(tmp_path, monkeypatch):
    """Provide an isolated Claude configuration directory."""
    home = tmp_path / 'claude-home'
    home.mkdir()
    monkeypatch.setenv('CLAUDE_CONFIG_DIR', str(home))
    return home


@pytest.fixture
def state_root(tmp_path, monkeypatch, claude_home):
    """Provide an isolated state root with the plugin-data variable cleared."""
    root = tmp_path / 'state'
    monkeypatch.delenv('CLAUDE_PLUGIN_DATA', raising=False)
    monkeypatch.setenv('SELF_IMPROVE_STATE_DIR', str(root))
    monkeypatch.setenv('CLAUDE_PLUGIN_ROOT', PLUGIN_ROOT)
    monkeypatch.delenv('SELF_IMPROVE_DISABLE', raising=False)
    monkeypatch.delenv('SELF_IMPROVE_REVIEWER', raising=False)
    return root


@pytest.fixture
def project(tmp_path, monkeypatch):
    """Provide an isolated working directory in place of the user's project."""
    directory = tmp_path / 'project'
    (directory / '.claude').mkdir(parents=True)
    monkeypatch.chdir(directory)
    return directory


@pytest.fixture
def fake_reviewer(tmp_path, monkeypatch):
    """
    Point the reviewer at a deterministic stand-in for the ``claude`` binary.

    Returns a callable that selects the behavior and yields the recorded
    invocation, so tests can assert on the isolation flags the real reviewer
    would receive.
    """
    launcher = tmp_path / 'fake-claude'
    launcher.write_text(
        '#!/bin/sh\nexec %s %s "$@"\n'
        % (
            sys.executable,
            os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fake_reviewer.py'),
        )
    )
    launcher.chmod(0o755)
    argv_path = tmp_path / 'reviewer-argv.json'
    stdin_path = tmp_path / 'reviewer-stdin.json'

    monkeypatch.setenv('SELF_IMPROVE_REVIEWER_CMD', str(launcher))
    monkeypatch.setenv('FAKE_REVIEWER_ARGV', str(argv_path))
    monkeypatch.setenv('FAKE_REVIEWER_STDIN', str(stdin_path))

    class Harness:
        argv_file = argv_path
        stdin_file = stdin_path

        def mode(self, name):
            monkeypatch.setenv('FAKE_REVIEWER_MODE', name)
            return self

        def recorded_argv(self):
            return json.loads(argv_path.read_text())

        def recorded_bundle(self):
            return json.loads(stdin_path.read_text())

    return Harness()


@pytest.fixture
def run_si(state_root, claude_home):
    """
    Invoke the shell entry point exactly as a hook would.

    Going through ``scripts/si`` rather than importing the module is deliberate:
    it exercises interpreter discovery, which is the part most likely to break on
    a machine whose ``python3`` points at a stale virtualenv.
    """

    def _run(*args, stdin=None, env=None, cwd=None):
        environment = dict(os.environ)
        environment.update(env or {})
        return subprocess.run(
            [SI, *args],
            input=stdin if stdin is not None else '',
            capture_output=True,
            text=True,
            env=environment,
            cwd=cwd,
            timeout=60,
        )

    return _run
