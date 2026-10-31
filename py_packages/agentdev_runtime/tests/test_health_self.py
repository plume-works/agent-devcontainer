"""The health probes re-enter the installed package, never a same-named one in the working directory."""

from __future__ import annotations

from pathlib import Path
import subprocess

from agentdev_runtime import health


def test_probe_command_ignores_a_shadowing_package_in_the_cwd(tmp_path: Path) -> None:
    """A checkout's own agentdev_runtime package in the cwd is not imported by a probe."""
    shadow = tmp_path / 'agentdev_runtime'
    shadow.mkdir()
    marker = tmp_path / 'shadow-imported'
    (shadow / '__init__.py').write_text(f'open({str(marker)!r}, "w").close()\n')
    (shadow / '__main__.py').write_text('')

    subprocess.run([*health.SELF, 'health', 'status'], cwd=tmp_path, capture_output=True)

    assert not marker.exists()
