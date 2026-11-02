from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import subprocess
import sys

GC = [sys.executable, '-m', 'agentdev_runtime', 'docker', 'gc']
IMAGE_PRUNE = 'image prune -af --filter until=72h'
CACHE_PRUNE = 'builder prune -f --max-used-space 10GB'
VOLUME_LIST = 'volume ls -q --filter dangling=true'
OLD = (datetime.now(timezone.utc) - timedelta(hours=100)).strftime('%Y-%m-%dT%H:%M:%SZ')
YOUNG = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
VOLUMES = {
    'dind-var-lib-docker-0abc': OLD,
    'proj_devcontainer_dind-var-lib-containerd-0abc': OLD,
    'proj_devcontainer_agentdev-cache': OLD,
    'proj_devcontainer_agentdev-codex': OLD,
    'dind-var-lib-docker-1young': YOUNG,
    'agentdev-agents-auth': OLD,
    'proj_devcontainer_agentdev-claude': OLD,
    'proj_devcontainer_agentdev-opencode': OLD,
    'someone-elses-data': OLD,
}
REMOVED = {
    'dind-var-lib-docker-0abc',
    'proj_devcontainer_dind-var-lib-containerd-0abc',
    'proj_devcontainer_agentdev-cache',
    'proj_devcontainer_agentdev-codex',
}


def run_gc(
    tmp_path: Path,
    *,
    docker_installed: bool = True,
    info_exit: int = 0,
    failing: str = '',
) -> tuple[subprocess.CompletedProcess[str], list[str]]:
    """Run one pass with a stub docker that logs its arguments and fails `failing`."""
    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    for tool in ('bash', 'env'):
        (fake_bin / tool).symlink_to(shutil.which(tool))
    log = tmp_path / 'docker.log'
    inspect = ''.join(
        f'  [[ " $* " == *" {name} "* ]] && echo "{name} {created}"\n'
        for name, created in VOLUMES.items()
    )
    if docker_installed:
        (fake_bin / 'docker').write_text(
            '#!/usr/bin/env bash\n'
            f'echo "$*" >> "{log}"\n'
            f'if [[ "$1" == info ]]; then exit {info_exit}; fi\n'
            f'if [[ -n "{failing}" && "$*" == "{failing}" ]]; then echo boom; exit 1; fi\n'
            f'if [[ "$*" == "{VOLUME_LIST}" ]]; then printf "%s\\n" {" ".join(VOLUMES)}; fi\n'
            'if [[ "$1 $2" == "volume inspect" ]]; then\n'
            f'{inspect}'
            '  exit 0\n'
            'fi\n'
            'exit 0\n'
        )
        (fake_bin / 'docker').chmod(0o755)
    result = subprocess.run(GC, env={'PATH': str(fake_bin)}, text=True, capture_output=True)
    calls = log.read_text().splitlines() if log.exists() else []
    return result, calls


def removed_volumes(calls: list[str]) -> set[str]:
    return {name for call in calls if call.startswith('volume rm ') for name in call.split()[2:]}


def test_prunes_images_then_cache_then_volumes_in_order(tmp_path):
    result, calls = run_gc(tmp_path)
    assert result.returncode == 0, result.stderr
    steps = [c for c in calls if c in (IMAGE_PRUNE, CACHE_PRUNE, VOLUME_LIST)]
    assert steps == [IMAGE_PRUNE, CACHE_PRUNE, VOLUME_LIST]


def test_removes_only_old_disposable_volumes(tmp_path):
    result, calls = run_gc(tmp_path)
    assert result.returncode == 0, result.stderr
    assert removed_volumes(calls) == REMOVED


def test_skips_when_docker_is_missing(tmp_path):
    result, calls = run_gc(tmp_path, docker_installed=False)
    assert result.returncode == 0, result.stderr
    assert calls == []


def test_skips_when_daemon_is_unreachable(tmp_path):
    result, calls = run_gc(tmp_path, info_exit=1)
    assert result.returncode == 0, result.stderr
    assert calls == ['info']


def test_a_failed_step_warns_and_the_pass_continues(tmp_path):
    result, calls = run_gc(tmp_path, failing=IMAGE_PRUNE)
    assert result.returncode == 0, result.stderr
    assert 'Warning' in result.stderr
    assert CACHE_PRUNE in calls
    assert removed_volumes(calls) == REMOVED
