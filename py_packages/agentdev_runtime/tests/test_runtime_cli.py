"""The command line's shape."""

from agentdev_runtime import cli
from agentdev_runtime.settings import VARIABLES
import pytest


def test_a_command_is_required(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as raised:
        cli.main([])
    assert raised.value.code == 2


def test_settings_prints_every_variable(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(['settings']) == 0
    out = capsys.readouterr().out
    assert all(f'`{variable.name}`' in out for variable in VARIABLES)
