#!/usr/bin/env python3

"""Tests for the ``--recommend`` path from the CLI through to reported warnings."""

from __future__ import annotations

from pathlib import Path

import pytest

from validate_agent_files.cli import parse_arguments
from validate_agent_files.main import main
from validate_agent_files.types import ValidationLevel
from validate_agent_files.validators.skill import (
    SkillFrontmatterValidator,
    SkillStructureValidator,
)

# A description carrying a term the frontmatter validator calls vague, over a
# top-level section short enough to trip the structure validator.
RECOMMENDABLE_SKILL = """---
name: sample-skill
description: A bundle of tools for the invented sample workflow.
---
# Sample

## Detail

The recommendation under test is about the top-level section, so this one
carries enough prose to stand on its own.
"""


def _write_skill(root: Path) -> Path:
    """Write the recommendation fixture and return its SKILL.md path."""
    skill_dir = root / 'sample-skill'
    skill_dir.mkdir(parents=True)
    skill_file = skill_dir / 'SKILL.md'
    skill_file.write_text(RECOMMENDABLE_SKILL)
    return skill_file


def _expected_messages() -> set[str]:
    """Ask the validators directly what the fixture should be warned about."""
    frontmatter = {
        'name': 'sample-skill',
        'description': 'A bundle of tools for the invented sample workflow.',
    }
    body = RECOMMENDABLE_SKILL.split('---\n', 2)[2]
    issues = SkillFrontmatterValidator().validate(frontmatter, show_warnings=True)
    issues += SkillStructureValidator().validate(body, show_warnings=True)
    return {issue.message for issue in issues if issue.level == ValidationLevel.WARNING}


def test_recommend_flag_reports_skill_warnings(package_tmp_path, capsys) -> None:
    """The recommendation flag surfaces both skill validators' warnings."""
    skill_file = _write_skill(package_tmp_path)

    exit_code = main([str(skill_file), '--recommend'])
    output = capsys.readouterr().out

    assert exit_code == 0
    expected = _expected_messages()
    assert expected, 'the fixture must trip at least one recommendation check'
    for message in expected:
        assert message in output


def test_without_recommend_no_warnings_are_reported(package_tmp_path, capsys) -> None:
    """Without the flag the same fixture reports none of those warnings."""
    skill_file = _write_skill(package_tmp_path)

    exit_code = main([str(skill_file)])
    output = capsys.readouterr().out

    assert exit_code == 0
    for message in _expected_messages():
        assert message not in output


def test_errors_only_suppresses_recommendations(package_tmp_path, capsys) -> None:
    """``--errors-only`` suppresses warnings even alongside ``--recommend``."""
    skill_file = _write_skill(package_tmp_path)

    exit_code = main([str(skill_file), '--recommend', '--errors-only'])
    output = capsys.readouterr().out

    assert exit_code == 0
    for message in _expected_messages():
        assert message not in output


@pytest.mark.parametrize('extra_args', [[], ['--recommend']])
def test_warnings_never_change_the_exit_code(
    package_tmp_path, capsys, extra_args: list[str]
) -> None:
    """A fixture with warnings and no errors exits 0 whether or not warnings show."""
    skill_file = _write_skill(package_tmp_path)

    exit_code = main([str(skill_file), *extra_args])
    capsys.readouterr()

    assert exit_code == 0


def test_parser_exposes_recommend_and_errors_only_destinations() -> None:
    """``main`` reads these destinations directly, so the parser must define both."""
    parsed = parse_arguments([])

    assert parsed.recommend is False
    assert parsed.errors_only is False
    assert parse_arguments(['--recommend']).recommend is True
    assert parse_arguments(['--errors-only']).errors_only is True
