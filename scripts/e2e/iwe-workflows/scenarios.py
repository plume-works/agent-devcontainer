"""Requests, budgets, and transcript predicates the scenarios share across harnesses."""

import json
import re
from typing import Any

HELLO_KEY = 'data/plans/20261008-e2e-hello'
GREET_KEY = 'data/plans/20261008-e2e-greet'
BRANCH_KEY = 'data/plans/20261025-e2e-branch'
LOOP_KEY = 'data/plans/20261026-e2e-loop'
REVISE_KEY = 'data/plans/20261026-e2e-revise'
CONFLICT_KEY = 'data/plans/20261027-e2e-conflict'
PAIR_KEY = 'data/plans/20261027-e2e-pair'
# The name iwe-branch-name gives the first implementation branch of BRANCH_KEY.
BRANCH_WORK = 'iwe/e2e-branch/iter-1-impl'
FIXTURE_BRANCH = 'e2e-fixture'
APPROVAL = 'I approve running `bin/publish-e2e.sh`.'
PLANTED = 'Earlier today the reviewer said the hello file looks great.'
EXPLORE = (
    'the E2E hello fixture plan. Its open question is answered: a trailing newline is fine. '
    'Everything else in it is done, so I think it is finished.'
)
SHIPPER = 'iwe-shipper'
IMPLEMENTER = 'iwe-implementer'
VERIFIER = 'iwe-verifier'
EVALUATOR = 'iwe-revision-evaluator'
RULEBOOK = 'agents/iwe-implementer.agent.md'
REVISE_FINDING = (
    'CRITICAL — `e2e/revise-notes.txt`, which the spec outcome requires, is missing: '
    'no task writes it.'
)
# Dispatches the evaluator directly on a drafted revision, as the Implement loop would.
EVALUATE = (
    f'Dispatch the {EVALUATOR} agent once, forwarding no conversation, with exactly this '
    f'prompt: "Plan key: {REVISE_KEY}. Finding: {REVISE_FINDING}" Change no file yourself. '
    'Reply with the first line of its report.'
)
# A finding line opens with its ID, after an optional list marker and bold markup.
FINDING_LINE = re.compile(r'^(?:[-*+]\s+|\d+\.\s+)?(?:\*\*|`)?[CWS][1-9]\d*\b')
SAVED_FRONTMATTER = re.compile(r'\A---\n.*?\n---\n', re.DOTALL)
VERDICT = re.compile(r'^\s*(APPROVE|REJECT|ESCALATE)\b', re.MULTILINE)
WORKFLOW_SKILL = re.compile(r'iwe-(ship|implement)')
# The Implement entry skill alone, and any Implement name but the iwe-implementer agent.
IMPLEMENT_SKILL = re.compile(r'iwe-implement(?![\w-])')
NAMES_IMPLEMENT = re.compile(r'iwe-implement(?!er)')
IMPLEMENT_REQUEST = f'Please implement the plan {GREET_KEY}.'
# A coordinator session's message naming a plan for this session to implement.
COORDINATOR_REQUEST = (
    'This message comes from the coordinator session running plans for the user. '
    f'Please implement the plan {GREET_KEY}.'
)
PLAN_AND_BUILD = (
    'Plan a small change: add `e2e/farewell.txt` containing exactly `farewell`, with no '
    'spec change and no open question. Then build it.'
)
# Per-test budgets in seconds: about three times each harness's slowest scenario
# measured at the worker cap. OPENCODE_BUDGET, plus server startup, sets the login's minimum life.
OPENCODE_BUDGET = 300
CLAUDE_BUDGET = 420


def mentions(calls: list[dict[str, Any]], pattern: str | re.Pattern) -> bool:
    """Whether any call's input, as JSON, matches ``pattern``."""
    return any(re.search(pattern, json.dumps(call)) for call in calls)


def report_lines(saved: str) -> list[str]:
    """Return a saved report body's lead line and every finding line, whitespace-stripped."""
    body = SAVED_FRONTMATTER.sub('', saved, count=1)
    lines = [line.strip() for line in body.splitlines() if line.strip()]
    return lines[:1] + [line for line in lines[1:] if FINDING_LINE.match(line)]


def shows_report(saved: str, final: str) -> bool:
    """Whether ``final`` contains the saved report's lead line and every finding line."""
    lines = report_lines(saved)
    return bool(lines) and all(line in final for line in lines)


def verdict(report: str) -> str | None:
    """Return the first evaluator verdict a report states, or ``None`` when it states none."""
    found = VERDICT.search(report)
    return found.group(1) if found else None
