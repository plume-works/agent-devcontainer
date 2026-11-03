"""A final message shows a saved Verify report when it carries its lead line and every finding."""

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2]
SUITE = REPO_ROOT / 'scripts/e2e/iwe-workflows'
_spec = importlib.util.spec_from_file_location(
    'e2e_iwe_workflows_scenarios', SUITE / 'scenarios.py'
)
scenarios = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(scenarios)

SAVED = """---
plan: data/plans/20990101-made-up
commit: 0123456789abcdef
verdict: Blocked
skill_request: |2-
  C9 is not a finding of the body
---
Blocked data/plans/20990101-made-up

**Findings**

- C1 `src/a.py:3` — the requirement has no implementation. Implement it.
- **W1** `src/b.py:9` — a scenario is unverified.
  Its recommendation continues here.
- S1 unverified — tighten the wording.

**Verification commands**

- `make test` — passed.
"""
SHOWN = """Saved Verify report from 0123456
  Blocked data/plans/20990101-made-up
**Findings**
- C1 `src/a.py:3` — the requirement has no implementation. Implement it.
   - **W1** `src/b.py:9` — a scenario is unverified.
- S1 unverified — tighten the wording.

Blocked: C1 /agentdev:iwe-implement
"""


def test_report_lines_are_the_lead_and_each_finding():
    """The frontmatter is skipped; the lead line and each ID-led line remain."""
    assert scenarios.report_lines(SAVED) == [
        'Blocked data/plans/20990101-made-up',
        '- C1 `src/a.py:3` — the requirement has no implementation. Implement it.',
        '- **W1** `src/b.py:9` — a scenario is unverified.',
        '- S1 unverified — tighten the wording.',
    ]


def test_a_reposted_report_is_shown():
    """Lines match after surrounding whitespace is stripped."""
    assert scenarios.shows_report(SAVED, SHOWN)


@pytest.mark.parametrize(
    'final',
    [
        'Blocked data/plans/20990101-made-up — 1 CRITICAL. Report: .tmp/verify/20990101-made-up.md',
        SHOWN.replace('- S1 unverified — tighten the wording.\n', ''),
        SHOWN.replace('  Blocked data/plans/20990101-made-up\n', ''),
        '',
    ],
    ids=['path-only', 'finding-missing', 'lead-missing', 'empty'],
)
def test_a_reduced_report_is_not_shown(final):
    """A verdict with a path, or a report missing its lead or any finding, is not shown."""
    assert not scenarios.shows_report(SAVED, final)


def test_an_empty_saved_report_is_never_shown():
    """A saved report with no body cannot be shown by any message."""
    assert not scenarios.shows_report('---\nplan: x\n---\n', 'anything')
