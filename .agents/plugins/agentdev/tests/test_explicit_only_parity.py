#!/usr/bin/env python3

"""
Every skill gated by ``disable-model-invocation`` is gated on Codex too.

Claude Code and the OpenCode bridge read the frontmatter key; Codex reads only
``agents/openai.yaml``. See architecture/explicit-only-workflow-agents.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


def _frontmatter(skill_md: Path) -> dict:
    """Parse the YAML frontmatter of a SKILL.md."""
    _, block, _ = skill_md.read_text(encoding='utf-8').split('---\n', 2)
    return yaml.safe_load(block) or {}


def _codex_implicit(skill_dir: Path) -> bool:
    """Whether Codex may invoke the skill implicitly, per its openai.yaml."""
    policy_file = skill_dir / 'agents' / 'openai.yaml'
    if not policy_file.is_file():
        return True
    policy = (yaml.safe_load(policy_file.read_text(encoding='utf-8')) or {}).get('policy') or {}
    return policy.get('allow_implicit_invocation', True) is not False


def parity_mismatches(skills_dir: Path) -> list[str]:
    """Name each skill whose Claude and Codex implicit-invocation gates disagree."""
    mismatches = []
    for skill_md in sorted(skills_dir.glob('*/SKILL.md')):
        claude_gated = _frontmatter(skill_md).get('disable-model-invocation') is True
        codex_gated = not _codex_implicit(skill_md.parent)
        if claude_gated != codex_gated:
            mismatches.append(
                f'{skill_md.parent.name}: disable-model-invocation={claude_gated}, '
                f'allow_implicit_invocation={not codex_gated}'
            )
    return mismatches


def _write_skill(root: Path, name: str, gated: bool, policy: bool | None) -> None:
    """Create a fake skill with the given Claude gate and Codex policy."""
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    gate = 'disable-model-invocation: true\n' if gated else ''
    (skill_dir / 'SKILL.md').write_text(
        f'---\nname: {name}\ndescription: Fake.\n{gate}---\n\nBody.\n', encoding='utf-8'
    )
    if policy is not None:
        (skill_dir / 'agents').mkdir()
        (skill_dir / 'agents' / 'openai.yaml').write_text(
            f'policy:\n  allow_implicit_invocation: {str(policy).lower()}\n', encoding='utf-8'
        )


def test_catalog_gates_agree(plugin_root: Path) -> None:
    """The shipped catalog gates every explicit-only skill on both harnesses."""
    skills_dir = plugin_root / 'skills'
    gated = [
        p
        for p in skills_dir.glob('*/SKILL.md')
        if _frontmatter(p).get('disable-model-invocation') is True
    ]
    assert gated, 'expected at least one explicit-only skill'
    assert parity_mismatches(skills_dir) == []


@pytest.mark.parametrize(
    ('gated', 'policy', 'expected'),
    [
        (True, False, False),
        (False, None, False),
        (True, None, True),
        (True, True, True),
        (False, False, True),
    ],
    ids=['both-gated', 'neither-gated', 'claude-only', 'codex-allows', 'codex-only'],
)
def test_parity_check(
    plugin_tmp_path: Path, gated: bool, policy: bool | None, expected: bool
) -> None:
    """A mismatch in either direction is reported, and agreement is not."""
    _write_skill(plugin_tmp_path, 'fake-skill', gated, policy)
    assert bool(parity_mismatches(plugin_tmp_path)) is expected
