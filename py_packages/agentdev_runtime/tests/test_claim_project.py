"""
The create phase changes the owner of the sibling checkout volume.

It does so only for a non-root account and only when the volume is a mount.
"""

from pathlib import Path
import subprocess

from agentdev_runtime import lifecycle, settings
import pytest


@pytest.fixture
def chowns(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[list[str]]:
    """Record every command ``claim_project`` runs, with the workspace elsewhere."""
    ran: list[list[str]] = []
    monkeypatch.setattr(
        subprocess,
        'run',
        lambda argv, **kwargs: ran.append(argv) or subprocess.CompletedProcess(argv, 0),
    )
    monkeypatch.setenv('DEV_WORKSPACE_FOLDER', str(tmp_path))
    return ran


def test_a_root_account_never_re_owns_the_volume(
    chowns: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lifecycle.os, 'getuid', lambda: 0)
    monkeypatch.setattr(lifecycle.os.path, 'ismount', lambda path: True)

    lifecycle.claim_project(settings.Settings())

    assert chowns == []


def test_no_mount_at_the_project_path_is_left_alone(
    chowns: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(lifecycle.os, 'getuid', lambda: 1000)
    monkeypatch.setattr(lifecycle.os.path, 'ismount', lambda path: False)

    lifecycle.claim_project(settings.Settings())

    assert chowns == []
