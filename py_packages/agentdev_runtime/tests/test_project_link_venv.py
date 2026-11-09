"""`project link-venv` links a checkout's `.venv` to its own directory under the venv root."""

import os
from pathlib import Path
import subprocess
import sys

from agentdev_runtime import project
from agentdev_runtime.settings import DEPLOY, DEVCONTAINER, Settings
import pytest


@pytest.fixture
def checkout(tmp_path: Path) -> Path:
    workspace = tmp_path / 'checkout'
    workspace.mkdir()
    subprocess.run(['git', 'init', '-q', str(workspace)], check=True)
    return workspace


@pytest.fixture
def root(tmp_path: Path) -> Path:
    return tmp_path / 'uv' / 'venvs'


def settings_for(root: Path, mode: str = DEVCONTAINER) -> Settings:
    (root.parent).mkdir(parents=True, exist_ok=True)
    return Settings({**os.environ, 'AGENTDEV_RUNTIME_MODE': mode, 'AGENTDEV_VENV_ROOT': str(root)})


def test_a_fresh_checkout_gets_a_link_to_its_own_directory(checkout: Path, root: Path) -> None:
    (checkout / 'sub').mkdir()
    assert project.link_venv(settings_for(root), checkout / 'sub') == 0
    venv = checkout / '.venv'
    assert venv.is_symlink()
    assert Path(os.readlink(venv)) == root / 'checkout'
    assert (root / 'checkout').is_dir()


def test_a_second_run_changes_nothing(checkout: Path, root: Path) -> None:
    settings = settings_for(root)
    project.link_venv(settings, checkout)
    (root / 'checkout' / 'marker').touch()
    before = os.lstat(checkout / '.venv')
    assert project.link_venv(settings, checkout) == 0
    assert os.lstat(checkout / '.venv').st_ino == before.st_ino
    assert (root / 'checkout' / 'marker').exists()


def test_a_dangling_link_gets_its_target_created(checkout: Path, root: Path) -> None:
    (checkout / '.venv').symlink_to(root / 'checkout')
    assert project.link_venv(settings_for(root), checkout) == 0
    assert (root / 'checkout').is_dir()


def test_a_link_elsewhere_under_the_root_is_repaired(checkout: Path, root: Path) -> None:
    (checkout / '.venv').symlink_to(root / 'ws-project')
    assert project.link_venv(settings_for(root), checkout) == 0
    assert Path(os.readlink(checkout / '.venv')) == root / 'checkout'


def test_a_real_venv_directory_is_left_with_a_warning(
    checkout: Path, root: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (checkout / '.venv').mkdir()
    assert project.link_venv(settings_for(root), checkout) == 0
    assert not (checkout / '.venv').is_symlink()
    assert 'not a link' in capsys.readouterr().err


def test_a_foreign_link_is_left_with_a_warning(
    checkout: Path, root: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    foreign = tmp_path / 'elsewhere'
    (checkout / '.venv').symlink_to(foreign)
    assert project.link_venv(settings_for(root), checkout) == 0
    assert Path(os.readlink(checkout / '.venv')) == foreign
    assert 'outside' in capsys.readouterr().err


def test_deploy_mode_changes_nothing(checkout: Path, root: Path) -> None:
    assert project.link_venv(settings_for(root, DEPLOY), checkout) == 0
    assert not os.path.lexists(checkout / '.venv')


def test_outside_a_checkout_changes_nothing(tmp_path: Path, root: Path) -> None:
    plain = tmp_path / 'plain'
    plain.mkdir()
    assert project.link_venv(settings_for(root), plain) == 0
    assert not os.path.lexists(plain / '.venv')


def test_a_missing_root_parent_changes_nothing(checkout: Path, tmp_path: Path) -> None:
    root = tmp_path / 'absent' / 'venvs'
    settings = Settings(
        {**os.environ, 'AGENTDEV_RUNTIME_MODE': DEVCONTAINER, 'AGENTDEV_VENV_ROOT': str(root)}
    )
    assert project.link_venv(settings, checkout) == 0
    assert not os.path.lexists(checkout / '.venv')


def test_the_command_line_links_the_named_checkout(checkout: Path, root: Path) -> None:
    root.parent.mkdir(parents=True)
    result = subprocess.run(
        [sys.executable, '-m', 'agentdev_runtime', 'project', 'link-venv', str(checkout)],
        env={**os.environ, 'AGENTDEV_RUNTIME_MODE': DEVCONTAINER, 'AGENTDEV_VENV_ROOT': str(root)},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert (checkout / '.venv').is_symlink()


def test_the_environment_records_its_checkout(checkout: Path, root: Path) -> None:
    project.link_venv(settings_for(root), checkout)
    assert (root / 'checkout.checkout').read_text() == str(checkout)
