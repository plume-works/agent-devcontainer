"""Tests for the deploy and devcontainer service profiles of runtime-supervisor.py."""

from __future__ import annotations

from collections.abc import Callable, Iterator
import configparser
import importlib.util
from pathlib import Path
import shutil
import signal
import sys
import time
from types import ModuleType
from uuid import uuid4

import pytest
from test_agent_runtime_supervision import (
    CONFIG,
    REPO_ROOT,
    started,
    Supervision,
    SUPERVISOR,
    TMP_ROOT,
)

DEVCONTAINER_CONFIG = REPO_ROOT / 'docker/devcontainer/supervisord.conf'

SHARED = {'dbus', 'keyring', 'dockerd', 'cbm', 'xpra', 'opencode', 'remote-control'}
DEVCONTAINER_REQUIRED = ['dbus', 'keyring', 'dockerd', 'cbm', 'xpra']


def load_supervisor() -> ModuleType:
    spec = importlib.util.spec_from_file_location('runtime_supervisor', SUPERVISOR)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope='module')
def supervisor() -> ModuleType:
    return load_supervisor()


def settings(supervisor: ModuleType, monkeypatch: pytest.MonkeyPatch, **env: str):
    for name in ('AGENTDEV_SKIP_XPRA', 'AGENTDEV_OPENCODE_WEB', 'AGENTDEV_CLAUDE_RC_MODE'):
        monkeypatch.delenv(name, raising=False)
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    return supervisor.Settings.from_env()


def names(services) -> list[str]:
    return [service.name for service in services]


def requires(services, name: str) -> set[str]:
    """Return every component ``name`` transitively waits for."""
    by_name = {service.name: service for service in services}
    found: set[str] = set()
    pending = list(by_name[name].after)
    while pending:
        dependency = pending.pop()
        if dependency not in found:
            found.add(dependency)
            pending.extend(by_name[dependency].after)
    return found


def test_both_profiles_share_one_service_vocabulary(supervisor):
    deploy = set(names(supervisor.PROFILES['deploy'].services))
    devcontainer = set(names(supervisor.PROFILES['devcontainer'].services))
    assert deploy & devcontainer == SHARED
    assert deploy - SHARED == {'prepare', 'config', 'prune', 'project', 'index'}
    assert devcontainer - SHARED == {'created'}


def test_deploy_gates_opencode_on_project_preparation(supervisor):
    services = supervisor.PROFILES['deploy'].services
    by_name = {service.name: service for service in services}
    assert {'keyring', 'prepare'} <= requires(services, 'opencode')
    assert by_name['opencode'].core and by_name['prepare'].core
    # Indexing is requested in the background; it never delays OpenCode.
    assert by_name['index'].after == ('cbm',)
    assert 'index' not in requires(services, 'opencode')
    assert not supervisor.PROFILES['deploy'].exit_on_latch


def test_devcontainer_requires_its_persistent_services_and_omits_project_work(
    supervisor, monkeypatch
):
    selected = supervisor.enabled_services(
        settings(supervisor, monkeypatch, AGENTDEV_RUNTIME_MODE='devcontainer')
    )
    assert names(selected) == DEVCONTAINER_REQUIRED
    assert all(service.core and not service.client for service in selected)
    assert supervisor.PROFILES['devcontainer'].exit_on_latch


def test_devcontainer_starts_opencode_only_as_an_opt_in_client(supervisor, monkeypatch):
    selected = supervisor.enabled_services(
        settings(
            supervisor,
            monkeypatch,
            AGENTDEV_RUNTIME_MODE='devcontainer',
            AGENTDEV_OPENCODE_WEB='1',
            AGENTDEV_CLAUDE_RC_MODE='session',
        )
    )
    by_name = {service.name: service for service in selected}
    assert names(selected) == [*DEVCONTAINER_REQUIRED, 'created', 'opencode', 'remote-control']
    for client in ('created', 'opencode', 'remote-control'):
        assert by_name[client].client and not by_name[client].core
    assert 'created' in requires(selected, 'opencode')
    assert 'created' in requires(selected, 'remote-control')


def test_disabled_optional_services_leave_both_profiles(supervisor, monkeypatch):
    for mode in ('deploy', 'devcontainer'):
        selected = names(
            supervisor.enabled_services(
                settings(
                    supervisor, monkeypatch, AGENTDEV_RUNTIME_MODE=mode, AGENTDEV_SKIP_XPRA='1'
                )
            )
        )
        assert 'xpra' not in selected and 'remote-control' not in selected
    deploy = names(
        supervisor.enabled_services(
            settings(supervisor, monkeypatch, AGENTDEV_RUNTIME_MODE='deploy')
        )
    )
    assert 'opencode' in deploy, 'deploy always serves OpenCode'


@pytest.mark.parametrize('mode', ['', 'standalone', 'Deploy', 'deploy,devcontainer'])
def test_an_invalid_profile_name_is_a_configuration_error(supervisor, monkeypatch, mode):
    parsed = settings(supervisor, monkeypatch, AGENTDEV_RUNTIME_MODE=mode)
    assert parsed.profile is None
    assert any(
        error.startswith('AGENTDEV_RUNTIME_MODE must be deploy or devcontainer')
        for error in parsed.errors
    )
    with pytest.raises(ValueError, match='no runtime profile'):
        supervisor.enabled_services(parsed)


def programs(config: Path) -> list[str]:
    parser = configparser.RawConfigParser()
    parser.read(config)
    return [s.split(':', 1)[1] for s in parser.sections() if s.startswith('program:')]


@pytest.mark.parametrize(
    ('mode', 'config'), [('deploy', CONFIG), ('devcontainer', DEVCONTAINER_CONFIG)]
)
def test_each_image_config_carries_exactly_its_profile_programs(supervisor, mode, config):
    assert sorted(programs(config)) == sorted(names(supervisor.PROFILES[mode].services))


def test_the_profiles_share_their_program_definitions(supervisor):
    deploy, devcontainer = configparser.RawConfigParser(), configparser.RawConfigParser()
    deploy.read(CONFIG)
    devcontainer.read(DEVCONTAINER_CONFIG)
    for name in SHARED:
        assert dict(devcontainer[f'program:{name}']) == dict(deploy[f'program:{name}']), name
    for section in ('supervisord', 'unix_http_server', 'eventlistener:controller'):
        assert dict(devcontainer[section]) == dict(deploy[section]), section
    assert devcontainer['program:created']['command'].endswith('devcontainer-created.sh wait')


@pytest.fixture
def devcontainer() -> Iterator[Callable[..., Supervision]]:
    TMP_ROOT.mkdir(exist_ok=True)
    created: list[Supervision] = []

    def factory(**env: str) -> Supervision:
        root = TMP_ROOT / f'dc-{uuid4().hex[:8]}'
        box = Supervision(
            root, config=DEVCONTAINER_CONFIG, oneshots={'created'}, mode='devcontainer', **env
        )
        # A Dev Container forwards Xpra locally; it needs no proxy secret.
        del box.env['XPRA_PASSWORD']
        created.append(box)
        return box

    yield factory
    for box in created:
        box.terminate()
        shutil.rmtree(box.root, ignore_errors=True)


def test_devcontainer_starts_required_services_then_publishes_readiness(devcontainer):
    box = devcontainer()
    box.start()
    box.wait_for(box.ready)
    assert started(box.events()) == ['bootstrap', *DEVCONTAINER_REQUIRED]
    state = box.runtime()
    assert state['profile'] == 'devcontainer' and state['ready'] is True
    assert state['probes'] == DEVCONTAINER_REQUIRED
    assert box.health('ready').returncode == 0


def test_readiness_is_withheld_until_every_required_service_is_healthy(devcontainer):
    box = devcontainer(AGENTDEV_SERVICE_START_TIMEOUT='20')
    box.set('dockerd', 'mode', 'never-ready')
    box.start()
    box.wait_for(lambda: box.status('dockerd') == 'starting')
    time.sleep(0.6)
    state = box.runtime()
    assert state['state'] == 'pending' and state['ready'] is False
    assert box.health('ready').returncode == 1
    (box.state / 'dockerd.mode').unlink()
    box.set('dockerd', 'ready')
    box.wait_for(box.ready)
    assert box.health('ready').returncode == 0


def test_a_failing_required_probe_withdraws_readiness(devcontainer):
    box = devcontainer()
    box.start()
    box.wait_for(box.ready)
    box.set('cbm', 'unhealthy', 'cbm is wedged')
    result = box.health('ready')
    assert result.returncode == 1 and 'core probe failed: cbm' in result.stdout


@pytest.mark.parametrize('service', DEVCONTAINER_REQUIRED)
def test_a_required_service_exhausting_recovery_ends_the_container(devcontainer, service):
    box = devcontainer(AGENTDEV_RECOVERY_ATTEMPTS='2')
    box.set(service, 'mode', 'crash-always')
    box.start()
    assert box.wait_exit(timeout=60) != 0
    state = box.runtime()
    assert state['state'] == 'failed' and state['latched'] == service
    assert state['ready'] is False
    assert box.health('ready').returncode == 1
    assert box.record()['component'] == service
    assert f'exiting: {service}:' in box.output()
    assert started(box.events()).count(service) == 3


def test_a_required_service_recovers_within_its_budget(devcontainer):
    box = devcontainer()
    box.start()
    box.wait_for(box.ready)
    box.set('dockerd', 'crash')
    box.wait_for(lambda: started(box.events()).count('dockerd') == 2)
    box.wait_for(box.ready)
    assert box.alive()


def test_a_bootstrap_failure_ends_the_devcontainer_without_starting_services(devcontainer):
    box = devcontainer()
    box.set('bootstrap', 'exit', '4')
    box.start()
    assert box.wait_exit() == 1
    assert started(box.events()) == ['bootstrap']
    state = box.runtime()
    assert state['latched'] == 'bootstrap' and state['ready'] is False


def test_an_invalid_profile_ends_the_runtime_before_the_bootstrap(devcontainer):
    box = devcontainer()
    box.env['AGENTDEV_RUNTIME_MODE'] = 'standalone'
    box.start()
    assert box.wait_exit() == 1
    assert box.events() == []
    state = box.runtime()
    assert state['latched'] == 'configuration' and state['ready'] is False
    assert 'AGENTDEV_RUNTIME_MODE must be deploy or devcontainer' in box.output()


def test_clients_wait_for_the_create_phase_without_gating_readiness(devcontainer):
    box = devcontainer(AGENTDEV_OPENCODE_WEB='1', AGENTDEV_PREPARE_TIMEOUT='30')
    box.set('created', 'sleep', '2')
    box.start()
    box.wait_for(lambda: box.runtime().get('ready') is True)
    assert 'opencode' not in started(box.events())
    assert box.health('ready').returncode == 0
    box.wait_for(lambda: box.status('opencode') == 'ready')
    assert started(box.events())[-2:] == ['created', 'opencode']


def test_a_failing_client_degrades_without_withdrawing_readiness(devcontainer):
    box = devcontainer(AGENTDEV_OPENCODE_WEB='1', AGENTDEV_STRICT_STARTUP='1')
    box.set('opencode', 'mode', 'crash-always')
    box.start()
    box.wait_for(lambda: box.status('opencode') == 'failed', timeout=40)
    state = box.runtime()
    assert state['state'] == 'degraded' and state['ready'] is True and state['latched'] is None
    assert box.alive() and box.health('ready').returncode == 0


def test_sigterm_stops_every_service_and_exits_cleanly(devcontainer):
    box = devcontainer()
    box.start()
    box.wait_for(box.ready)
    assert box.process is not None
    box.process.send_signal(signal.SIGTERM)
    assert box.wait_exit() == 0
    stopped = [e.split()[1] for e in box.events() if e.startswith('stop ')]
    assert sorted(stopped) == sorted(DEVCONTAINER_REQUIRED)
    assert stopped.index('xpra') < stopped.index('dockerd')
