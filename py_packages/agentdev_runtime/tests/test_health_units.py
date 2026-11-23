"""Readiness and status read from systemd's view of the image's units."""

from pathlib import Path

from agentdev_runtime import health
import pytest

SYSTEMCTL = """#!/bin/sh
shift_user=""
[ "$1" = --user ] && shift && shift_user=1
[ "$1" = is-active ] || exit 64
shift
for unit in "$@"; do
  if [ -n "$shift_user" ]; then echo "${USER_STATE:-active}"; continue; fi
  case "$unit" in
    "$FAILED_UNIT") echo failed ;;
    *) echo "${SYSTEM_STATE:-active}" ;;
  esac
done
"""
DOCKER = '#!/bin/sh\n[ "${ENGINE_DOWN:-}" = 1 ] && exit 1\necho 29.0.0\n'


@pytest.fixture
def stubs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name, body in (('systemctl', SYSTEMCTL), ('docker', DOCKER)):
        (tmp_path / name).write_text(body)
        (tmp_path / name).chmod(0o755)
    monkeypatch.setenv('PATH', f'{tmp_path}:/usr/bin:/bin')
    return tmp_path


def test_ready_when_every_core_unit_is_active_and_the_engine_answers(stubs: Path) -> None:
    assert health.ready() == 0


def test_not_ready_while_a_unit_activates(
    stubs: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv('SYSTEM_STATE', 'activating')

    assert health.ready() == 1
    assert 'agentdev-bootstrap.service: activating' in capsys.readouterr().out


def test_not_ready_while_the_engine_does_not_answer(
    stubs: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv('ENGINE_DOWN', '1')

    assert health.ready() == 1


def test_failed_names_only_failed_core_units(stubs: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv('FAILED_UNIT', 'agentdev-created.service')

    assert health.failed() == ['agentdev-created.service']


def test_status_points_at_the_journal_of_a_failed_unit(
    stubs: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv('FAILED_UNIT', 'agentdev-bootstrap.service')
    monkeypatch.setenv('USER_STATE', 'inactive')

    assert health.status() == 1
    out = capsys.readouterr().out
    assert 'agentdev-xpra.service (user): inactive' in out
    assert 'journalctl -u agentdev-bootstrap.service -b --no-pager' in out


def test_without_systemd_every_unit_is_unknown(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv('PATH', str(tmp_path))

    assert set(health.unit_states(health.CORE_UNITS).values()) == {'unknown'}
