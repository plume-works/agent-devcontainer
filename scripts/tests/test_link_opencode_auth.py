import os
from pathlib import Path
import stat
import subprocess

REPO_ROOT = Path(__file__).parents[2]
SCRIPT = REPO_ROOT / '.devcontainer/scripts/link-opencode-auth.sh'


def run_link(tmp_path: Path) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
    """Run the script with the shared and local auth paths under tmp_path."""
    shared_dir = tmp_path / 'agents-auth' / 'opencode'
    local = tmp_path / 'home' / '.local' / 'share' / 'opencode' / 'auth.json'
    env = {
        'PATH': os.environ['PATH'],
        'HOME': str(tmp_path / 'home'),
        'AGENTDEV_AGENTS_AUTH_DIR': str(tmp_path / 'agents-auth'),
    }
    result = subprocess.run([SCRIPT], env=env, text=True, capture_output=True)
    return result, shared_dir / 'auth.json', local


def test_links_without_creating_the_target(tmp_path):
    result, target, local = run_link(tmp_path)
    assert result.returncode == 0, result.stderr
    assert local.is_symlink()
    assert Path(os.readlink(local)) == target
    assert not target.exists()


def test_moves_a_regular_file_into_the_shared_volume(tmp_path):
    local = tmp_path / 'home' / '.local' / 'share' / 'opencode' / 'auth.json'
    local.parent.mkdir(parents=True)
    local.write_text('{"openai": {}}')
    result, target, local = run_link(tmp_path)
    assert result.returncode == 0, result.stderr
    assert local.is_symlink()
    assert target.read_text() == '{"openai": {}}'
    assert stat.S_IMODE(target.stat().st_mode) == 0o600


def test_rerun_keeps_the_link_and_the_shared_content(tmp_path):
    run_link(tmp_path)
    target = tmp_path / 'agents-auth' / 'opencode' / 'auth.json'
    target.write_text('{"xai": {}}')
    result, target, local = run_link(tmp_path)
    assert result.returncode == 0, result.stderr
    assert Path(os.readlink(local)) == target
    assert target.read_text() == '{"xai": {}}'


def test_shared_directory_is_private(tmp_path):
    result, target, _ = run_link(tmp_path)
    assert result.returncode == 0, result.stderr
    assert stat.S_IMODE(target.parent.stat().st_mode) == 0o700
